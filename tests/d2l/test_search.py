"""Test literal matching, representation fidelity, and bounded provenance."""

import pytest
from d2l_test_helpers import Harness

from gc_stem.d2l.models import AuthoredField, RepresentationOutcome
from gc_stem.d2l.search import compile_targets, match_field


@pytest.mark.parametrize("term", ["", " ", "\n", "\t"])
def test_blank_targets_are_rejected(term: str) -> None:
    """Empty targets cannot match every position in a field."""
    with pytest.raises(ValueError):
        compile_targets([term])


@pytest.mark.parametrize("terms", [[], "needle", [1], [True], None])
def test_malformed_targets_are_rejected(terms: object) -> None:
    """Target strings are explicit ordered inputs rather than truthy scalars."""
    with pytest.raises((ValueError, TypeError)):
        compile_targets(terms)


def test_targets_keep_order_whitespace_and_exact_deduplication() -> None:
    """Only exact duplicates are removed; original significant text is kept."""
    plan = compile_targets([" needle ", "a.b?", " needle ", "NEEDLE"])
    assert [item.target_id for item in plan.targets] == ["T001", "T002", "T003"]
    assert [item.text for item in plan.targets] == [
        " needle ",
        "a.b?",
        "NEEDLE",
    ]


@pytest.mark.parametrize(
    "term", ["a.b?", "[abc]", "a+b", "^needle$", "\\d+", "(a|b)"]
)
def test_metacharacters_remain_literal(harness: Harness, term: str) -> None:
    """Regex punctuation is searched exactly as authored."""
    field = harness.text(harness.ref(), f"before {term} after {term}")
    batch = match_field(field, compile_targets([term]), "text")
    assert batch.matches[0].occurrence_count == 2
    assert batch.matches[0].first_offset == 7


@pytest.mark.parametrize("ignore_case,count", [(True, 3), (False, 1)])
def test_case_rules_are_independent(
    harness: Harness, ignore_case: bool, count: int
) -> None:
    """Sensitive and insensitive plans use their declared rules."""
    batch = match_field(
        harness.text(harness.ref(), "needle NEEDLE Needle"),
        compile_targets(["needle"], ignore_case),
        "text",
    )
    assert batch.matches[0].occurrence_count == count


def test_nonoverlapping_counts_and_independent_terms(harness: Harness) -> None:
    """Every target gets its own finding; overlapping starts are not counted."""
    batch = match_field(
        harness.text(harness.ref(), "aaaa missing-other"),
        compile_targets(["aa", "aaaa", "absent"]),
        "text",
    )
    assert [
        (item.target.text, item.occurrence_count) for item in batch.matches
    ] == [("aa", 2), ("aaaa", 1)]


def test_unicode_offsets_reference_original_string(harness: Harness) -> None:
    """Offsets count Unicode code points, not UTF-8 bytes or casefold output."""
    batch = match_field(
        harness.text(harness.ref(), "🐍é Needle"),
        compile_targets(["needle"]),
        "text",
    )
    assert batch.matches[0].first_offset == 3
    assert batch.matches[0].context == "🐍é Needle"
    assert not match_field(
        harness.text(harness.ref(), "straße"),
        compile_targets(["STRASSE"]),
        "text",
    ).matches


@pytest.mark.parametrize("offset", [0, 50, 350, 799])
def test_context_is_bounded_and_contains_first_match(
    harness: Harness, offset: int
) -> None:
    """Long fields retain only a useful bounded excerpt around the first hit."""
    value = "x" * offset + "needle" + "y" * (800 - offset)
    match = match_field(
        harness.text(harness.ref(), value), compile_targets(["needle"]), "text"
    ).matches[0]
    assert len(match.context) == 200
    assert "needle" in match.context
    assert match.first_offset == offset


def test_long_target_still_has_bounded_context(harness: Harness) -> None:
    """A target longer than the context budget does not expand retained data."""
    term = "z" * 500
    match = match_field(
        harness.text(harness.ref(), term), compile_targets([term]), "text"
    ).matches[0]
    assert match.context == "z" * 200
    assert match.occurrence_count == 1


