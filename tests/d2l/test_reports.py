"""Test spooling, stable schemas, safe CSV, and manifest-last publication."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest
from d2l_test_helpers import NOW, Harness

from gc_stem.d2l.reports import (
    COVERAGE_COLUMNS,
    MATCH_COLUMNS,
    ReportError,
    ReportWriter,
    csv_safe,
)
from gc_stem.d2l.search import match_field


def add_match(
    harness: Harness, writer: ReportWriter, **changes: object
) -> None:
    """Record one bounded text finding using the writer's compiled targets."""
    ref = harness.ref()
    match = match_field(harness.text(ref), writer.plan, "text").matches[0]
    writer.record_match(replace(match, **changes))


@pytest.mark.parametrize(
    "value",
    [
        "=1+1",
        "+1",
        "-cmd",
        "@SUM(A1)",
        "  =1",
        "\t=1",
        " \x00=1",
        "\rplain",
        "\nplain",
        "\u2003@x",
        "\ufeff=1",
        "\u200b@x",
        "\x81-1",
    ],
)
def test_formula_and_control_leading_strings_are_escaped(value: str) -> None:
    """Leading spaces or controls cannot bypass spreadsheet-safe exports."""
    assert csv_safe(value) == "'" + value


@pytest.mark.parametrize(
    "value", ["", "ordinary", "x=1", " apostrophe", 0, 3, None]
)
def test_normal_values_and_trusted_counts_are_unchanged(value: object) -> None:
    """CSV safety does not alter ordinary metadata or trusted numeric counts."""
    assert csv_safe(value) == value


def test_fixed_schemas_counts_and_manifest_metadata(harness: Harness) -> None:
    """One coherent run publishes all fixed columns and truthful metadata."""
    writer = harness.writer()
    add_match(harness, writer)
    courses = harness.complete_results(writer)
    outputs = writer.finalize("COMPLETE", courses, finished_at=NOW)
    writer.close()
    with outputs.matches.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        assert tuple(reader.fieldnames) == MATCH_COLUMNS
    assert len(rows) == 1 and rows[0]["occurrence_count"] == "1"
    assert json.loads(rows[0]["object_path"]) == ["Module 1"]
    with outputs.coverage.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        coverage = list(reader)
        assert tuple(reader.fieldnames) == COVERAGE_COLUMNS
    assert len(coverage) == 14
    assert coverage[1]["status"] == "NOT_SELECTED"
    summary = json.loads(outputs.summary.read_text(encoding="utf-8"))
    assert summary["run_state"] == "COMPLETE"
    assert summary["counts"]["match_rows"] == 1
    assert summary["counts"]["matched_locations"] == 1
    assert summary["software"]["provider"] == "synthetic-fixture"
    assert summary["software"]["commit"] is None
    assert summary["inventory"]["sha256"] == harness.inventory.sha256
    assert summary["courses"][0]["match_status"] == "FOUND"
    assert summary["courses"][1]["match_status"] == "NOT_FOUND"
    assert not (outputs.run_directory / "spool.sqlite3").exists()
    assert not list(outputs.run_directory.glob("temporary-*"))


def test_csv_neutralizes_metadata_while_json_keeps_original(
    harness: Harness,
) -> None:
    """CSV export is escaped; original metadata remains available in JSON."""
    courses = harness.inventory.courses
    first = replace(courses[0], name="\t=HYPERLINK(1)")
    harness.inventory = replace(
        harness.inventory, courses=(first, *courses[1:])
    )
    writer = harness.writer()
    ref = harness.ref()
    add_match(
        harness, writer, owner=replace(ref, title="=1+1"), context="  @formula"
    )
    results = harness.complete_results(writer)
    paths = writer.finalize("COMPLETE", results, finished_at=NOW)
    with paths.matches.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["course_name"] == "'\t=HYPERLINK(1)"
    assert row["object_title"] == "'=1+1"
    assert row["context"] == "'  @formula"
    summary = json.loads(paths.summary.read_text(encoding="utf-8"))
    assert summary["courses"][0]["course_name"] == "\t=HYPERLINK(1)"


