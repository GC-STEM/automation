"""Match literal targets against explicitly labeled authored field values.

HTML fields require source/DOM/text according to mode. Plain text fields are
searched as text in every mode. URL fields are searched in source, DOM, and
all modes; visible link text belongs in a separate text field. URL attributes
must be supplied by adapters as URL fields, with raw/resolved field paths.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import get_args

from .models import (
    MAX_CONTEXT_CHARACTERS,
    AuthoredField,
    Match,
    Representation,
    SearchMode,
    Target,
)


@dataclass(frozen=True, slots=True)
class SearchPlan:
    """Hold literal patterns and original targets from compile_targets()."""

    targets: tuple[Target, ...]
    patterns: tuple[re.Pattern[str], ...]

    def __post_init__(self) -> None:
        """Reject regex patterns and mutable or inconsistent literal plans."""
        if (
            not isinstance(self.targets, tuple)
            or not isinstance(self.patterns, tuple)
            or not self.targets
            or len(self.targets) != len(self.patterns)
            or len({item.target_id for item in self.targets})
            != len(self.targets)
        ):
            raise ValueError(
                "Use compile_targets() for immutable literal plans."
            )
        for target, pattern in zip(self.targets, self.patterns, strict=True):
            expected_flags = re.UNICODE | (
                re.IGNORECASE if target.ignore_case else 0
            )
            if (
                not isinstance(pattern, re.Pattern)
                or pattern.pattern != re.escape(target.text)
                or pattern.flags != expected_flags
            ):
                raise ValueError(
                    "Search plans may contain only escaped literal patterns."
                )


@dataclass(frozen=True, slots=True)
class RepresentationGap:
    """Describe requested work unavailable to the matcher, without raw data."""

    representation: Representation
    reason_code: str


@dataclass(frozen=True, slots=True)
class MatchBatch:
    """Return bounded findings, searched representations, and coverage gaps."""

    matches: tuple[Match, ...]
    searched: tuple[Representation, ...]
    gaps: tuple[RepresentationGap, ...]

    @property
    def complete(self) -> bool:
        """Return whether all representations required for this mode worked."""
        return not self.gaps


def compile_targets(
    terms: Sequence[str], ignore_case: bool = True
) -> SearchPlan:
    """Compile unique literal targets in their original input order.

    Args:
        terms: Nonempty ordered strings; meaningful whitespace is retained.
        ignore_case: Use Python's Unicode-aware re.IGNORECASE when true.

    Returns:
        Patterns escaped with re.escape and targets numbered T001 onward.
        Only exact duplicate strings are removed; case variants stay distinct.

    Raises:
        TypeError: For a scalar string, invalid sequence, or nonboolean flag.
        ValueError: For an empty list or blank target.

    Matching uses nonoverlapping occurrences and does not claim full Unicode
    case-fold equivalence. No user-supplied regex is executed.
    """
    if isinstance(terms, (str, bytes)) or not isinstance(terms, Sequence):
        raise TypeError("terms must be an ordered sequence of strings.")
    if not isinstance(ignore_case, bool):
        raise TypeError("ignore_case must be a boolean.")
    unique: dict[str, None] = {}
    for term in terms:
        if not isinstance(term, str):
            raise TypeError("Each target must be a string.")
        if not term.strip():
            raise ValueError("Targets must not be blank.")
        unique.setdefault(term, None)
    if not unique:
        raise ValueError("At least one target is required.")
    flags = re.IGNORECASE if ignore_case else 0
    targets = tuple(
        Target(f"T{index:03d}", term, ignore_case)
        for index, term in enumerate(unique, start=1)
    )
    return SearchPlan(
        targets=targets,
        patterns=tuple(
            re.compile(re.escape(item.text), flags) for item in targets
        ),
    )


def _required(
    field: AuthoredField, mode: SearchMode
) -> tuple[Representation, ...]:
    """Select field-type representations without substituting missing values."""
    if field.field_type == "text":
        return ("text",)
    if field.field_type == "url":
        return () if mode == "text" else ("url",)
    extra_url = any(
        outcome.name == "url" and outcome.state != "NOT_APPLICABLE"
        for outcome in field.outcomes
    )
    if mode == "all":
        return (
            ("source", "dom", "text", "url")
            if extra_url
            else ("source", "dom", "text")
        )
    if mode == "dom" and extra_url:
        return ("dom", "url")
    return (mode,)


def _context(value: str, offset: int, length: int) -> str:
    """Take up to 200 original Unicode code points around the first match."""
    room = MAX_CONTEXT_CHARACTERS - min(length, MAX_CONTEXT_CHARACTERS)
    start = max(0, offset - room // 2)
    end = min(len(value), start + MAX_CONTEXT_CHARACTERS)
    start = max(0, end - MAX_CONTEXT_CHARACTERS)
    return value[start:end]


def match_field(
    field: AuthoredField,
    plan: SearchPlan,
    mode: SearchMode,
    *,
    max_characters: int | None = None,
) -> MatchBatch:
    """Search each required available representation independently.

    Args:
        field: One normalized authored field, not a whole browser page.
        plan: Result of compile_targets().
        mode: source, dom, text, or all.
        max_characters: Optional positive limit per representation. Oversized
            values produce gaps and are not silently truncated.

    Returns:
        One Match per representation/target with count, first offset, and
        bounded original context. Raw field values are not retained.

    Raises:
        TypeError: For invalid record/limit types.
        ValueError: For an unsupported mode, invalid plan, or nonpositive limit.
    """
    if not isinstance(field, AuthoredField) or not isinstance(plan, SearchPlan):
        raise TypeError("field and plan must be normalized search records.")
    if mode not in get_args(SearchMode):
        raise ValueError("Unsupported search mode.")
    if not plan.targets or len(plan.targets) != len(plan.patterns):
        raise ValueError("Use compile_targets() to construct a search plan.")
    if max_characters is not None:
        if isinstance(max_characters, bool) or not isinstance(
            max_characters, int
        ):
            raise TypeError("max_characters must be an integer.")
        if max_characters <= 0:
            raise ValueError("max_characters must be positive.")
    outcomes = {item.name: item for item in field.outcomes}
    matches: list[Match] = []
    searched: list[Representation] = []
    gaps: list[RepresentationGap] = []
    for name in _required(field, mode):
        outcome = outcomes.get(name)
        if outcome is None or outcome.state != "AVAILABLE":
            code = "REPRESENTATION_MISSING"
            if outcome is not None:
                code = (
                    "REPRESENTATION_UNAVAILABLE"
                    if outcome.state == "UNAVAILABLE"
                    else "INVALID_APPLICABILITY"
                )
            gaps.append(RepresentationGap(name, code))
            continue
        value = outcome.value
        if not isinstance(value, str):
            raise TypeError("Available representations must contain strings.")
        if max_characters is not None and len(value) > max_characters:
            gaps.append(RepresentationGap(name, "FIELD_SIZE_LIMIT"))
            continue
        searched.append(name)
        for target, pattern in zip(plan.targets, plan.patterns, strict=True):
            count, offset, length = 0, 0, 0
            for occurrence in pattern.finditer(value):
                if count == 0:
                    offset = occurrence.start()
                    length = occurrence.end() - offset
                count += 1
            if count:
                matches.append(
                    Match(
                        owner=field.owner,
                        field_path=field.field_path,
                        representation=name,
                        target=target,
                        occurrence_count=count,
                        first_offset=offset,
                        context=_context(value, offset, length),
                        extraction_method=field.extraction_method,
                    )
                )
    return MatchBatch(tuple(matches), tuple(searched), tuple(gaps))
