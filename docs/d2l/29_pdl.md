# GC-STEM D2L Automation | Program Design Language

> **Proposed Python-oriented contracts.** This file was empty in the source baseline. It supplements the design with interface sketches and invariants. The sketches are not a working library and must not be copied into production as a complete implementation.

## Table of Contents <!-- omit from toc -->

* [Purpose and Scope](#purpose-and-scope)
* [Type Contracts](#type-contracts)
* [Provider and Adapter Interfaces](#provider-and-adapter-interfaces)
* [Application Service Interfaces](#application-service-interfaces)
* [Configuration and Path Logic](#configuration-and-path-logic)
* [Inventory Logic](#inventory-logic)
* [Literal Matching Logic](#literal-matching-logic)
* [Coverage Aggregation Logic](#coverage-aggregation-logic)
* [Run and Failure Logic](#run-and-failure-logic)
* [Report Writer Contract](#report-writer-contract)
* [Construction Checks](#construction-checks)
* [Deferred Work and References](#deferred-work-and-references)

## Purpose and Scope

Translate the architecture and language-independent [pseudocode](./26_pseudocode.txt) into a concise construction guide. Keep provider-specific browser objects outside application, search, and reporting interfaces.

The [design](./20_design.md) owns field meanings, report columns, modes, limits, and status rules. This document must not redefine them independently.

## Type Contracts

The following illustrates type relationships; omitted fields are defined in the design tables.

~~~python
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

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


@dataclass(frozen=True)
class CourseRef:
    tenant_origin: str
    org_unit_id: str
    name: str
    course_url: str


@dataclass(frozen=True)
class ObjectRef:
    course: CourseRef
    tool: ToolKey
    object_key: str
    object_type: str
    title: str
    paths: tuple[str, ...]
    page_url: str
    location_kind: Literal["direct", "container"]


@dataclass(frozen=True)
class RepresentationOutcome:
    name: Representation
    state: Literal["AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"]
    value: str | None
    reason: str | None


@dataclass(frozen=True)
class AuthoredField:
    owner: ObjectRef
    field_path: str
    field_type: Literal["html", "text", "url"]
    outcomes: tuple[RepresentationOutcome, ...]
    extraction_method: str
~~~

A URL attribute's raw and resolved values use different field paths so their positions/counts cannot be confused. Empty `AVAILABLE` values are valid. `UNAVAILABLE` values need a reason. `NOT_APPLICABLE` must follow the field contract, not hide extraction failure.

`DiscoveryEnd`, `ReadResult`, `Match`, `Settings`, `Inventory`, and report records are additional planned dataclasses. Define them from [Data Design](./20_design.md#data-design), not from arbitrary browser response dictionaries.

## Provider and Adapter Interfaces

~~~python
class BrightspaceReadClient(Protocol):
    def authenticate(self) -> None: ...

    def capabilities(
        self, course: CourseRef, tools: tuple[ToolKey, ...]
    ) -> "CapabilitySet": ...

    def discover(
        self, course: CourseRef, tool: ToolKey
    ) -> Iterator["ObjectRef | DiscoveryEnd"]: ...

    def read_object(self, ref: ObjectRef) -> "ReadResult": ...

    def close(self) -> None: ...


class ToolAdapter(Protocol):
    key: ToolKey

    def discover(
        self, course: CourseRef, session: "ReadSession"
    ) -> Iterator["ObjectRef | DiscoveryEnd"]: ...

    def read_object(
        self, ref: ObjectRef, session: "ReadSession"
    ) -> "ReadResult": ...
~~~

The concrete client also implements context-manager lifetime. `ReadSession` is provider-private; the coordinator never sees a Playwright page/context.

**Discovery invariants:**

1. Yield each discovered platform identity once, retaining alternate containing paths.
2. Emit a trustworthy terminal `DiscoveryEnd` with enumeration completeness and reason codes.
3. A thrown exception or missing terminal outcome leaves enumeration incomplete.
4. Permission denial or a selector mismatch is not a successful empty result.
5. A verified disabled tool is NOT_APPLICABLE; a missing menu alone proves neither absence nor authorization.

**Read invariants:**

* Return the expected authored-field inventory and explicit missing-field outcomes.
* Do not include shell navigation, user/session controls, learner records, or other courses.
* Preserve extraction provenance and representation labels.
* Never modify controls, save, publish, delete, submit, evaluate, or start attempts.
* Raise typed failures; unsafe-action detection is fatal to the session.

## Application Service Interfaces

~~~python
def load_settings(
    config_path: "Path",
    overrides: Mapping[str, object],
    environment: Mapping[str, str],
) -> "Settings":
    ...


def load_courses(settings: "Settings") -> "Inventory":
    ...


def extract_course_urls(
    source: "Path",
    destination: "Path",
    *,
    sheet_name: str = "D2L",
    overwrite: bool = False,
) -> "ExtractionResult":
    ...


def compile_targets(
    terms: tuple[str, ...], ignore_case: bool
) -> "SearchPlan":
    ...


def match_field(
    field: AuthoredField,
    plan: "SearchPlan",
    mode: SearchMode,
) -> "MatchBatch":
    ...


def scan_courses(
    settings: "Settings",
    inventory: "Inventory",
    client: BrightspaceReadClient,
    writer: "ReportWriter",
) -> "RunResult":
    ...
~~~

These signatures are a proposed migration. The existing extractor currently returns an integer and uses a fixed worksheet constant. New public functions need PEP 257 docstrings describing behavior, arguments, return values, and expected exceptions during construction.

## Configuration and Path Logic

~~~text
resolve the selected configuration file
load TOML and retain its absolute parent directory
apply only documented environment overrides, retaining invocation origin
apply explicit command overrides, retaining invocation origin
fill safe defaults that do not encode institution/course/user identity
reject unknown, unsupported, unsafe, or contradictory options
resolve each path relative to its own origin
validate required local inputs and output destination
return immutable validated settings
~~~

Do not locate `pyproject.toml` at package import time. A local checkout can supply example paths through configuration. An installed package must work without the repository tree.

## Inventory Logic

~~~text
read configured Excel worksheet/headers or normalized CSV columns
for each nonempty course row:
    normalize a positive OrgUnitID if provided
    validate the tenant and recognized course-home URL if provided
    derive missing identity only through the tested route parser/builder
    reject an ID/URL conflict
    record display metadata and original row reference
deduplicate by tenant origin plus OrgUnitID in first-input order
fail preflight for invalid identity rows
return courses, nonfatal duplicate diagnostics, and input digest
~~~

Do not turn blank or malformed rows into fabricated IDs. The search operation does not rewrite its inventory.

## Literal Matching Logic

~~~python
# Illustrative core only; surrounding contracts still require implementation.
flags = re.IGNORECASE if ignore_case else 0
pattern = re.compile(re.escape(target.text), flags)
occurrences = list(pattern.finditer(representation_value))
~~~

The production implementation should count matches without retaining an unbounded list of occurrence objects. Keep only the count, first offset, and first bounded context. Literal targets with regex metacharacters remain literal. Escape source snippets for output; do not execute retrieved markup.

The report key is `course/tool/object/field/representation/target`. Matches from separate representations are intentional rows. Unique matched locations are counted independently.

## Coverage Aggregation Logic

~~~text
tool COMPLETE:
    enumeration is verified complete
    every requested applicable object/field/representation succeeded
    or the tool is verified genuinely empty

tool NOT_APPLICABLE:
    verified tool-specific absence/disabled evidence exists

tool PARTIAL:
    a requested gap exists and some scoped field work succeeded

tool ERROR:
    a requested gap exists and no scoped field work succeeded

course COMPLETE:
    every selected tool is COMPLETE or NOT_APPLICABLE

course PARTIAL:
    some selected work completed but a requested gap remains

course ERROR:
    selected scope could not be searched

match FOUND:
    at least one match exists, regardless of coverage

match NOT_FOUND:
    no matches and course COMPLETE

match UNKNOWN:
    no matches and course not COMPLETE
~~~

Explicitly unselected tools remain in coverage output as NOT_SELECTED. Limits, unsupported field types, missing source, unknown pagination, and cancellation create requested gaps. A successful empty tool counts as completed work for course aggregation even with zero fields.

## Run and Failure Logic

Use the complete flow in [26_pseudocode.txt](./26_pseudocode.txt). The application owns validation and exit codes; the client owns verified safe reads; the writer owns publication integrity.

* Preflight failures: no live session; exit 2.
* Scoped retrieval failures: continue safe independent work; run PARTIAL/exit 3.
* Session loss: suspend reads; allow bounded interactive reauthentication.
* Unsafe action, unrecovered authentication, or fatal runtime failure: run FAILED/exit 1.
* Cancellation: run CANCELLED/exit 130 if finalization succeeds.
* Any output finalization failure overrides the process outcome to exit 1.

Retry at most the configured number of transient **reads**. Never retry an operation whose read-only effect is uncertain.

## Report Writer Contract

~~~python
class ReportWriter(Protocol):
    def record_match(self, match: "Match") -> None: ...

    def record_coverage(self, event: "CoverageEvent") -> None: ...

    def finalize(self, state: RunState) -> "OutputPaths": ...

    def close(self) -> None: ...
~~~

The implementation creates a unique run directory, stores bounded report rows in a temporary local spool, and writes fixed-column CSV outputs. It publishes the final JSON manifest last.

CSV strings from course content are spreadsheet-safe. The authoritative JSON retains bounded original values when present. The manifest describes the declared scope and actual completion; it does not claim an immutable course snapshot.

## Construction Checks

| Invariant | Verification |
| --- | --- |
| Business logic imports no browser backend. | Import-boundary review; fake-client run; TC-020. |
| Missing source cannot silently become DOM source. | Representation tests; TC-009. |
| All selected tools are accounted for. | Tool matrix fixture; TC-006, TC-014. |
| Session expiry cannot become NOT_FOUND. | Fault injection; TC-015–TC-016. |
| No write/attempt routes are used. | Guard tests and controlled pilot network evidence; TC-021. |
| Installed operation works outside the checkout. | Clean-package/path tests; TC-025–TC-026. |

## Deferred Work and References

API provider, regex, saved sessions, resume/cache, and additional tool adapters are deferred. Open decisions are recorded in the [worksheet](./worksheet.md).

References: [architecture](./19_architecture.md), [design](./20_design.md), [pseudocode](./26_pseudocode.txt), [test plan](./40_testing.md), [PEP 8](https://peps.python.org/pep-0008/), and [PEP 257](https://peps.python.org/pep-0257/).

<!--
title: "GC-STEM D2L Automation | Program Design Language"
document_type: "Program Design Language (PDL)"
description: "Draft requirements and implementation guidance for reusable GC-STEM D2L tools."
owner: "GC-STEM Automation maintainers"
scope: "GC-STEM Automation / D2L"
status: "draft for review"
version: "0.1.0-draft.1"
updated: "2026-10-16T19:46:29-04:00"
source_commit: "196cda43adf48a8b3b74b3ea03101763bcb0f67f"
toc: true
tags: ["d2l", "brightspace", "automation", "draft"]
-->
