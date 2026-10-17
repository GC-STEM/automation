"""Define shared records and status values for D2L automation.

These records contain data only; they do not open files or browser sessions.
Input adapters normalize and validate tenant URLs before constructing records.
The constructors enforce identity, extraction, and match-result invariants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args


ToolKey = Literal[
    "content",
    "files",
    "announcements",
    "assignments",
    "discussions",
    "quizzes",
    "question_library",
]
Representation = Literal["source", "dom", "text", "url"]
SearchMode = Literal["source", "dom", "text", "all"]
FieldType = Literal["html", "text", "url"]
RepresentationState = Literal[
    "AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"
]
LocationKind = Literal["direct", "container"]
MatchStatus = Literal["FOUND", "NOT_FOUND", "UNKNOWN"]
CourseCoverage = Literal["COMPLETE", "PARTIAL", "ERROR"]
ToolStatus = Literal[
    "COMPLETE",
    "PARTIAL",
    "ERROR",
    "NOT_APPLICABLE",
    "NOT_SELECTED",
]
RunState = Literal["COMPLETE", "PARTIAL", "FAILED", "CANCELLED"]

MAX_CONTEXT_CHARACTERS = 200


def _require_nonblank(value: str, name: str) -> None:
    """Require a string with at least one nonwhitespace character."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if not value.strip():
        raise ValueError(f"{name} must not be blank.")


def _require_choice(value: str, choices: tuple[str, ...], name: str) -> None:
    """Require one of the documented string values."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    if value not in choices:
        raise ValueError(f"Unsupported {name}: {value!r}.")


def _require_count(value: int, name: str, minimum: int = 0) -> None:
    """Require an integer count, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer.")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}.")


@dataclass(frozen=True, slots=True)
class CourseRef:
    """Identify a normalized course from the selected inventory.

    Attributes:
        tenant_origin: Validated HTTPS origin without the /d2l path.
        org_unit_id: Canonical positive decimal ID without leading zeros.
        name: Course display name; an empty name is permitted.
        course_url: Validated course-home URL on the selected tenant.
        source_rows: One-based inventory data-row numbers, when available.

    URL parsing and tenant authorization belong to the inventory adapter.
    """

    tenant_origin: str
    org_unit_id: str
    name: str
    course_url: str
    source_rows: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """Reject blank identifiers and noncanonical course IDs."""
        _require_nonblank(self.tenant_origin, "tenant_origin")
        _require_nonblank(self.course_url, "course_url")
        _require_nonblank(self.org_unit_id, "org_unit_id")
        if (
            not self.org_unit_id.isascii()
            or not self.org_unit_id.isdecimal()
            or self.org_unit_id.startswith("0")
        ):
            raise ValueError(
                "org_unit_id must be a canonical positive decimal string."
            )
        if not isinstance(self.name, str):
            raise TypeError("name must be a string.")
        if not isinstance(self.source_rows, tuple):
            raise TypeError("source_rows must be a tuple.")
        for row in self.source_rows:
            _require_count(row, "source row", minimum=2)


@dataclass(frozen=True, slots=True)
class ObjectRef:
    """Identify one authored object and its review location.

    Attributes:
        course: Course that owns the object.
        tool: Tool adapter key.
        object_key: Stable platform ID or deterministic local identity.
        object_type: Adapter-defined object kind, such as quiz_question.
        title: Display title; may be empty.
        paths: Containing paths retained during discovery.
        page_url: Validated direct or containing-page review URL.
        location_kind: Whether page_url is direct or a container.
        identity_provenance: How object_key was obtained, such as platform
            or file_path. Adapters must supply this explicitly.
    """

    course: CourseRef
    tool: ToolKey
    object_key: str
    object_type: str
    title: str
    paths: tuple[str, ...]
    page_url: str
    location_kind: LocationKind
    identity_provenance: str

    def __post_init__(self) -> None:
        """Validate object identity and declared location metadata."""
        if not isinstance(self.course, CourseRef):
            raise TypeError("course must be a CourseRef.")
        _require_choice(self.tool, get_args(ToolKey), "tool")
        _require_nonblank(self.object_key, "object_key")
        _require_nonblank(self.object_type, "object_type")
        _require_nonblank(self.page_url, "page_url")
        _require_nonblank(self.identity_provenance, "identity_provenance")
        _require_choice(
            self.location_kind, get_args(LocationKind), "location_kind"
        )
        if not isinstance(self.title, str):
            raise TypeError("title must be a string.")
        if not isinstance(self.paths, tuple):
            raise TypeError("paths must be a tuple.")
        for path in self.paths:
            _require_nonblank(path, "object path")

    @property
    def identity(self) -> tuple[str, str, ToolKey, str]:
        """Return a deduplication key independent of titles and paths."""
        return (
            self.course.tenant_origin,
            self.course.org_unit_id,
            self.tool,
            self.object_key,
        )