def test_source_dom_and_text_keep_their_own_offsets(harness: Harness) -> None:
    """Each representation keeps its own content and original offsets."""
    ref = harness.ref()
    field = AuthoredField(
        ref,
        "body",
        "html",
        (
            RepresentationOutcome("source", "AVAILABLE", "<!-- needle -->"),
            RepresentationOutcome("dom", "AVAILABLE", "<p>other</p>"),
            RepresentationOutcome("text", "AVAILABLE", "needle"),
        ),
        "synthetic_html",
    )
    batch = match_field(field, compile_targets(["needle"]), "all")
    assert [
        (item.representation, item.first_offset) for item in batch.matches
    ] == [("source", 5), ("text", 0)]
    assert batch.searched == ("source", "dom", "text")


@pytest.mark.parametrize(
    "state,code",
    [
        ("UNAVAILABLE", "REPRESENTATION_UNAVAILABLE"),
        ("NOT_APPLICABLE", "INVALID_APPLICABILITY"),
    ],
)
def test_html_missing_required_representation_is_a_gap(
    harness: Harness, state: str, code: str
) -> None:
    """Missing source cannot be labeled a successful empty authored field."""
    field = AuthoredField(
        harness.ref(),
        "body",
        "html",
        (
            RepresentationOutcome("source", state, reason="AUTH_SECRET"),
            RepresentationOutcome("dom", "AVAILABLE", "needle"),
        ),
        "synthetic_html",
    )
    batch = match_field(field, compile_targets(["needle"]), "all")
    assert len(batch.matches) == 1
    assert [item.reason_code for item in batch.gaps] == [
        code,
        "REPRESENTATION_MISSING",
    ]
    assert "AUTH_SECRET" not in repr(batch)


@pytest.mark.parametrize("mode", ["source", "dom", "text", "all"])
def test_plain_text_needs_no_fabricated_html(
    harness: Harness, mode: str
) -> None:
    """Plain authored titles remain searchable in every requested mode."""
    batch = match_field(
        harness.text(harness.ref()), compile_targets(["needle"]), mode
    )
    assert batch.complete
    assert batch.searched == ("text",)


@pytest.mark.parametrize(
    "mode,found",
    [("source", True), ("dom", True), ("all", True), ("text", False)],
)
def test_url_values_are_data_without_navigation(
    harness: Harness, mode: str, found: bool
) -> None:
    """URL-only targets are searched in declared modes, never fetched."""
    field = AuthoredField(
        harness.ref(),
        "href.raw",
        "url",
        (
            RepresentationOutcome(
                "url", "AVAILABLE", "https://unreachable.invalid/needle?a=1&b=2"
            ),
        ),
        "synthetic_attribute",
    )
    batch = match_field(field, compile_targets(["needle"]), mode)
    assert bool(batch.matches) is found
    assert batch.complete


def test_available_empty_field_is_successful(harness: Harness) -> None:
    """An empty successfully read representation contributes coverage."""
    batch = match_field(
        harness.text(harness.ref(), ""), compile_targets(["needle"]), "text"
    )
    assert batch.complete and batch.searched == ("text",) and not batch.matches


def test_oversized_representation_is_not_truncated(harness: Harness) -> None:
    """A size limit cannot manufacture a negative from a truncated field."""
    batch = match_field(
        harness.text(harness.ref(), "xxxxxneedle"),
        compile_targets(["needle"]),
        "text",
        max_characters=5,
    )
    assert not batch.matches and not batch.searched
    assert batch.gaps[0].reason_code == "FIELD_SIZE_LIMIT"


def test_match_keeps_owner_field_target_and_provenance(
    harness: Harness,
) -> None:
    """Bounded results retain exact review identity and provenance."""
    field = harness.text(harness.ref(), path="title")
    match = match_field(field, compile_targets(["needle"]), "text").matches[0]
    assert match.owner == field.owner and match.field_path == "title"
    assert match.extraction_method == field.extraction_method
    assert not hasattr(match, "outcomes")


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_bad_matching_limits_are_rejected(
    harness: Harness, limit: object
) -> None:
    """Invalid size controls do not silently disable a field bound."""
    with pytest.raises((TypeError, ValueError)):
        match_field(
            harness.text(harness.ref()),
            compile_targets(["needle"]),
            "text",
            max_characters=limit,
        )


def test_invalid_mode_does_not_fall_back(harness: Harness) -> None:
    """Unknown representation selection is an error."""
    with pytest.raises(ValueError):
        match_field(
            harness.text(harness.ref()), compile_targets(["needle"]), "anything"
        )


def test_ignore_case_requires_boolean() -> None:
    """Truthy strings cannot silently change matching semantics."""
    with pytest.raises(TypeError):
        compile_targets(["needle"], "false")
