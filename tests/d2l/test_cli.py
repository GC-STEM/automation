"""Test concrete command-line preparation, validation, and scan outcomes."""

import json

import pytest
from d2l_test_helpers import FixtureClient, Harness
from openpyxl import Workbook

from gc_stem.cli import main
from gc_stem.d2l.models import DiscoveryEnd


def arguments(harness: Harness, *extra: str) -> list[str]:
    """Select the synthetic configuration using the public command hierarchy."""
    return ["d2l", "search", "--config", str(harness.config), *extra]


def test_validate_only_reports_concrete_scope(
    harness: Harness, capsys: pytest.CaptureFixture[str]
) -> None:
    """Local validation works without a live provider."""
    assert main(arguments(harness, "--validate-only"), environment={}) == 0
    output = capsys.readouterr()
    assert "2 courses, 1 targets, 1 tools" in output.out
    assert not output.err and not harness.settings.output.directory.exists()


def test_validate_only_never_opens_provider(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The local validation command cannot accidentally start authentication."""

    def forbidden_provider(settings: object) -> None:
        """Trap any attempt to construct a provider during local validation."""
        raise AssertionError("Provider opened during validation")

    monkeypatch.setattr("gc_stem.cli.create_client", forbidden_provider)
    assert main(arguments(harness, "--validate-only"), environment={}) == 0


def test_live_unavailable_returns_two_without_report_directory(
    harness: Harness, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing browser code is not replaced by a synthetic success result."""
    assert main(arguments(harness), environment={}) == 2
    assert "browser provider" in capsys.readouterr().err
    assert not harness.settings.output.directory.exists()


def test_config_can_be_selected_from_supported_environment(
    harness: Harness,
) -> None:
    """D2L_CONFIG works consistently through the CLI."""
    assert (
        main(
            ["d2l", "search", "--validate-only"],
            environment={"D2L_CONFIG": str(harness.config)},
        )
        == 0
    )


def test_repeated_overrides_replace_file_lists(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit term/tool lists replace configured lists and retain order."""
    captured = []
    client = FixtureClient(harness)

    def create(settings: object) -> FixtureClient:
        """Capture the effective choices at the provider boundary."""
        captured.append(settings)
        return client

    monkeypatch.setattr("gc_stem.cli.create_client", create)
    status = main(
        arguments(
            harness,
            "--term",
            "first",
            "--term",
            "second",
            "--tool",
            "files",
            "--mode",
            "source",
            "--case-sensitive",
        ),
        environment={},
    )
    assert status == 0
    settings = captured[0]
    assert settings.search.terms == ("first", "second")
    assert settings.crawl.tools == ("files",)
    assert settings.search.mode == "source" and not settings.search.ignore_case


def test_cli_scan_with_injected_provider_publishes_reports(
    harness: Harness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The actual CLI, writer, and coordinator integrate using fixtures."""
    client = FixtureClient(harness)
    ref = harness.ref()
    client.discovery[("123", "content")] = [[ref, DiscoveryEnd(True, 1)]]
    monkeypatch.setattr("gc_stem.cli.create_client", lambda settings: client)
    assert main(arguments(harness), environment={}) == 0
    manifests = list(harness.settings.output.directory.glob("*/summary.json"))
    assert len(manifests) == 1
    summary = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert summary["software"]["provider"] == "synthetic-fixture"
    assert summary["counts"]["match_rows"] == 1 and client.closed
    assert "COMPLETE" in capsys.readouterr().out


def test_cli_partial_and_cancellation_exit_codes(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Incomplete and canceled runs preserve their public process outcomes."""
    client = FixtureClient(harness)
    client.discovery[("123", "content")] = [
        [DiscoveryEnd(False, reason_codes=("PAGINATION_UNKNOWN",))]
    ]
    monkeypatch.setattr("gc_stem.cli.create_client", lambda settings: client)
    assert main(arguments(harness), environment={}) == 3


def test_cli_preparation_uses_explicit_workbook_paths(
    harness: Harness, capsys: pytest.CaptureFixture[str]
) -> None:
    """The common CLI exposes the tested workbook utility with planned flags."""
    source = harness.root / "raw.xlsx"
    destination = harness.root / "processed.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "D2L"
    sheet.append(["CourseName"])
    sheet.append(["Course"])
    sheet["A2"].hyperlink = "https://tenant.example/d2l/p/home/123"
    workbook.save(source)
    workbook.close()
    status = main(
        [
            "d2l",
            "courses",
            "extract-urls",
            "--source",
            str(source),
            "--destination",
            str(destination),
        ],
        environment={},
    )
    assert status == 0 and destination.is_file()
    assert "Saved 1 course URLs" in capsys.readouterr().out


def test_invalid_local_inputs_return_two(
    harness: Harness, capsys: pytest.CaptureFixture[str]
) -> None:
    """An invalid inventory prevents provider startup and report creation."""
    harness.source.write_text("org_unit_id\nAUTH_SECRET\n", encoding="utf-8")
    assert main(arguments(harness, "--validate-only"), environment={}) == 2
    assert "AUTH_SECRET" not in capsys.readouterr().err


@pytest.mark.parametrize(
    "extra",
    [
        ["--password", "AUTH_SECRET"],
        ["--mode", "AUTH_SECRET"],
        ["--tool", "AUTH_SECRET"],
    ],
)
def test_rejected_cli_values_are_not_echoed(
    harness: Harness, capsys: pytest.CaptureFixture[str], extra: list[str]
) -> None:
    """Unknown or invalid argument diagnostics omit potential secret values."""
    with pytest.raises(SystemExit) as caught:
        main(arguments(harness, *extra), environment={})
    assert caught.value.code == 2
    assert "AUTH_SECRET" not in capsys.readouterr().err


def test_command_help_is_successful_and_specific(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public help identifies the local commands and supported overrides."""
    with pytest.raises(SystemExit) as caught:
        main(["d2l", "search", "--help"], environment={})
    assert caught.value.code == 0
    text = capsys.readouterr().out
    assert "--validate-only" in text and "--courses-format" in text


def test_output_setup_failure_closes_constructed_client(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A client cannot leak when writer initialization fails."""
    client = FixtureClient(harness)
    monkeypatch.setattr("gc_stem.cli.create_client", lambda settings: client)
    monkeypatch.setattr(
        "gc_stem.cli.ReportWriter",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError()),
    )
    assert main(arguments(harness), environment={}) == 1
    assert client.closed