@dataclass(frozen=True, slots=True)
class RepresentationOutcome:
    """Record an extracted representation or an explicit coverage gap.

    AVAILABLE requires a string value, including a valid empty string.
    UNAVAILABLE and NOT_APPLICABLE require an explanatory reason and no
    value. Applicability is determined by the adapter's field contract.
    """

    name: Representation
    state: RepresentationState
    value: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        """Prevent missing data from masquerading as an empty field."""
        _require_choice(self.name, get_args(Representation), "representation")
        _require_choice(
            self.state, get_args(RepresentationState), "representation state"
        )
        if self.state == "AVAILABLE":
            if not isinstance(self.value, str):
                raise ValueError("AVAILABLE requires a string value.")
            if self.reason is not None:
                raise ValueError("AVAILABLE must not include a gap reason.")
        else:
            if self.value is not None:
                raise ValueError(f"{self.state} must not include a value.")
            if self.reason is None:
                raise ValueError(f"{self.state} requires a reason.")
            _require_nonblank(self.reason, "representation reason")


@dataclass(frozen=True, slots=True)
class AuthoredField:
    """Hold one authored field with explicitly labeled representations.

    Attributes:
        owner: Object that owns this field.
        field_path: Stable field location within the object.
        field_type: Whether the authored value is HTML, text, or a URL.
        outcomes: One availability outcome per applicable representation.
        extraction_method: Adapter's source/view extraction strategy.
    """

    owner: ObjectRef
    field_path: str
    field_type: FieldType
    outcomes: tuple[RepresentationOutcome, ...]
    extraction_method: str

    def __post_init__(self) -> None:
        """Require explicit, unique representation outcomes."""
        if not isinstance(self.owner, ObjectRef):
            raise TypeError("owner must be an ObjectRef.")
        _require_nonblank(self.field_path, "field_path")
        _require_choice(self.field_type, get_args(FieldType), "field_type")
        _require_nonblank(self.extraction_method, "extraction_method")
        if not isinstance(self.outcomes, tuple):
            raise TypeError("outcomes must be a tuple.")
        if not self.outcomes:
            raise ValueError("A field requires representation outcomes.")
        names = []
        for outcome in self.outcomes:
            if not isinstance(outcome, RepresentationOutcome):
                raise TypeError(
                    "outcomes must contain RepresentationOutcome records."
                )
            names.append(outcome.name)
        if len(names) != len(set(names)):
            raise ValueError("A field must not repeat a representation.")


@dataclass(frozen=True, slots=True)
class FieldGap:
    """Describe an authored field that could not be extracted at all."""

    field_path: str
    reason: str

    def __post_init__(self) -> None:
        """Require an identifiable field and an explanatory gap reason."""
        _require_nonblank(self.field_path, "field_path")
        _require_nonblank(self.reason, "field gap reason")