def test_duplicate_paths_are_merged_without_duplicate_match_rows(
    harness: Harness,
) -> None:
    """Late alternate locations survive export without rescanning the object."""
    writer = harness.writer()
    add_match(harness, writer)
    writer.merge_object_paths(harness.ref(paths=("Module 2", "Module 1")))
    paths = writer.finalize(
        "COMPLETE", harness.complete_results(writer), finished_at=NOW
    )
    with paths.matches.open(encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert json.loads(row["object_path"]) == ["Module 1", "Module 2"]


def test_duplicate_match_identity_is_not_double_counted(
    harness: Harness,
) -> None:
    """Conflicting replay cannot silently inflate findings."""
    writer = harness.writer()
    try:
        add_match(harness, writer)
        with pytest.raises(ReportError, match="DUPLICATE_MATCH"):
            add_match(harness, writer)
        assert writer.course_counts("123") == (1, 1)
    finally:
        writer.close()


def test_unique_run_directory_never_overwrites_previous_run(
    harness: Harness,
) -> None:
    """A repeated explicit run ID is refused atomically."""
    first = harness.writer()
    first.close()
    original = (first.run_directory / "spool.sqlite3").read_bytes()
    with pytest.raises(FileExistsError):
        harness.writer()
    assert (first.run_directory / "spool.sqlite3").read_bytes() == original


@pytest.mark.parametrize(
    "run_id", ["../outside", "/absolute", "has space", "", "."]
)
def test_unsafe_run_identifiers_are_rejected(
    harness: Harness, run_id: str
) -> None:
    """A run identifier cannot escape the configured output location."""
    with pytest.raises(ValueError):
        harness.writer(run_id)


def test_incomplete_coverage_cannot_publish_complete_manifest(
    harness: Harness,
) -> None:
    """Coverage evidence controls run completion independently of row counts."""
    writer = harness.writer()
    try:
        results = harness.complete_results(writer)
        first = results[0]
        tools = tuple(
            replace(item, enumeration_complete=False) if item.selected else item
            for item in first.tools
        )
        incomplete = (replace(first, tools=tools), *results[1:])
        with pytest.raises(ReportError, match="INCOMPLETE_COVERAGE"):
            writer.finalize("COMPLETE", incomplete)
        assert not (writer.run_directory / "summary.json").exists()
    finally:
        writer.close()


def test_missing_tool_rows_are_not_published_as_complete(
    harness: Harness,
) -> None:
    """A manifest cannot skip baseline scope rows."""
    writer = harness.writer()
    try:
        with pytest.raises(ReportError):
            writer.finalize("COMPLETE", ())
        assert not (writer.run_directory / "summary.json").exists()
    finally:
        writer.close()


def test_false_match_counts_are_rejected(harness: Harness) -> None:
    """Course summary counts must match the spooled report rows."""
    writer = harness.writer()
    try:
        results = harness.complete_results(writer)
        wrong = (
            replace(results[0], match_count=1, matched_locations=1),
            *results[1:],
        )
        with pytest.raises(ReportError, match="MATCH_COUNTS_MISMATCH"):
            writer.finalize("COMPLETE", wrong)
    finally:
        writer.close()


def test_manifest_is_published_after_both_csv_files(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The completion marker cannot appear before its prerequisite reports."""
    writer = harness.writer()
    results = harness.complete_results(writer)
    original = writer._publish
    order = []

    def publish(filename: str, write: object) -> Path:
        """Observe publication boundaries without changing serialization."""
        if filename == "summary.json":
            assert (writer.run_directory / "matches.csv").is_file()
            assert (writer.run_directory / "coverage.csv").is_file()
        order.append(filename)
        return original(filename, write)

    monkeypatch.setattr(writer, "_publish", publish)
    writer.finalize("COMPLETE", results, finished_at=NOW)
    assert order == ["matches.csv", "coverage.csv", "summary.json"]


@pytest.mark.parametrize(
    "failed_file", ["matches.csv", "coverage.csv", "summary.json"]
)
def test_publication_failure_never_leaves_a_completion_manifest(
    harness: Harness, monkeypatch: pytest.MonkeyPatch, failed_file: str
) -> None:
    """Output failures retain actual artifacts without false completion."""
    writer = harness.writer()
    add_match(harness, writer)
    results = harness.complete_results(writer)
    original = writer._publish

    def publish(filename: str, write: object) -> Path:
        """Fail one designated output write."""
        if filename == failed_file:
            raise OSError("AUTH_SECRET")
        return original(filename, write)

    monkeypatch.setattr(writer, "_publish", publish)
    with pytest.raises(ReportError) as caught:
        writer.finalize("COMPLETE", results, finished_at=NOW)
    writer.close()
    assert "AUTH_SECRET" not in str(caught.value)
    assert not (writer.run_directory / "summary.json").exists()
    assert writer.saved_paths
    assert not list(writer.run_directory.glob("temporary-*"))


def test_finalize_and_record_cannot_be_repeated(harness: Harness) -> None:
    """Published reports are immutable within one writer lifetime."""
    writer = harness.writer()
    results = harness.complete_results(writer)
    paths = writer.finalize("COMPLETE", results, finished_at=NOW)
    original = paths.summary.read_bytes()
    with pytest.raises(ReportError):
        writer.finalize("FAILED", results, finished_at=NOW)
    with pytest.raises(ReportError):
        add_match(harness, writer)
    assert paths.summary.read_bytes() == original


def test_report_sorting_is_stable_across_insertion_order(
    harness: Harness,
) -> None:
    """Match row order is inventory/tool/object/field/representation/target."""
    writer = harness.writer()
    for key in ("z-object", "a-object"):
        ref = harness.ref(key)
        writer.record_match(
            match_field(harness.text(ref), writer.plan, "text").matches[0]
        )
    results = harness.complete_results(writer)
    paths = writer.finalize("COMPLETE", results, finished_at=NOW)
    with paths.matches.open(encoding="utf-8", newline="") as stream:
        assert [row["object_id"] for row in csv.DictReader(stream)] == [
            "a-object",
            "z-object",
        ]


def test_unknown_versions_and_commit_are_explicit_nulls(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing build identities remain explicitly unknown."""
    from importlib.metadata import PackageNotFoundError

    monkeypatch.setattr(
        "gc_stem.d2l.reports.version",
        lambda name: (_ for _ in ()).throw(PackageNotFoundError()),
    )
    writer = harness.writer()
    paths = writer.finalize(
        "COMPLETE", harness.complete_results(writer), finished_at=NOW
    )
    info = json.loads(paths.summary.read_text(encoding="utf-8"))["software"]
    assert info["version"] is None and info["version_reason"] == "not_installed"
    assert info["commit"] is None and info["browser"] is None


def test_process_environment_is_not_copied_to_reports(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Authentication-like process values are outside effective settings."""
    monkeypatch.setenv("PRIVATE_ACCESS_TOKEN", "AUTH_SECRET")
    writer = harness.writer()
    paths = writer.finalize(
        "COMPLETE", harness.complete_results(writer), finished_at=NOW
    )
    assert "AUTH_SECRET" not in paths.summary.read_text(encoding="utf-8")
