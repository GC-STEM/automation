# GC-STEM D2L Automation | Software Design Description

> **Proposed design, not implemented behavior.** Browser-first direction and broader search are confirmed. Interfaces, defaults, statuses, and schemas in this document form the proposed implementation contract.

## Table of Contents <!-- omit from toc -->

* [Purpose and Scope](#purpose-and-scope)
* [Design Overview](#design-overview)
* [Component and Module Design](#component-and-module-design)
* [Data Design](#data-design)
* [Interface Design](#interface-design)
* [Control and Behavioral Design](#control-and-behavioral-design)
* [Error Handling, Fault Tolerance, and Recovery](#error-handling-fault-tolerance-and-recovery)
* [Security and Privacy Design](#security-and-privacy-design)
* [Logging, Monitoring, and Diagnostics](#logging-monitoring-and-diagnostics)
* [Configuration and Environment Design](#configuration-and-environment-design)
* [Performance and Resource Design](#performance-and-resource-design)
* [Design Patterns and Reuse](#design-patterns-and-reuse)
* [Design Decisions and Rationale](#design-decisions-and-rationale)
* [Design Verification and Traceability](#design-verification-and-traceability)
* [Open Issues and Deferred Design Work](#open-issues-and-deferred-design-work)
* [References](#references)

## Purpose and Scope

### Purpose

Define enough detail to implement the requirements without coupling login, tool navigation, matching, and output. Keep the first implementation straightforward and make uncertainty visible in reports.

### Design Scope

Local workbook preparation and sequential browser search across the seven required authored-content tool areas. API, regex, persistent sessions, cache/resume, non-HTML parsing, and modification tools are deferred.

### Design Inputs

* [Requirements](./10_requirements.md) and [architecture](./19_architecture.md).
* Current `config/d2l.toml`, workbook utility, empty module scaffolds, and legacy experiments at [commit 196cda4](https://github.com/GC-STEM/automation/tree/196cda43adf48a8b3b74b3ea03101763bcb0f67f).
* Project-owner constraints and clarifications recorded in the [README](./README.md).
* PEP 8/257, existing LF text settings, and the current Python 3.12 CI context.

### Definitions, Acronyms, and Abbreviations

**Stored source** means the authored HTML string available from the owning object/view or its normal read response, not necessarily original HTTP bytes. **DOM** means a serialized authored fragment after the browser renders it. **Visible text** excludes navigation and nonvisible markup. **Review location** is either a direct object URL or a containing page with a precise object path.

## Design Overview

### Design Approach

Use functions and typed records for local data, matching, and output. Use small protocols for external reads. Keep the orchestration explicit: validate, authenticate, discover, read, match, account, write, close.

### Design Diagram

The **Architecture** page in [23_diagram.drawio](./23_diagram.drawio) shows responsibility boundaries. The **Search workflow** page shows loops, incomplete paths, session handling, and finalization. The [PDL](./29_pdl.md) gives Python-oriented contracts; the [pseudocode](./26_pseudocode.txt) gives language-independent logic.

### Design Responsibilities

| Responsibility | Owner |
| --- | --- |
| Settings, path origins, supported options | `config.py` and CLI |
| Workbook/CSV normalization and course scope | `courses.py` / `extract_course_urls.py` |
| Browser lifecycle, identity check, guarded requests | `browser.py` / `auth.py` |
| Tool enumeration and authored-field extraction | `tools/*` |
| Course/tool sequencing and limits | `content.py` |
| Shared records and status values | `models.py` |
| Literal target matching | `search.py` |
| Coverage, spool, stable CSV/JSON output | `reports.py` |

## Component and Module Design

### Configuration and Inventory Services

#### Purpose and Responsibilities

Realize FR-001–FR-004, FR-018, FR-020, and NFR-009. Resolve settings before network access; normalize course inventory; preserve the existing workbook operation.

#### Public Interface

* `load_settings(config_path, overrides, environment) -> Settings`.
* `load_courses(settings) -> Inventory`, containing validated courses, source metadata, and duplicate diagnostics.
* `extract_course_urls(source, destination, *, sheet_name="D2L", overwrite=False) -> ExtractionResult`.
* `validate_inputs(settings) -> ValidationReport`, with no browser/login side effects.

These are planned interfaces. The current extractor accepts only source/destination and returns an integer.

#### Internal Structure

Keep parsing, validation, URL-to-ID extraction, deduplication, and workbook writing separate. Preserve original row numbers for diagnostics. Resolve each path according to where it was supplied.

#### Dependencies

Standard library TOML/CSV/JSON/pathlib/urllib parsing plus openpyxl for Excel. No browser import.

#### Algorithms and Logic

For Excel search, read `CourseURL` and `D2l_course_name` from the configured worksheet. Accept an optional configured OrgUnitID column. For CSV, read `org_unit_id` and optional `course_name`/`course_url`.

Normalize IDs as positive decimal strings. Accept Excel numeric IDs only if integral; reject booleans, fractions, nonpositive values, and ambiguous scientific-notation strings. Derive IDs only from recognized tenant course-home routes, including the current inventory's `/d2l/p/home/ID` form and `/d2l/home/ID`. Any additional form requires an explicit parser/test.

If ID and URL both exist, they must agree. If only ID exists, build a course-home URL with the provider's tested route builder. A missing processed `CourseURL` must produce a preparation instruction, not silently modify the input workbook.

Deduplicate by normalized tenant origin and OrgUnitID, preserving first input order. Record duplicate rows and nonfatal display-name differences. Reject identity conflicts and invalid rows before login.

#### Data Used or Produced

Settings, normalized courses, inventory digest, row-level validation diagnostics, and the processed workbook.

#### Error and Exception Behavior

Raise `ConfigurationError` or `InventoryError` before opening Brightspace. Report missing workbook/sheet/header and duplicate normalized headers specifically. Do not infer IDs from a course title.

For workbook preparation, create destination parents, write a temporary workbook, and replace the destination only after success. Refuse source/destination identity and preexisting output unless the caller explicitly requests overwrite. The default preserves the source.

### Read Client, Browser Provider, and Authentication

#### Purpose and Responsibilities

Realize FR-005, FR-015–FR-016, FR-021, and the session/security constraints. Offer read operations without exposing provider objects to business logic.

#### Public Interface

`BrightspaceReadClient` is a context manager with `authenticate()`, `capabilities(course, tools)`, `discover(course, tool)`, and `read_object(ref)`. Discovery yields references plus an explicit terminal enumeration outcome. Reads return authored fields and representation availability.

The browser implementation is proposed as `BrowserClient`. `api.py` does not claim usable API behavior; selecting it raises an unsupported-provider configuration error in the first release.

#### Internal Structure

`browser.py` owns Playwright startup, context/page lifetime, pacing, route/navigation guard, and the adapter registry. `auth.py` owns the interactive login state machine and tenant/authenticated-sentinel check.

Before crawl, validate permitted tenant routes and explicitly required shell asset hosts. During login, the operator interacts with normal institutional identity pages. After login, do not navigate to arbitrary hosts or follow course-authored external links.

#### Dependencies

Proposed Playwright sync API, settings, typed records, and tool adapters. Authentication does not depend on search targets or reports.

#### Algorithms and Logic

Launch a headed isolated context; navigate to the configured instance; wait up to the configured authentication timeout for manual login. Confirm both the expected tenant and a verified authenticated marker. A generic HTTP 200 or absence of a password form is insufficient.

On session expiry, suspend crawl actions. Allow at most the configured number of interactive reauthentications per run (proposed default: one), each within the configured timeout. Retry the unfinished safe read after successful authentication; preserve completed identities. A declined/timed-out login stops the run with unfinished scope recorded.

#### Data Used or Produced

In-memory browser/session context, verified tenant identity, capabilities, object references, authored fields, and typed failure events. Do not export cookies or authorization headers.

#### Error and Exception Behavior

Use `AuthenticationRequired`, `AuthenticationFailed`, `AccessDenied`, `UnsupportedView`, `TransientReadError`, `ReadTimeout`, and `UnsafeActionBlocked`. Detect permission failures and unexpected page structure; do not interpret them as an empty list. An unsafe action or unexpected mutation attempt stops the live session and fails the run.

### Tool Adapters and Traversal Coordinator

#### Purpose and Responsibilities

Realize FR-006–FR-009 and ensure the broader scope is independent of Content links.

#### Public Interface

Each registered adapter provides `discover` and `read_object`, declares its authored-field families, and returns explicit enumeration/field outcomes. `scan_courses(settings, inventory, client, writer) -> RunResult` coordinates adapters.

#### Internal Structure

Provide seven adapters keyed `content`, `files`, `announcements`, `assignments`, `discussions`, `quizzes`, and `question_library`. Shared utilities handle nested lists, pagination tokens, locators, frames, and canonical identity. Keep tool-specific selectors and read routes inside the adapter.

#### Dependencies

Read session, configuration, model records, field extraction utilities, matcher, and writer. No direct workbook loading or global credential access.

#### Algorithms and Logic

Enumerate each selected tool independently. Use a work queue/stack for modules, file folders, sections, or question groups. Maintain visited identities and pagination signatures. Repeated nonterminal cursors, cycles that prevent enumeration, or unknown counts trigger incomplete coverage.

Required extraction rules:

| Area | Design rule |
| --- | --- |
| Content | Separate module descriptions, topic descriptions, HTML bodies, and link-target fields. Do not confuse a wrapper page with the authored HTML. |
| Manage Files | Traverse permitted folders; inspect HTML/HTM only. Keep file paths as identity when no file ID exists. Do not execute an HTML file merely to obtain source. |
| Announcements | Enumerate relevant listing tabs/date states and record visibility filters. |
| Assignments | Extract authored instructions; never open submissions/evaluation views. |
| Discussions | Read forum/topic configuration/prompts only. Do not enumerate posts to find instructor contributions. |
| Quizzes | Read authoring/read-only source fields without changing controls or starting an attempt. A preview sample cannot stand in for all questions. |
| Question Library | Enumerate unused questions and sections independently. If bank/pool membership or a field type cannot be fully inspected, report the gap. |

Source can be read from normal authenticated read responses or unmodified editor/view models where available. The first release must not invent direct calls to undocumented private endpoints.

Wait for expected elements/field readiness, not fixed sleeps. Pacing is a separate load control. Use semantic locators first; fall back to tested stable selectors. Inspect authored fragments in required frames/open shadow roots explicitly. Do not assume page HTML serialization contains all framed or shadow content. Closed/inaccessible roots or frames yield representation gaps.

#### Data Used or Produced

Object references, field records, enumeration outcomes, exclusion records, and coverage events.

#### Error and Exception Behavior

Catch scoped read failures, record their cause, and continue independent objects when safe. Do not catch every exception and return an empty list. Unknown tool structures and unsupported question fields remain visible failures.

### Domain Records and Matcher

#### Purpose and Responsibilities

Realize FR-009–FR-012 using provider-independent data.

#### Public Interface

`compile_targets(terms, ignore_case) -> SearchPlan` and `match_field(field, plan, mode) -> MatchBatch`. Results include findings and requested-representation gaps.

#### Internal Structure

Use immutable dataclasses for identities/fields/matches and small enums for states. Represent each searchable field separately. Keep source strings and positions local to matching; store only report records afterward.

#### Dependencies

Standard library dataclasses, enum, and regular-expression functions used to implement escaped **literal** search. The browser library must not be imported.

#### Algorithms and Logic

Reject empty/whitespace-only targets but preserve meaningful leading/trailing characters in nonblank targets. Give each unique target a stable `T001`-style ID in input order. Match every target independently; there is no “all terms must appear” filter.

Use `re.escape(target)` with Python's Unicode-aware `re.IGNORECASE` for default insensitive literal matching, or no ignore-case flag for sensitive matching. Report nonoverlapping occurrences. Do not claim full Unicode case-fold equivalence. Regex syntax is treated literally; `regex=true` is an explicit unsupported option.

#### Data Used or Produced

SearchPlan, AuthoredField, Match, and representation-gap events. Exact strings, source offsets, and optional URL-value variants are separate.

#### Error and Exception Behavior

Unavailable required representations yield gaps, not empty successful searches. Fields explicitly defined as plain text do not require fictitious source/DOM variants. Unexpected matcher errors fail the field and propagate incomplete coverage.

### Reports and CLI

#### Purpose and Responsibilities

Realize FR-012–FR-020. Keep outputs consistent and operator decisions visible.

#### Public Interface

`ReportWriter.start_run(metadata)`, `record_match(match)`, `record_coverage(event)`, and `finalize(run_state) -> OutputPaths`. The CLI validates, calls one operation, prints a compact result, and maps its result to an exit code.

#### Internal Structure

Use a unique UTC run identifier and a temporary SQLite spool for report records and stable ordering. This is a local implementation detail, not a shared application database. Store bounded excerpts and metadata, not raw page HTML. Remove the spool after orderly finalization.

#### Dependencies

Standard library CSV/JSON/SQLite/pathlib/tempfile plus normalized records. The writer does not own the browser or infer scan completeness.

#### Algorithms and Logic

Write output files through temporary paths in the same run directory, flush/close them, and publish `summary.json` last as the final manifest. It records success, partial completion, failure, or cancellation. Never overwrite another run.

When serializing CSV, neutralize formula-triggering untrusted strings, including after leading whitespace/control characters. CSV quoting alone is not sufficient. Preserve the unmodified bounded value in JSON when included; CSV-safe escaping is an export transformation.

#### Data Used or Produced

The three output files described below, terminal progress, exit code, and the temporary spool.

#### Error and Exception Behavior

A report-write failure fails the run even if retrieval succeeded. Do not print “saved” until finalization succeeds. Leave any recoverable `.partial` artifacts clearly labeled and report their paths to the operator. Hard termination may leave a spool; automatic cross-run resume is not supported.

## Data Design

### Domain Model

A CourseRef owns ToolCoverage records. A tool owns ObjectRefs. An object owns AuthoredFields. Matches refer to a field, target, representation, and review location. CourseResult aggregates tool coverage; RunSummary aggregates courses.

One underlying object may be referenced from several course paths. Deduplicate the object identity while retaining its discovered locations. Distinct quiz copies and Question Library entries remain distinct unless the platform exposes an authoritative relationship.

### Data Structures

| Record | Required data / invariant |
| --- | --- |
| `CourseRef` | Tenant origin, positive `org_unit_id`, display name, validated course URL, source row references. |
| `ObjectRef` | Course, tool key, stable object key, object type/title, containing path(s), review URL, `location_kind`, identity provenance. |
| `AuthoredField` | ObjectRef, `field_path`, field type, available representation strings, explicit unavailable/not-applicable outcomes, extraction method. |
| `Target` | Stable target ID, original literal string, case rule. |
| `Match` | Target, field identity, representation, occurrence count, bounded first context, source-relative first offset, review location. |
| `ToolCoverage` | Scope, enumeration outcome, object/field counts, status, reason codes, exclusions, start/end times. |
| `CourseResult` | Tool outcomes, match status, coverage status, match/location counts. |
| `RunSummary` | Schema/software identity, state, scan interval, redacted effective settings, inventory digest, course results, counts, diagnostics. |

Counts are defined explicitly: `objects_scanned` means all requested applicable fields/representations succeeded; `objects_failed` includes partially read and not-attempted discovered objects. Excluded objects have their own count. `fields_scanned` counts successful field/representation pairs, allowing useful partial work to be distinguished from total failure. `known_total` is null when unknown; unknown is not zero.

### Persistent Storage

Proposed destination: a unique run directory below `output.directory`. Persist `matches.csv`, `coverage.csv`, and `summary.json`. No persistent page cache, credential store, or shared database is introduced.

The temporary spool contains report data and must receive the same local access protection as final reports. Cleanup cannot guarantee recovery after power loss or hard process termination.

### Data Flow and Transformation

Validate settings and inventory → obtain normal authenticated session → discover tool objects → extract field representations → apply literal matching → spool bounded report records → aggregate coverage → serialize outputs.

A raw field may be HTML-entity decoded for parsed attribute values or rendered by the existing view. These representations must remain labeled; source offsets never refer to a different transformed string.

## Interface Design

### User Interface Design

These commands are **planned**, not available in the current snapshot:

~~~powershell
gc-stem d2l courses extract-urls --source "data/raw/d2l_courses.xlsx" --destination "data/processed/d2l_courses.xlsx" --sheet "D2L"
gc-stem d2l search --config "config/d2l.local.toml" --validate-only
gc-stem d2l search --config "config/d2l.local.toml"
~~~

The quoted paths are examples from a repository-root invocation. Core library functions receive resolved paths and do not assume that working directory.

Supported search overrides are proposed as repeated `--term`/`--tool`, `--courses`, `--output`, `--mode`, and `--case-sensitive`. Repeated term/tool options replace the corresponding configured list, rather than unexpectedly adding to it.

Progress identifies current course/tool, scanned objects, findings, and gaps without displaying full authored fields or secrets. Ctrl+C requests graceful cancellation.

| Exit code | Meaning |
| ---: | --- |
| 0 | Declared scan completed; matches may be present or absent. |
| 1 | Run failed, including authentication failure, unsafe-action detection, or output failure. |
| 2 | Invalid settings/input or unavailable configured feature; no crawl started. |
| 3 | Run finished with incomplete course/tool coverage. |
| 130 | Operator canceled; saved output, if finalized, explicitly says canceled. |

### API and Service Interface Design

The read-client protocol is internal Python API. Tool adapters return data and outcomes; they do not perform arbitrary modifications.

Future Brightspace API work must separately establish supported versions, approved authentication/scopes, pagination, rate-limit behavior, field availability, and parity tests. Browser session cookies must not be treated as approval for a new API integration. An API provider may have a different capability matrix.

### File and Data Exchange Interfaces

**Workbook preparation:** Configure worksheet and header names; preserve unrelated data supported by openpyxl. A row with no external hyperlink target keeps its existing CourseURL. Internal hyperlink locations and HYPERLINK formulas are not silently treated as external hyperlink objects. Missing or malformed inputs fail specifically. Existing macros/unsupported Excel features are not promised for a general workbook format.

**Inventory:** Excel uses configured column mapping; CSV uses the normalized contract. Course names are display metadata. Conflicting IDs/URLs fail preflight.

**matches.csv — fixed columns, in order:**

~~~text
run_id,org_unit_id,course_name,course_url,tool,object_type,object_id,
object_title,object_path,page_url,location_kind,field_path,representation,
target_id,target,occurrence_count,first_offset,context,extraction_method
~~~

One row represents one unique `course/tool/object/field/representation/target` combination. Count all nonoverlapping occurrences in that representation; retain the first bounded context (maximum 200 Unicode code points). Different representations may intentionally produce separate rows. Report unique locations separately from row counts.

Use `location_kind=direct` only for a verified stable direct link. Otherwise use `container` and supply a containing page URL plus exact object path/ID. A question without a stable direct URL must not receive an invented deep link.

**coverage.csv — fixed columns, in order:**

~~~text
run_id,org_unit_id,course_name,tool,selected,status,enumeration_complete,
objects_discovered,objects_scanned,objects_failed,objects_excluded,
fields_scanned,fields_unavailable,known_total,reason_codes,exclusions,
started_at,finished_at
~~~

List values in CSV cells use JSON arrays. Every course includes rows for the seven baseline tool keys, including `NOT_SELECTED` for explicit exclusions. Future extra selected adapters add rows.

**summary.json:** `schema_version=1`; `run_id`; `run_state`; UTC `started_at`/`finished_at`; software version/commit when available; Python/browser versions; inventory SHA-256; redacted settings and declared field/visibility/representation scope; counts; per-course results; diagnostics; output filenames; and formula-escaping policy. Unknown software commit is null with a reason, not a fabricated hash. Explicitly record excluded tools and non-HTML/external/student-data boundaries.

Do not hash and report authentication data. Inventory digest supports reproducibility but does not make live course contents a snapshot.

## Control and Behavioral Design

### Main Processing Flow

Validate configuration and inventory before live access. Prepare a unique output directory/spool. Authenticate, then iterate courses and selected tools. Traverse all discovered objects within bounds; match each requested field representation and record outcomes. Aggregate course results, finalize reports, print a textual summary, and close browser/spool resources.

See [26_pseudocode.txt](./26_pseudocode.txt) for full control logic.

### State and Mode Behavior

**Tool coverage states:**

| State | Rule |
| --- | --- |
| `COMPLETE` | Enumeration ended normally and every in-scope object/field/representation was searched; a proven empty tool also qualifies. |
| `NOT_APPLICABLE` | A verified tool-specific signal proves the tool is disabled/not applicable in this course. A missing menu or access-denied view is insufficient. |
| `PARTIAL` | Some requested work succeeded, but a known or unknown gap remains. |
| `ERROR` | Required work could not be performed and no in-scope field was successfully searched. |
| `NOT_SELECTED` | Operator explicitly excluded the tool from this run. Record the exclusion. |

**Course coverage aggregation:** Ignore explicitly unselected tools when judging the declared scope, but retain them in reports. Course `COMPLETE` requires every selected tool to be COMPLETE or verified NOT_APPLICABLE. A genuine all-empty/all-NOT_APPLICABLE course can therefore be COMPLETE. With gaps, use `PARTIAL` if any selected tool/field was successfully searched or completed; otherwise `ERROR`.

**Match aggregation:** `FOUND` means at least one match. With no matches, `NOT_FOUND` requires COMPLETE course coverage; otherwise use `UNKNOWN`. Finding a match never changes incomplete coverage to complete.

**Run state:** `COMPLETE` requires every course COMPLETE and successful output finalization. Use `PARTIAL` for a completed run with scoped gaps; `FAILED` for a fatal run-level failure; `CANCELLED` for operator cancellation. The final manifest can describe all four states.

**Search modes:**

| Mode | Required applicable representations |
| --- | --- |
| `source` | Stored authored HTML, or a stored literal link-target field. |
| `dom` | Serialized rendered authored fragments plus extracted URL attribute values. |
| `text` | Visible authored text; plain authored titles/text fields are included. |
| `all` | Union of applicable source, DOM, visible text, and URL values. |

A plain-text title does not need fabricated HTML. For an HTML field, unavailable source or rendered content is a gap in a mode that requires it. Declare applicability by field contract; do not relabel a failure “not applicable.” An empty successfully extracted field is a valid empty field.

In source mode, escaped code is searched exactly as stored. Parsed URL values decode HTML entities and retain both raw attribute and resolved-URL variants as distinct field paths. Do not silently percent-decode URL paths/queries or lowercase case-sensitive URL parts. `srcset` candidates and CSS URL references require explicit parsing tests; source mode still searches their authored strings.

### Event Handling

The coordinator handles cancellation, session expiry, transient read failures, unexpected views, limit events, and write failures. It does not install background event consumers or schedule jobs.

### Concurrency and Synchronization

Sequential first release. One coordinator owns the browser page, coverage ledger, and writer. No parallel course reads or concurrent SQLite writers are planned.

## Error Handling, Fault Tolerance, and Recovery

| Condition | Response |
| --- | --- |
| Invalid configuration/inventory | Fail preflight; no login/crawl. |
| Denied tool/object | Record access failure; continue independent scope when safe. |
| Unknown selectors/view/question type | Record unsupported/incomplete extraction; no empty-success fallback. |
| Transient timeout/service failure | At most two retries after the first attempt, with bounded backoff and normal pacing. |
| 429 or explicit service cooldown | Respect advertised wait; if it exceeds the configured wait bound, stop/defer work with incomplete coverage rather than retry early. |
| Session expired | Pause reads; allow interactive reauthentication; preserve completed identities. |
| Page/object limit | Stop that scope, label truncation, and continue others if safe. |
| Unsafe action / suspected mutation | Stop browser activity and fail the run; do not retry. |
| Cancellation | Mark current and remaining work unfinished; finalize acquired report data; close resources. |
| Output failure | Fail the run, retain clearly labeled recoverable artifacts, and report actual saved paths only. |

Do not retry 403/permission errors or generic structure changes. Bound retry waits and authentication waits explicitly. Catch expected failures narrowly; unexpected defects must remain diagnosable.

## Security and Privacy Design

Use the institution's login directly. Do not accept passwords/MFA codes as program flags, TOML, or environment variables. Do not deliberately persist session state, headers, or cookies. Default diagnostics omit screenshots, HAR, traces, raw HTML, and browser storage.

Separate allowed authentication navigation from crawl navigation. After login, permit only verified tenant read routes and necessary configured asset hosts. Block authored external destinations, popup navigation, third-party frames, and unrelated tenant/cross-course reads. Keep target URLs as data.

For quizzes and Question Library, read unmodified authoring/view data without saving, changing fields, or starting a preview/attempt. Test network effects in a controlled shell. Do not assume read-only behavior from HTTP method alone. Never emit student activity or correctness weights.

## Logging, Monitoring, and Diagnostics

Use structured events with run/course/tool/object identity, event code, elapsed time, attempt number, and sanitized error text. Include progress and final counts. Do not log full field strings, auth redirects, URL query secrets, or local session state.

Use reason codes such as `ACCESS_DENIED`, `UNSUPPORTED_VIEW`, `FIELD_UNAVAILABLE`, `ENUMERATION_INCOMPLETE`, `LIMIT_REACHED`, `SESSION_LOST`, `CANCELLED`, `READ_FAILED`, and `UNSAFE_ACTION_BLOCKED`. Keep user-facing messages distinct from internal exception details.

## Configuration and Environment Design

Configuration-file paths resolve relative to that file's parent. Explicit CLI and supported environment paths resolve relative to the invocation directory. Resolve `~` deliberately; do not silently interpolate arbitrary environment placeholders in TOML.

Search requires `--config` or `D2L_CONFIG`. Supported nonsecret environment overrides are proposed as `D2L_BASE_URL`, `D2L_COURSES_FILE`, and `D2L_OUTPUT_DIRECTORY`. CLI overrides take priority. No tenant URL or course identity is a source-code default.

The following is a **proposed replacement schema**, not the current file:

~~~toml
schema_version = 1

[instance]
base_url = "https://brightspace.example.org/d2l/"
provider = "browser"
auth = "interactive"

[courses]
file = "../data/processed/d2l_courses.xlsx"
format = "xlsx"
sheet = "D2L"
name_column = "D2l_course_name"
url_column = "CourseURL"

[search]
terms = ["example.org"]
mode = "all"
ignore_case = true
regex = false

[crawl]
tools = ["content", "files", "announcements", "assignments",
         "discussions", "quizzes", "question_library"]
include_hidden = true
follow_external_links = false
delay_seconds = 1.0
read_timeout_seconds = 30
auth_timeout_seconds = 300
max_retries = 2
max_reauthentications = 1
max_retry_wait_seconds = 60
max_pages_per_course = 300
max_objects_per_tool = 1000
max_field_characters = 2000000
concurrency = 1

[browser]
headless = false
trusted_asset_hosts = []

[output]
directory = "../data/processed/d2l-search"
formats = ["csv", "json"]
~~~

The existing `max_pages_per_course` becomes a navigation/read-action bound, not a synonym for object count. The additional object/field bounds prevent one view containing many questions or huge HTML from bypassing limits. Hitting any bound records incomplete coverage. These values are provisional; tune from pilot evidence.

Trusted asset hosts are necessary shell/CDN hosts established by the tenant spike, not an unrestricted web allowlist. The schema must reject unsafe flags such as `follow_external_links=true` and `headless=true` in this first interactive release.

The current config uses DOM mode, visible-only scope, `data/courses.csv`, and `output`. Adopting the example above changes those choices and requires reviewed implementation/configuration updates.

## Performance and Resource Design

For each field/representation, literal scanning costs approximately field length times number of targets. Keep raw data to the current object, enforce field-size bounds, and spool only report records. Maintain per-run identity sets to prevent loops; their size is bounded by item limits.

Use adapter-complete pagination rather than arbitrary link recursion. No previous-run content cache is enabled. A fresh run records its scan interval because course changes during a scan can affect consistency.

## Design Patterns and Reuse

Use adapter/protocol boundaries for external access, a strategy for authentication/provider choice, and ordinary dataclasses for normalized values. Do not introduce a plugin-loading framework or a generic task engine in the first release.

Reuse the workbook utility's behavior, not its import-time repository-root assumption. Reuse legacy experiments only as inspected examples; do not import their login functions into production.

## Design Decisions and Rationale

| ID | Decision | Alternatives Considered | Rationale / Trade-offs | Related Requirements |
| --- | --- | --- | --- | --- |
| DD-001 | Relative paths retain their input origin. | Everything relative to CWD or repository root. | Config stays portable; explicit CLI paths remain conventional. | FR-001, NFR-009 |
| DD-002 | Match status and coverage are independent. | One overloaded status. | Findings and uncertainty can coexist. | FR-014 |
| DD-003 | All-mode administrative audit is the proposed default. | Current DOM/visible-only sample settings. | Better fit for source/URL maintenance search; may reveal more gaps. | FR-007–FR-011 |
| DD-004 | One row per field/representation/target with count and first context. | One row per occurrence; one row per course. | Useful locations without excessive report volume. | FR-012–FR-013 |
| DD-005 | Literal matching only in the first release. | Early regex support. | Matches the stated need and keeps semantics simple. | FR-010, FR-018 |
| DD-006 | Unique directory; temporary spool; JSON manifest published last. | In-place report overwrite. | Preserves prior runs and avoids false completion. | FR-017, FR-019 |
| DD-007 | Explicit containing-page fallback for questions. | Invented deep-link patterns. | Maintainers can find objects without unreliable links. | FR-012 |
| DD-008 | No CLI depends on a source checkout. | Import-time `pyproject.toml` root discovery. | Supports package reuse and arbitrary invocation locations. | FR-021, NFR-009 |

## Design Verification and Traceability

| Requirement / Architecture Driver | Design Element | Verification Approach |
| --- | --- | --- |
| FR-001–FR-004, ADR-002 | Configuration/inventory services | TC-001–TC-004, TC-026 |
| FR-005, ADR-001/ADR-005 | Browser authentication/session | TC-005, TC-015, TC-023 |
| FR-006–FR-008, ADR-003/ADR-008 | Seven adapters / enumeration | TC-006–TC-008, TC-021 |
| FR-009–FR-012 | Field representations / matcher / review locations | TC-009–TC-012 |
| FR-013–FR-019, ADR-006 | Reports, state rules, recovery | TC-013–TC-019 |
| FR-020–FR-022, ADR-007 | Validation CLI / reusable protocol | TC-018, TC-020, TC-025 |
| NFR-001–NFR-012 | Crosscutting controls | Complete mapping in [test plan](./40_testing.md#requirements-traceability) |

## Open Issues and Deferred Design Work

Before construction claims stable contracts, inspect the tenant's content experience, source/read responses, editor behavior, pagination, question types, hidden/draft access, and safe route set. Confirm the proposed seven-tool matrix and operating limits with the owner.

API parity, additional tool adapters, regex, persistent authentication, resumable scans, snapshot/export workflows, and binary-file parsing remain deferred. A later requirement change must update coverage semantics and tests, not just add a configuration flag.

## References

* [Requirements](./10_requirements.md), [architecture](./19_architecture.md), [PDL](./29_pdl.md), and [test plan](./40_testing.md).
* D2L, [Course content](https://docs.valence.desire2learn.com/res/content.html), [Quizzes](https://docs.valence.desire2learn.com/res/quiz.html), and [Managing questions in Question Library](https://community.d2l.com/brightspace/kb/articles/3422-managing-questions-in-question-library), consulted October 16, 2026. API resources inform future integration; they do not establish browser or SNHU availability.
* Playwright, [Authentication](https://playwright.dev/python/docs/auth) and [Locators](https://playwright.dev/python/docs/locators).
* Python, [tomllib](https://docs.python.org/3/library/tomllib.html); PyPA, [Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

<!--
title: "GC-STEM D2L Automation | Software Design Description"
document_type: "Software Design Description (SDD)"
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