@dataclass(frozen=True, slots=True)
class ReadResult:
    """Return one object's fields and explicitly missing fields.

    A real empty field is an AVAILABLE representation with value "".
    Returning no fields and no gaps is ambiguous and is rejected.
    Whole-object access failures are raised by the provider instead.
    """

    owner: ObjectRef
    fields: tuple[AuthoredField, ...] = ()
    missing_fields: tuple[FieldGap, ...] = ()

    def __post_init__(self) -> None:
        """Reject ambiguous reads and mismatched field ownership."""
        if not isinstance(self.owner, ObjectRef):
            raise TypeError("owner must be an ObjectRef.")
        if not isinstance(self.fields, tuple):
            raise TypeError("fields must be a tuple.")
        if not isinstance(self.missing_fields, tuple):
            raise TypeError("missing_fields must be a tuple.")
        if not self.fields and not self.missing_fields:
            raise ValueError("A read requires fields or explicit field gaps.")

        field_paths = []
        for field in self.fields:
            if not isinstance(field, AuthoredField):
                raise TypeError("fields must contain AuthoredField records.")
            if field.owner.identity != self.owner.identity:
                raise ValueError("Every field must belong to the read object.")
            field_paths.append(field.field_path)
        for gap in self.missing_fields:
            if not isinstance(gap, FieldGap):
                raise TypeError("missing_fields must contain FieldGap records.")
            field_paths.append(gap.field_path)
        if len(field_paths) != len(set(field_paths)):
            raise ValueError("A read must not repeat an authored field path.")


@dataclass(frozen=True, slots=True)
class DiscoveryEnd:
    """Identify the terminal outcome of a tool enumeration.

    known_total is None when unknown. Incomplete discovery requires an
    explicit reason; an empty complete enumeration can have total zero.
    """

    enumeration_complete: bool
    known_total: int | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Keep unknown totals and incomplete discovery explicit."""
        if not isinstance(self.enumeration_complete, bool):
            raise TypeError("enumeration_complete must be a boolean.")
        if self.known_total is not None:
            _require_count(self.known_total, "known_total")
        if not isinstance(self.reason_codes, tuple):
            raise TypeError("reason_codes must be a tuple.")
        for reason in self.reason_codes:
            _require_nonblank(reason, "discovery reason")
        if not self.enumeration_complete and not self.reason_codes:
            raise ValueError("Incomplete discovery requires a reason.")


@dataclass(frozen=True, slots=True)
class Target:
    """Identify a literal search string without changing its characters."""

    target_id: str
    text: str
    ignore_case: bool = True

    def __post_init__(self) -> None:
        """Reject empty targets while preserving meaningful whitespace."""
        _require_nonblank(self.target_id, "target_id")
        _require_nonblank(self.text, "target text")
        if not isinstance(self.ignore_case, bool):
            raise TypeError("ignore_case must be a boolean.")


@dataclass(frozen=True, slots=True)
class Match:
    """Summarize one target's occurrences in a field representation.

    Attributes:
        owner: Object and review-location metadata.
        field_path: Matched field's stable path.
        representation: Representation actually searched.
        target: Literal target and case rule.
        occurrence_count: Positive count of nonoverlapping matches.
        first_offset: Zero-based offset in that representation's string.
        context: Bounded excerpt around the first occurrence.
        extraction_method: How the searched data was obtained.

    Raw AuthoredField data is deliberately not retained in this record.
    """

    owner: ObjectRef
    field_path: str
    representation: Representation
    target: Target
    occurrence_count: int
    first_offset: int
    context: str
    extraction_method: str

    def __post_init__(self) -> None:
        """Validate counts, provenance, and the bounded excerpt contract."""
        if not isinstance(self.owner, ObjectRef):
            raise TypeError("owner must be an ObjectRef.")
        if not isinstance(self.target, Target):
            raise TypeError("target must be a Target.")
        _require_nonblank(self.field_path, "field_path")
        _require_choice(
            self.representation, get_args(Representation), "representation"
        )
        _require_count(self.occurrence_count, "occurrence_count", minimum=1)
        _require_count(self.first_offset, "first_offset")
        _require_nonblank(self.extraction_method, "extraction_method")
        if not isinstance(self.context, str):
            raise TypeError("context must be a string.")
        if len(self.context) > MAX_CONTEXT_CHARACTERS:
            raise ValueError(
                f"context must not exceed {MAX_CONTEXT_CHARACTERS} characters."
            )
