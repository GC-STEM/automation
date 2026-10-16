# GC-STEM D2L Automation | Software Requirements Specification

> **Draft baseline for review.** “Shall” defines proposed acceptance behavior. Only the project direction identified in the README is confirmed; detailed requirements and defaults remain subject to review.

## Table of Contents <!-- omit from toc -->

* [Purpose and Scope](#purpose-and-scope)
* [Product Context](#product-context)
* [Functional Requirements](#functional-requirements)
* [Data Requirements](#data-requirements)
* [External Interface Requirements](#external-interface-requirements)
* [Nonfunctional Requirements](#nonfunctional-requirements)
* [Technology and Implementation Constraints](#technology-and-implementation-constraints)
* [Legal, Regulatory, Policy, and Ethical Constraints](#legal-regulatory-policy-and-ethical-constraints)
* [Acceptance Criteria](#acceptance-criteria)
* [Requirements Traceability](#requirements-traceability)
* [Requirement Priorities and Release Allocation](#requirement-priorities-and-release-allocation)
* [Risks, Conflicts, and Open Issues](#risks-conflicts-and-open-issues)
* [References](#references)

## Purpose and Scope

### Purpose

Define verifiable behavior for reusable Brightspace access, Excel course-URL preparation, and the first course-content search tool. Developers use this specification to implement the tool; maintainers use it to judge scope, results, and readiness.

### Product Scope

An internal Python library and command-line interface search an explicit course list across selected Brightspace tools. Browser access is required for the first implementation. An API provider is a future integration, not a dependency for the first release.

The search inspects authorized course-authored strings and HTML. It returns evidence for matching locations and an independent account of search completeness. Editing or repairing the matched content is a separate future tool.

### Intended Audience

GC-STEM Automation maintainers, developers, testers, course subject matter experts, and relevant Brightspace administrators.

### Definitions, Acronyms, and Abbreviations

| Term | Meaning |
| --- | --- |
| Brightspace / D2L | The learning management system being inspected. |
| Org Unit / OrgUnitID | A Brightspace organizational object and its identifier; this tool selects course shells explicitly. |
| Tool adapter | Code that discovers and reads one Brightspace tool area. |
| Authored field | A title, description, HTML body, question field, or other course-created material; not a learner response. |
| Representation | Source HTML, rendered DOM fragment, visible text, or extracted URL value. |
| Coverage | Whether the declared course/tool/field/representation scope was fully searched. |
| SSO / MFA | Single sign-on / multifactor authentication. |
| Must / Should / Could | Required for the proposed release / desirable later / optional extension. |

## Product Context

### Problem Statement

Maintainers need a reliable way to locate course material containing particular strings, including embedded URLs that are not displayed as text. Manual review is time-consuming and does not reliably reveal missed tool areas.

### Product Perspective

This is a new reusable implementation informed by earlier browser experiments. It extends the repository's existing Excel URL-extraction utility. The current crawler-related modules are empty scaffolds and do not establish working SNHU integration.

### Stakeholders and User Classes

| Stakeholder or User Class | Goals / Needs | Relevant Characteristics |
| --- | --- | --- |
| Operator / course maintainer | Find affected locations and understand gaps. | Authorized internal user; comfortable with files and a terminal. |
| Course SME | Verify context and decide remediation. | Needs course/tool/object identity and navigable references. |
| Developer / tester | Replace providers and add tools without rewriting search. | Works with Python, fixtures, and documented contracts. |
| Brightspace administrator | Protect service operation and clarify access. | Controls permissions and integration availability. |

### Operating Environment

Proposed runtime: Python 3.12 or later in a project virtual environment, on Windows, Linux, or macOS. Windows with VS Code and PowerShell is the primary development context. The current repository's core CI uses Python 3.12; other runtime/platform combinations require evidence before being advertised as supported.

A headed browser, network access to the institution's Brightspace instance and login services, and an authorized account are needed for live search. Local URL extraction requires no Brightspace login.

### Assumptions and Dependencies

* SNHU API availability is unknown.
* The operator is allowed to access the selected shells using their normal account.
* Appropriate pilot content and browser tool views can be inspected before building adapters.
* Tool availability, permissions, content experiences, HTML frames, and question types vary and must be detected.
* Workbooks are local trusted inputs; the project does not require a shared database.

### Scope Boundaries

#### In Scope

This proposed first-release matrix turns “broader search” into a reviewable scope. **Every selected row requires discovery, extraction, coverage reporting, and acceptance evidence.**

| Tool key | Authored fields to search | Important coverage condition |
| --- | --- | --- |
| `content` | Module/topic titles and descriptions, HTML topics, link labels and targets. | Traverse all nested modules and pages; linked activities do not replace independent tool scans. |
| `files` | Authorized HTML/HTM course files, including unlinked files visible in Manage Files. | Recursively enumerate permitted folders; report inaccessible folders and non-HTML exclusions. |
| `announcements` | Announcement title and HTML body. | Include authorized current, scheduled, expired, hidden, and draft items when requested and available. |
| `assignments` | Assignment title and instructions/descriptions. | Do not enter submissions or evaluation records. |
| `discussions` | Forum/topic titles, descriptions, and authored prompts. | Exclude discussion threads, replies, and participant activity. |
| `quizzes` | Quiz title/introduction/descriptions, section text, questions, choices, hints, model-answer text, and authored feedback where exposed. | Inspect authoring/read views without starting attempts; enumerate all pool members and field types or mark gaps. |
| `question_library` | Authorized section text, questions, choices, hints, model-answer text, and authored feedback. | Scan independently of quiz usage; record whether shared references or copies can be identified. |

Hidden/draft material is proposed to be included by default for administrative audits, subject to the user's permissions. Explicit exclusion narrows the declared scope. It does not authorize gaining additional access.

#### Out of Scope

* Student submissions, attempts, answers, discussion contributions, grades, enrollments, and personal communications.
* Content modification, publication, deletion, copying, course provisioning, and automatic remediation.
* External-site crawling, link safety assessment, or opening third-party/LTI activities.
* Searching inside PDF, Office, images, audio/video, archives, SCORM packages, or executable content. Their link targets remain searchable.
* Survey, Checklist, Rubric, custom-widget, and other adapters in the proposed baseline. They are extension candidates and must not be implied by a claim of organization-wide or “all tools” coverage.
* Unattended MFA, password capture, SSO bypass, and reusing legacy institution-specific credentials.
* A web dashboard, scheduled execution, automatic messaging, and API integration in this increment.

## Functional Requirements

Sources: **U** = explicit project-owner need or clarification; **R** = observed repository behavior; **P** = proposed behavior needed to make the draft implementable. All rows are part of the proposed acceptance baseline.

| ID | Requirement | Rationale / Source | Priority | Acceptance Evidence |
| --- | --- | --- | --- | --- |
| FR-001 | The tool shall load validated nonsecret settings with precedence: explicit command options, supported environment variables, selected TOML file, defaults. | U: configurable data; P: precedence. | Must | TC-001. |
| FR-002 | The tool shall read the existing Excel inventory and a normalized CSV alternative into the same course model. | R: Excel workflow; P: adapters. | Must | TC-002. |
| FR-003 | The tool shall validate course IDs and tenant URLs, reject conflicts, deduplicate by tenant and course ID, and scan only the validated list. | U: supplied list; P: integrity. | Must | TC-003. |
| FR-004 | The URL utility shall copy external `CourseName` hyperlink targets to `CourseURL`, add that column if absent, leave rows without targets unchanged, preserve unrelated workbook data, and save to the explicit destination. | U/R: existing utility behavior. | Must | TC-004. |
| FR-005 | Browser search shall allow the operator to complete institutional SSO/MFA directly and verify return to the configured tenant before reading courses. | U: browser first; P: authentication contract. | Must | TC-005. |
| FR-006 | The tool shall discover each selected tool independently for every selected course. | U: broader search; P: matrix. | Must | TC-006. |
| FR-007 | Each required adapter shall extract only its documented authored fields and honor declared hidden/draft scope. | U: HTML search; P: authored-field boundary. | Must | TC-007. |
| FR-008 | Discovery shall follow nested structures and pagination, detect repeats, and identify incomplete enumeration. | P: coverage integrity. | Must | TC-008. |
| FR-009 | Search shall support `source`, `dom`, `text`, and `all` modes with explicit representation labels and no silent substitution of unavailable representations. | U: HTML/visible text; P: modes. | Must | TC-009. |
| FR-010 | Search shall evaluate each nonempty literal target independently, use case-insensitive matching by default, and support case-sensitive matching. | U: target strings; P: defaults. | Must | TC-010. |
| FR-011 | The tool shall search URL attributes and link-topic targets without navigating to their external destinations. | U: embedded URLs; P: navigation boundary. | Must | TC-011. |
| FR-012 | Each match shall identify course, tool, object, field, representation, target, occurrence count, bounded context, and review location. | U: course/page results; P: schema. | Must | TC-012. |
| FR-013 | Search shall produce `matches.csv`, `coverage.csv`, and `summary.json` in a unique run directory. | P: reusable outputs. | Must | TC-013. |
| FR-014 | Reports shall keep match status separate from coverage status and permit `NOT_FOUND` only for complete declared coverage. | P: prevent false negatives. | Must | TC-014. |
| FR-015 | The tool shall classify retrieval failures, retry only appropriate bounded reads, and continue independent work when the session remains safe and valid. | P: resilience. | Must | TC-015. |
| FR-016 | On cancellation or session loss, the tool shall preserve acquired matches, identify unfinished scope, close resources, and return a non-success exit status. | P: recoverable runs. | Must | TC-016. |
| FR-017 | Reports shall record run time, software identity, redacted effective settings, selected scope, input digest, counts, exclusions, and failures. | P: reproducibility. | Must | TC-017. |
| FR-018 | Configuration shall reject unsupported keys, invalid values, empty targets, unsupported tools, and unimplemented `regex=true` or API modes before crawling. | R: prototype flags; P: fail clearly. | Must | TC-001, TC-018. |
| FR-019 | Output creation shall protect existing files, publish the JSON completion manifest last, and neutralize spreadsheet formulas in untrusted CSV fields. | P: integrity and export safety. | Must | TC-019. |
| FR-020 | A validation-only command shall check local inputs, paths, and settings without logging in or reading Brightspace. | P: operator feedback. | Must | TC-018. |
| FR-021 | New D2L operations shall be able to reuse session, course, and retrieval interfaces without importing matching or reporting internals. | U: more tools expected. | Must | TC-020. |
| FR-022 | A later approved API provider should satisfy the same read contracts and report its own per-tool capabilities. | U: API unknown; P: extension seam. | Should; deferred | TC-020 contract review now; live API tests later. |

### Use Cases or User Stories

* **UC-01 — Prepare inventory:** An operator extracts workbook hyperlinks, checks validation, and uses the processed inventory for search. FR-002–FR-004, FR-020.
* **UC-02 — Find a referenced domain:** An operator supplies a domain string. Matches in authored text, source HTML, and embedded URLs identify the affected courses and locations. FR-006–FR-013.
* **UC-03 — Handle incomplete access:** One Question Library area is denied. Results from other areas remain available, while that course has incomplete coverage and cannot receive `NOT_FOUND`. FR-014–FR-017.
* **UC-04 — Add another operation:** A developer reuses course/session interfaces without copying browser-login logic. FR-021–FR-022.

## Data Requirements

### Inputs

| Input | Source | Type / Format | Validation / Constraints | Related Requirements |
| --- | --- | --- | --- | --- |
| Workbook | Operator/local inventory | `.xlsx`, worksheet `D2L` by default | Required headers for each operation; no duplicate normalized headers; input exists; source is preserved by default. | FR-002–FR-004 |
| CSV inventory | Operator | UTF-8; `org_unit_id`, optional `course_name`/`course_url` | Decimal positive IDs; URL/ID agreement; tenant agreement; stable deduplication. | FR-002–FR-003 |
| Targets | Configuration/command options | Ordered list of strings | At least one nonblank string; retain literal characters; reject regex mode in first release. | FR-010, FR-018 |
| Tenant | Configuration | HTTPS base URL | No credentials/query/fragment; supported Brightspace path; host is the scope boundary. | FR-001, FR-003 |
| Tool and visibility scope | Configuration | Validated keys and booleans | Required matrix defaults; explicit narrower scope recorded; unknown keys fail. | FR-006–FR-007 |
| Crawl limits | Configuration | Positive numeric settings | Finite timeouts/retries/item limits; nonnegative pacing. | FR-015 |
| Output directory | Operator/configuration | Local filesystem path | Parent can be created; target run must not overwrite a prior run. | FR-013, FR-019 |

### Outputs

| Output | Destination | Type / Format | Required Characteristics | Related Requirements |
| --- | --- | --- | --- | --- |
| Processed inventory | Explicit path | Excel | Preserved worksheets/values/styles supported by openpyxl; unchanged missing-hyperlink rows; no claim of byte-identical XLSX output. | FR-004 |
| Matches | Unique run directory | UTF-8 CSV | Fixed columns; stable final order; spreadsheet-safe string cells; useful bounded excerpts. | FR-012–FR-013, FR-019 |
| Coverage | Same run directory | UTF-8 CSV | One row per course/tool, including confirmed absence or explicit exclusion. | FR-014 |
| Manifest | Same run directory | JSON, `schema_version=1` | Final run state, scope, versions, counts, diagnostics; no secrets or full raw pages. | FR-017, FR-019 |
| Terminal result | Terminal/process | Plain text and exit code | Match counts do not control success; incomplete coverage does. | FR-014–FR-016 |

### Persistent Data

Input inventories and completed reports are intentionally persistent. Raw retrieved HTML is processed in memory by default; a temporary local spool may hold report rows. Browser state is not deliberately saved between runs.

Do not invent a retention period. Before operational use, the maintainer must agree where reports are kept, who can access them, and how they are removed. A later explicit cache or resume feature requires a separate design and retention decision.

### Data Privacy and Sensitivity

Authored course material may be internal; quiz text, model answers, and feedback may be restricted assessment material. Reports should contain only required location metadata and bounded matching context. The tool must not read learner submissions, attempts, grades, posts, or personal communications.

## External Interface Requirements

### User Interfaces

A command-line interface provides help, input validation, progress, cancellation, a final coverage summary, and meaningful exit codes. Interactive authentication occurs in the normal browser interface. Status must be understandable without color.

### Software Interfaces and APIs

* Excel via openpyxl; CSV/JSON/TOML via documented file contracts.
* Browser automation through a proposed Playwright provider.
* Provider-independent Python records and exceptions.
* Deferred Brightspace API provider only after access, version, scope, and field coverage are established. API documentation does not establish SNHU availability.

### Communication Interfaces

Use HTTPS with normal certificate verification. SSO may redirect to institutional identity services. After authentication, crawl navigation and requests are constrained to validated tenant/read routes and explicitly required asset hosts. Browser UI reads must be evaluated by their effect, not by assuming every GET is safe or every POST is a write.

## Nonfunctional Requirements

### Performance and Efficiency

**NFR-001:** Pacing, timeouts, retry count, item limits, and request concurrency shall be bounded. Proposed initial settings are one active course/page, a minimum one-second gap between crawl actions, a 30-second read timeout, and at most two transient-read retries. These are local design defaults, not D2L-approved limits. TC-015, TC-022.

### Reliability, Availability, and Recoverability

**NFR-002:** A failed object/tool shall not erase earlier results; unknown completeness shall propagate to coverage. No report may label an interrupted or failed scan complete. TC-014–TC-016, TC-019.

### Security

**NFR-003:** The first release shall expose only read operations and block authoring, publishing, deletion, attempt, submission, evaluation, and configuration actions. Normal platform view logging is not an authoring change. TC-021.

**NFR-004:** Passwords, MFA codes, session cookies, authorization headers, and tokens shall not be collected by the tool's configuration/CLI, deliberately persisted, or emitted in logs/reports. TC-005, TC-023.

### Privacy

**NFR-005:** Retrieval and outputs shall exclude learner activity and minimize stored course/assessment text. Third-party page navigation and embedded-resource requests shall be blocked unless explicitly required for the trusted Brightspace shell. TC-007, TC-011, TC-023.

### Usability and Accessibility

**NFR-006:** Help, validation failures, progress, cancellation, exit codes, and partial-coverage reasons shall be available in text, without relying on color or a mouse outside the institutional login process. TC-018, TC-024.

### Maintainability and Supportability

**NFR-007:** Modules shall separate login, provider navigation, tool adapters, course input, matching, and reporting. Public Python functions shall follow PEP 8/257 and have meaningful type annotations. Business logic shall be testable without live Brightspace. TC-020, TC-025.

**NFR-008:** Runs shall record structured diagnostics by course/tool/object and software version without full HTML dumps or secret-bearing URLs. TC-017, TC-023.

### Portability, Compatibility, and Interoperability

**NFR-009:** Configured paths shall not depend on the caller's working directory or a particular user's checkout path. Package execution shall not require finding `pyproject.toml` at import time. TC-026.

**NFR-010:** The first supported platform/runtime list shall be based on clean-install and browser evidence. Python 3.12 is the proposed minimum; Windows is the initial pilot platform. TC-025–TC-026.

### Scalability

**NFR-011:** Memory shall be bounded by an object/field and a local report spool rather than all course HTML. Per-course/per-tool limits shall produce partial coverage instead of silent truncation. TC-008, TC-022.

**NFR-012:** Fresh runs shall retrieve current content rather than silently reusing previous-run page caches. Results shall identify scan start/end times because live courses are not a transactional snapshot. TC-017, TC-027.

## Technology and Implementation Constraints

Python is the implementation language. Browser access must work before an API integration exists. Secrets and institution-specific data belong outside code. PEP 8/257 apply to new Python code.

Playwright, the `gc_stem` package name, Python 3.12 minimum, TOML schema, and report filenames are proposed choices. The current dependency list includes Selenium, requests, bs4, and openpyxl; that list does not prove the proposed implementation exists.

## Legal, Regulatory, Policy, and Ethical Constraints

Use only the operator's authorized access and institutionally permitted automation. Do not bypass access controls. Existing institutional requirements govern course and assessment data; no policy approval, retention period, or production authorization has been established by this draft.

## Acceptance Criteria

Release acceptance requires all Must requirements and NFRs to have passing evidence. At minimum:

1. A suitable pilot proves normal login and no course-authoring/attempt changes.
2. Each of the seven required adapters finds a seeded text and embedded-URL target.
3. An inaccessible area, unsupported field/question type, pagination failure, and limit each produce truthful partial/error coverage.
4. Source/text/DOM/URL behavior matches the requested mode.
5. Workbook preparation, inventory validation, reports, cancellation, and output-failure handling pass their cases.
6. A clean package installation supports documented invocation from another working directory.
7. The product owner reviews declared exclusions and unresolved operational decisions.

A Content-only prototype can be useful for development but does not satisfy this proposed broader release baseline.

## Requirements Traceability

Architecture and detailed module allocation are in [19_architecture.md](./19_architecture.md) and [20_design.md](./20_design.md). All listed implementation units are planned unless identified in the current-state review.

| Requirement ID | Source | Architecture / Design | Implementation | Verification |
| --- | --- | --- | --- | --- |
| FR-001, FR-018, FR-020 | U/P | ADR-002; configuration contract | Planned `config.py` / CLI | TC-001, TC-018 |
| FR-002–FR-004 | U/R/P | Inventory adapter / path rules | `extract_course_urls.py` exists; `courses.py` planned | TC-002–TC-004 |
| FR-005 | U/P | ADR-001, ADR-005 | Planned `auth.py`, `browser.py` | TC-005 |
| FR-006–FR-008 | U/P | Tool adapter / traversal contracts | Planned `tools/*`, `content.py` | TC-006–TC-008 |
| FR-009–FR-011 | U/P | Representation and matching rules | Planned `search.py` / extraction adapters | TC-009–TC-011 |
| FR-012–FR-014, FR-017, FR-019 | U/P | Data/status/report contracts | Planned `models.py`, `reports.py` | TC-012–TC-014, TC-017, TC-019 |
| FR-015–FR-016 | P | Error and run-state rules | Planned provider/orchestrator | TC-015–TC-016 |
| FR-021–FR-022 | U/P | ADR-001, ADR-003 | Planned client protocol; API deferred | TC-020 |
| NFR-001–NFR-012 | U/P | Quality strategies / design | Planned crosscutting controls | Mapping in test plan |

## Requirement Priorities and Release Allocation

**Current documentation baseline:** all Must rows, including seven-tool coverage, are proposed for the first operational search release. Build and test them incrementally.

**Deferred:** FR-022 API implementation, regex, saved sessions, resume/cache, additional tool adapters, non-HTML file parsing, scheduled execution, and modification tools. A deferred feature must be rejected or explicitly excluded, not silently simulated.

## Risks, Conflicts, and Open Issues

| ID | Issue / Risk | Impact | Owner | Status / Resolution |
| --- | --- | --- | --- | --- |
| REQ-ISSUE-001 | The exact additional-tool set was not enumerated by the owner. | Scope could differ from expectations. | Product owner | Proposed seven-tool matrix; confirm before release planning. |
| REQ-ISSUE-002 | SNHU content experience, selectors, and safe read routes are unverified. | Browser extraction may need different strategies. | Developer + Brightspace administrator | Resolve with a pilot before claiming support. |
| REQ-ISSUE-003 | API availability and permissions are unknown. | API work cannot be promised. | Brightspace administrator | Browser-first confirmed; API deferred. |
| REQ-ISSUE-004 | Hidden content, question pools, and Question Library fields may be inaccessible. | Complete coverage may be impossible for some roles. | Developer + operator | Capability tests; report gaps; never relax status rules. |
| REQ-ISSUE-005 | Load, report access, and retention have not been agreed. | Operational settings remain provisional. | Maintainer + institutional contacts | Agree before routine use. |
| REQ-ISSUE-006 | Package, inventory configuration, legacy tests, and generic CI need migration. | Installation or verification can fail before search begins. | Maintainer | Address construction prerequisites; do not describe them as completed. |

## References

* [Documentation source and decision record](./README.md).
* [Repository configuration](https://github.com/GC-STEM/automation/blob/196cda43adf48a8b3b74b3ea03101763bcb0f67f/config/d2l.toml).
* [Existing URL extractor](https://github.com/GC-STEM/automation/blob/196cda43adf48a8b3b74b3ea03101763bcb0f67f/src/gc-stem/d2l/extract_course_urls.py).
* D2L, [Brightspace API calling conventions](https://docs.valence.desire2learn.com/basic/apicall.html), consulted October 16, 2026.
* [PEP 8](https://peps.python.org/pep-0008/) and [PEP 257](https://peps.python.org/pep-0257/).

<!--
title: "GC-STEM D2L Automation | Software Requirements Specification"
document_type: "Software Requirements Specification (SRS)"
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
