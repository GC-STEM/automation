# GC-STEM D2L Automation | Software Architecture Description

> **Draft architecture.** Browser-first access is confirmed direction. The component contracts, package migration, Playwright choice, and seven-tool baseline are proposed.

## Table of Contents <!-- omit from toc -->

* [Purpose and Scope](#purpose-and-scope)
* [Architecture Context](#architecture-context)
* [Architecture Overview](#architecture-overview)
* [Architecture Views](#architecture-views)
* [Interfaces and Integration](#interfaces-and-integration)
* [Quality Attribute Strategies](#quality-attribute-strategies)
* [Technology Stack and Platform Decisions](#technology-stack-and-platform-decisions)
* [Dependencies and Supply-Chain Considerations](#dependencies-and-supply-chain-considerations)
* [Architectural Decisions and Rationale](#architectural-decisions-and-rationale)
* [Architecture Risks and Technical Debt](#architecture-risks-and-technical-debt)
* [Architecture Evaluation](#architecture-evaluation)
* [Traceability to Detailed Design and Testing](#traceability-to-detailed-design-and-testing)
* [Open Issues](#open-issues)
* [References](#references)

## Purpose and Scope

### Purpose

Keep institutional authentication, Brightspace navigation, tool-specific extraction, and search/reporting independent. Define boundaries that let future D2L tools reuse the library without copying login code or depending on search internals.

### Architecture Scope

This description covers local inventory preparation and a read-only, multiple-course search across the [proposed tool matrix](./10_requirements.md#in-scope). It includes a browser provider, common records, coverage accounting, and local output. API integration and content-changing operations remain outside this increment.

### Intended Audience

Developers, maintainers, testers, course owners reviewing search scope, and administrators assessing integration boundaries.

### Definitions, Acronyms, and Abbreviations

* **Provider:** A backend that offers the read-client contract; browser first, API later.
* **Adapter:** A tool-specific implementation that discovers objects and reads authored fields.
* **Coordinator:** Application logic that validates inputs, controls scanning, and combines results.
* **Capability:** An explicitly supported tool, field, representation, and visibility combination.
* **ADR:** An architectural decision record.

## Architecture Context

### Requirements and Architectural Drivers

| Driver / ASR | Source | Architectural Significance |
| --- | --- | --- |
| FR-005, FR-022 | [Requirements](./10_requirements.md) | Browser login must work independently of future API availability. |
| FR-006–FR-008 | Requirements | Tool areas require independent enumeration; Content links are insufficient. |
| FR-009–FR-014 | Requirements | Retrieval, representations, matching, and coverage must remain separate. |
| FR-021, NFR-007 | Requirements | Future operations need reusable access components and offline tests. |
| NFR-003–NFR-005 | Requirements | Read-only behavior, ephemeral authentication, and data minimization define trust boundaries. |
| NFR-001, NFR-009, NFR-011 | Requirements | Bound network load, avoid checkout-dependent paths, and stream course data. |

### Stakeholders and Concerns

| Stakeholder | Architectural Concerns | Relevant View(s) |
| --- | --- | --- |
| Operator | Reliable locations, understandable gaps, safe cancellation. | Scenario, runtime, information. |
| Course owner | Correct authored content and visibility scope. | Logical, information. |
| Developer / maintainer | Replace login/provider code; add adapters; package normally. | Module, interfaces, decisions. |
| Administrator / security contact | Existing permissions, safe routes, service load, restricted output. | Context, deployment, quality strategies. |

### System Context

The application runs on an operator-controlled workstation. Local files supply inventory and nonsecret settings. The browser connects to Brightspace and the institution's normal identity services. Reports remain local.

There are three meaningful boundaries:

1. **Local inputs to the application:** Validate IDs, URLs, paths, targets, and settings before live access.
2. **Application/browser to institutional services:** Use normal authentication and existing authorization; restrict crawl actions to validated reads.
3. **Retrieved content to persistent reports:** Emit location metadata and bounded matching context; do not persist full course pages or authentication state.

The authorized course list is a boundary. Tool adapters do not crawl arbitrary links, neighboring OrgUnits, or all courses available to the account.

### Assumptions and Constraints

The current repository has scaffolds, not a working crawler. The SNHU login flow, content experience, read routes, and field availability must be proven in a pilot. The first release is interactive and sequential. Existing role permissions remain authoritative.

## Architecture Overview

### Architectural Style or Pattern

Use a **modular Python application with adapters**. The command-line layer calls application services. Application logic depends on small read interfaces and plain data records. Providers and tool adapters implement the external interactions.

No microservices, message broker, shared database, dependency-injection framework, or background worker is required. A local temporary report spool may use SQLite for bounded-memory sorting.

### Major Architectural Elements

| Element | Responsibility | Interfaces / Dependencies | Related Requirements |
| --- | --- | --- | --- |
| CLI and configuration | Parse explicit inputs; validate effective settings; display progress and exit status. | Application services; TOML/environment/arguments. | FR-001, FR-018, FR-020 |
| Inventory services | Extract Excel URLs; normalize workbook/CSV courses; validate scope. | openpyxl; CSV; path/URL validation. | FR-002–FR-004 |
| Run coordinator | Iterate courses/tools; enforce limits; combine failures, matches, and coverage. | Read client, matcher, report writer. | FR-006–FR-017 |
| Read-client contract | Describe lifecycle, capabilities, discovery, and authored-field retrieval. | Provider-independent records and exceptions. | FR-021–FR-022 |
| Browser provider and authentication | Launch/close isolated context; let user log in; validate tenant/session; enforce safe reads. | Proposed Playwright; institutional web UI. | FR-005, NFR-003–NFR-005 |
| Tool adapters | Enumerate one tool and read its authored fields using validated view strategies. | Browser session; field/capability contracts. | FR-006–FR-009 |
| Matcher | Find literal targets in explicitly labeled representations. | Plain records; no browser import. | FR-009–FR-012 |
| Reports and coverage | Preserve rows; derive independent statuses; write CSV and final JSON. | Local filesystem; temporary spool. | FR-013–FR-019 |

### Key Interactions

Configuration and inventory validation happen before browser creation. Authentication prepares one session per run. The coordinator asks each selected adapter to enumerate a tool, then retrieves one object at a time. Matching consumes authored-field records; reporting consumes matches, coverage events, and diagnostics.

The coordinator, not the matcher, decides whether a scan is complete. The report writer does not infer coverage from match counts.

## Architecture Views

### Logical / Capability View

~~~mermaid
flowchart TB
    Operator["Operator"] --> Run["Run coordinator"]
    Inputs["Inventory and settings"] --> Run
    Run --> Client["Read-client contract"]
    Client --> Browser["Browser provider"]
    Client -. "future" .-> API["API provider"]
    Browser --> Tools["Tool adapters"]
    Tools <--> LMS["Brightspace"]
    Browser <--> Login["Institutional login"]
    Tools --> Fields["Authored field records"]
    Fields --> Matcher["Literal matcher"]
    Matcher --> Reports["Reports and coverage"]
    Run --> Reports
~~~

The API branch is a future alternative. The initial run does not switch providers automatically or probe undocumented APIs.

### Module / Development View

The proposed import package is `gc_stem`, replacing the current `src/gc-stem` directory. A single top-level CLI can later expose other automation domains.

| Planned path | Responsibility / dependency direction |
| --- | --- |
| `src/gc_stem/cli.py` | Thin command routing; imports application services. |
| `src/gc_stem/d2l/config.py` | Validated D2L settings and origin-aware path resolution. |
| `courses.py`, `extract_course_urls.py` | Input adapters and local workbook operation. |
| `models.py` | Plain records, statuses, and error codes; imports no provider. |
| `client.py` | Read-client and tool-adapter protocols. |
| `auth.py`, `browser.py` | Browser login, session, request/navigation guard, and provider lifecycle. |
| `tools/content.py`, `files.py`, `announcements.py`, `assignments.py`, `discussions.py`, `quizzes.py`, `question_library.py` | Tool-specific read strategies. Paths in this row are under `d2l/tools/`. |
| `content.py` | Shared traversal/coordinator over provider and tool contracts. |
| `search.py` | Pure representation/target matching. |
| `reports.py` | Coverage aggregation, spool, CSV/JSON serialization. |
| `api.py` | Reserved future provider; explicitly unavailable in the first release. |
| `tests/d2l/` | Unit, fixture, contract, integration, and explicit live-test groups. |

The current `old/` directory must not be imported or auto-discovered as production tests. Its experiments should be excluded from normal test collection during migration.

### Component-and-Connector / Runtime View

One foreground Python process controls one headed browser context. The operator completes login. Browser adapters use the authenticated UI and strictly scoped read responses; they do not pass browser objects into matching or reporting.

Normal path: validate → authenticate → enumerate tool → read object → match → record coverage → finalize. Read failures produce typed events. A lost session pauses crawl activity for interactive reauthentication; resuming repeats only the unfinished safe read and does not duplicate completed objects.

### Information / Data View

**CourseRef** identifies tenant/course and display metadata. **ObjectRef** identifies a tool object and its containing paths. **AuthoredField** holds one field with representations and availability evidence. **Match** contains a target/location/excerpt. **ToolCoverage**, **CourseResult**, and **RunSummary** track completeness and findings separately.

Records use stable identifiers when exposed. If a provider lacks one, it records a deterministic local identity and its provenance rather than pretending that a title is a platform ID.

Raw field data is short-lived. A temporary local spool stores report records, not full HTML. Completed CSV files and a final JSON manifest are the persistent run outputs. See the [detailed contracts](./20_design.md#data-design).

### Process / Concurrency View

Use one active course and one active read view in the first release. This simplifies session recovery, rate control, field attribution, and read-only checks. The coordinator owns pacing and limits; adapters cannot start unbounded work.

Future concurrency must preserve per-tenant load limits, provider safety, deterministic reporting, and independent coverage. It is not enabled merely by adding an asynchronous library call.

### Deployment / Physical View

| Location | Elements |
| --- | --- |
| Operator workstation | Virtual environment, installed package, settings/inventory, browser, temporary report spool, completed reports. |
| Institutional services | Brightspace and identity/MFA services; no application component is deployed there. |
| GitHub | Source, synthetic fixtures, documentation, offline CI; no live credentials or course scan artifacts. |

Windows is the initial development/pilot target. Cross-platform code is planned; supported platform claims require installation and browser tests.

### Scenario / Use-Case View

**URL found in an assignment but absent from Content:** The Assignments adapter independently enumerates assignments, extracts the instructions, and returns the URL field. The matcher reports it even if no Content topic links to the assignment.

**Question Library denied after other matches:** The adapter returns an access failure. Existing matches remain `FOUND`; course coverage becomes `PARTIAL`. The report does not imply that Question Library was searched.

**Unknown question pool membership:** The quiz adapter records incomplete enumeration. Previewing one randomized attempt is prohibited and would not prove pool coverage.

## Interfaces and Integration

### External Interfaces

* Local Excel/CSV input and CSV/JSON output.
* Browser UI and normal institutional SSO/MFA.
* Trusted tenant/asset hosts explicitly required by the verified browser experience.
* Deferred documented Brightspace APIs, with separate approved authentication and version/capability checks.

### Internal Architectural Interfaces

`BrightspaceReadClient` owns session lifecycle, capability discovery, object discovery, and object reads. `ToolAdapter` isolates tool-specific navigation and extraction. Application services receive normalized records and typed failures, not Selenium/Playwright handles.

`Matcher` accepts a field plus target plan and returns match records. `ReportWriter` accepts matches and coverage events, then finalizes outputs. Interfaces are specified in [29_pdl.md](./29_pdl.md).

### Interoperability

Normalize tool output into the same schema regardless of provider. Preserve platform IDs, original review URLs, field paths, extraction provenance, and selected scope. An API provider is not assumed to have the same coverage as the browser provider; each advertises verified capabilities.

## Quality Attribute Strategies

### Performance and Scalability

Process one object at a time, enforce pacing and item limits, and spool report rows locally. Cache only per-run identities and discovery state. Do not reuse prior-run content without an explicit future cache design.

Limits are safety bounds, not successful completion: hitting a bound produces incomplete coverage.

### Reliability, Availability, and Recoverability

Isolate failures by object/tool/course while the session remains valid. Distinguish genuine empty tools from denied access or failed selectors. Retry bounded transient reads, not permission failures, configuration errors, unknown markup, or potentially state-changing actions.

Write output in a unique run directory. Publish the final manifest only after the requested report files are finalized. Graceful cancellation finalizes a clearly canceled run; hard crashes cannot be labeled complete.

### Security and Privacy

The browser session is scoped to one interactive run. Do not export cookies or save login state. Normal browser temporary data must be closed and cleaned up; this is not a guarantee that the browser or operating system never writes temporary data.

Crawl routes and UI actions are allowlisted by verified read behavior. Reject authoring/attempt/submission/evaluation actions and block unapproved navigation, popups, third-party frames, and requests. Authentication traffic has a separate phase and is not blocked by a simplistic “GET only” rule.

Extract authored fields from their owning views, not entire page bodies. Do not gather learner activity. Reports containing assessment excerpts require appropriate local handling. No correctness weights, student answers, authorization headers, or raw page dumps belong in reports.

### Maintainability, Modifiability, and Testability

Keep protocols small, errors typed, matching pure, and selectors within adapters. Use captured synthetic UI fixtures and a fake client for most tests. A provider change must not require matcher/report rewrites.

Prefer ordinary functions and dataclasses over a generic workflow engine. Add an adapter only when a tool's scope, field contract, failure behavior, and evidence are defined.

### Usability and Accessibility

Use a terminal interface with textual progress and explicit coverage reasons. The operator uses the institution's browser login. No custom credential form is introduced.

## Technology Stack and Platform Decisions

| Technology | Status / rationale |
| --- | --- |
| Python | Existing project language; proposed minimum 3.12, subject to declared support tests. |
| Playwright Python | Proposed browser backend; supports explicit locators and isolated contexts. Adoption requires a tenant spike. |
| openpyxl | Existing workbook dependency; retains the local Excel workflow. |
| Standard library TOML/CSV/JSON/pathlib/dataclasses/sqlite3 | Configuration, portable paths, records, and bounded report spool without a shared service. |
| Beautiful Soup, if useful | Optional HTML parsing implementation detail; do not require it merely because `bs4` appears in the old dependency file. |
| pytest / Ruff | Existing development dependencies; D2L coverage must be added rather than inferred from generic CI. |
| requests / Selenium | Present in current requirements. Keep only where active code needs them; removal is separate reviewed migration work. |

## Dependencies and Supply-Chain Considerations

Declare runtime and developer dependencies explicitly when packaging is added. Record the versions actually tested, including the browser binary. Use compatible version ranges and reproducible installation evidence; do not claim that every future version is supported.

Review package source, license metadata, and maintenance/security status before adoption. Keep live sessions and internal scan artifacts out of CI and build distributions. This draft does not establish a redistribution license for the repository.

## Architectural Decisions and Rationale

| ID | Decision | Alternatives Considered | Rationale / Trade-offs | Consequences |
| --- | --- | --- | --- | --- |
| ADR-001 | Browser first; explicit API provider later. **Direction confirmed.** | API-first; direct reuse of legacy login. | API access is unknown; existing UI access is the current path. | Browser drift is an accepted implementation risk; API scope remains unpromised. |
| ADR-002 | Layered nonsecret configuration with explicit path origins. **Proposed.** | Embedded paths; implicit working-directory assumptions. | Supports different instances and installed-package use. | Requires schema and precedence tests. |
| ADR-003 | Per-tool adapters behind normalized read contracts. **Proposed.** | One giant crawler; arbitrary link following. | Broader authored-content scope needs independent tool discovery. | Each adapter needs capability/coverage evidence. |
| ADR-004 | Use Playwright for the new browser provider. **Proposed.** | Modernize Selenium experiments. | Clear locator/context model suits the intended design. | New runtime/browser dependency; validate before committing to it. |
| ADR-005 | Interactive login with no deliberately persisted authentication state. **Proposed.** | Password files; exported persistent sessions. | Keeps credentials out of program inputs and repository artifacts. | Operator participation is required each run. |
| ADR-006 | Separate match findings from completeness. **Proposed.** | A single FOUND/NOT_FOUND/PARTIAL status. | A scan can find a match and still miss an area. | Reports and aggregation are more explicit. |
| ADR-007 | Installable `gc_stem` package with thin CLI. **Proposed.** | Execute scripts from `src/gc-stem` using checkout-relative imports. | Ordinary imports and package use are needed for reuse. | Rename package and add build/project metadata before CLI examples work. |
| ADR-008 | Seven-tool authored-content baseline with declared visibility and representations. **Proposed.** | Content-only scan; unsupported “all tools” claim. | Makes the requested broader search testable. | Additional areas remain explicit scope decisions. |

## Architecture Risks and Technical Debt

* Browser UI drift, frames, or shadow roots can invalidate selectors. Detect unexpected structures and mark gaps.
* Read views may perform stateful requests. Validate routes and effects in the pilot; “read-only” cannot be inferred from button labels or HTTP verbs alone.
* Hidden fields and question pools may not expose complete enumeration. Report a limitation rather than using a sample attempt.
* The existing package name, root README, dependency list, test discovery, missing inventory CSV, and inherited CI assumptions need construction work.
* The workbook utility currently finds the repository root at import time and does not create destination parents. Isolate and improve it during migration without changing its established data-preservation contract.

## Architecture Evaluation

Planned evaluation uses a fake-client end-to-end run, per-adapter fixture tests, a controlled tenant spike, and a seeded multiple-tool pilot. Review scenarios include session expiry, partial Question Library access, blocked external resources, output failure, pagination loops, and cancellation.

No live SNHU interaction, provider prototype, performance benchmark, or product test execution occurred in this documentation task.

## Traceability to Detailed Design and Testing

| Architecture element / decision | Detailed realization | Verification |
| --- | --- | --- |
| ADR-001, ADR-004, ADR-005 | Session/client and guard contracts | TC-005, TC-015, TC-021, TC-023 |
| ADR-002, ADR-007 | Configuration, package, path contracts | TC-001, TC-018, TC-025–TC-026 |
| ADR-003, ADR-008 | Adapter registry and authored fields | TC-006–TC-009, TC-020 |
| ADR-006 | Coverage aggregation and report schema | TC-012–TC-019 |
| Bounded local processing | Sequential traversal and spool | TC-008, TC-022, TC-027 |

## Open Issues

Resolve the shared [requirements issues](./10_requirements.md#risks-conflicts-and-open-issues). The first architectural construction checkpoint is a verified SNHU browser/login/read spike, not implementation of all adapters at once.

## References

* [Requirements](./10_requirements.md), [Design](./20_design.md), and [source record](./README.md).
* [Existing module tree](https://github.com/GC-STEM/automation/tree/196cda43adf48a8b3b74b3ea03101763bcb0f67f/src/gc-stem/d2l).
* Playwright, [Authentication](https://playwright.dev/python/docs/auth) and [Locators](https://playwright.dev/python/docs/locators), consulted October 16, 2026.
* D2L, [OAuth 2 authentication](https://docs.valence.desire2learn.com/basic/oauth2.html), consulted October 16, 2026.

<!--
title: "GC-STEM D2L Automation | Software Architecture Description"
document_type: "Software Architecture Description (SAD)"
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
