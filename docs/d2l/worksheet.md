# GC-STEM D2L Automation | Maintainer Worksheet

> **Internal project worksheet — draft, October 16, 2026.** This replaces the inherited student assignment instructions. It records project decisions and evidence; it is not a graded activity or a Brightspace submission task.

## Table of Contents <!-- omit from toc -->

* [Getting Started](#getting-started)
* [Decision Register](#decision-register)
* [Evidence Record](#evidence-record)
* [Getting Help](#getting-help)
* [Related Documents](#related-documents)

## Getting Started

Use this worksheet with the [overview](./00_overview.md), [requirements](./10_requirements.md), and [construction plan](./30_construction.md). Complete checkpoints when evidence exists. An unchecked item means planned/unverified work, not a failed test.

### 0. Meet the Prerequisites

#### Required Prerequisites

* [x] Resolve a fresh repository snapshot and read the D2L template prompts.
* [x] Review the project's earlier architecture, search, inventory, and environment discussions.
* [x] Obtain direction for broader search, browser-first access, and downloadable drafts.
* [ ] Confirm the proposed seven-tool first-release matrix.
* [ ] Identify a suitable SNHU pilot course, operator identity, and safe authored-content read views.
* [ ] Agree acceptable crawl load and report access/retention for operational use.

#### Recommended Prerequisites

* [ ] Assign the developer, operator, reviewer, and Brightspace contact roles.
* [ ] Prepare synthetic fixtures with known positive, negative, and incomplete cases.
* [ ] Record browser/content experience and required course-tool permissions.

### 1. Analyze the Problem

**Need:** Find target strings in authored course material across an explicit course list, including source HTML and embedded URLs.

**Users:** Authorized GC-STEM administrators/maintainers and course SMEs reviewing matches.

**Confirmed boundaries:** Reusable library, configurable data, protected secrets, browser first while API availability is unknown, broader than Content, downloadable documentation.

**Proposed detailed scope:** Content, Manage Files HTML, Announcements, Assignments, Discussions, Quizzes, and Question Library. Learner activity, grade data, external-site crawling, and binary-file contents are excluded.

* [ ] Review [functional requirements](./10_requirements.md#functional-requirements) and proposed scope.
* [ ] Resolve or explicitly retain REQ-ISSUE-001–REQ-ISSUE-006.
* [ ] Confirm that complete coverage means the declared tools/fields/visibility/representations, not all possible Brightspace data.

### 2. Design the Solution

**Design summary:** Config/inventory → browser read client and per-tool adapters → authored field records → literal matching → independent coverage and findings → local CSV/JSON reports.

* [ ] Review [architecture](./19_architecture.md), [design](./20_design.md), and the [editable diagrams](./23_diagram.drawio).
* [ ] Review [pseudocode](./26_pseudocode.txt) and [PDL](./29_pdl.md).
* [ ] Verify source/DOM/text/URL field availability in the tenant spike.
* [ ] Confirm safe quiz/question-bank reads and complete pool enumeration.
* [ ] Confirm the proposed configuration, report schema, and status/exit-code rules.

### 3. Construct the Solution

Current-state review: the workbook utility has source code; other new D2L modules/tests are empty. Packaging and CLI metadata are absent. These findings are not execution evidence.

* [ ] Make `gc_stem` importable and installable; isolate legacy experiments/test collection.
* [ ] Preserve and harden the workbook workflow.
* [ ] Complete an offline fake-client pipeline before expanding live reads.
* [ ] Implement normal interactive login and verified read guards.
* [ ] Implement each required adapter and its field/capability contract.
* [ ] Implement bounded matching, truthful coverage, reports, cancellation, and product CI.
* [ ] Keep documentation synchronized with actual behavior.

### 4. Test the Solution

Use [40_testing.md](./40_testing.md). All product tests are currently **not executed** for this documentation task.

* [ ] Execute meaningful local and offline integration cases.
* [ ] Execute clean-install and arbitrary-working-directory checks.
* [ ] Execute a suitable seeded multiple-tool pilot.
* [ ] Demonstrate denied/unsupported/limited areas cannot produce a clean NOT_FOUND.
* [ ] Demonstrate no authoring, attempt, submission, grade, or settings changes.
* [ ] Record exact versions, inputs, expected/actual results, and remaining gaps.

### 5. Review and Handoff

* [ ] Review the eleven documentation files and exact file paths.
* [ ] Record actual source commit and test evidence for any implementation release.
* [ ] Confirm output handling and known exclusions with the product owner.
* [ ] Make an acceptance or no-release recommendation based on evidence.
* [ ] Handle repository submission through the maintainer's normal workflow.

The current deliverable is a downloadable draft package. It does not create a pull request or modify Brightspace.

## Decision Register

| ID | Decision / Question | Current Record | Owner / Trigger |
| --- | --- | --- | --- |
| DEC-001 | Initial scope | Broader than Content confirmed; seven-tool matrix proposed. | Product owner; before release planning. |
| DEC-002 | Access method | API availability unknown; browser first confirmed. | Brightspace contact; API decision later. |
| DEC-003 | Delivery | Downloadable files matching `docs/d2l` confirmed. | Draft preparation. |
| DEC-004 | Browser technology | Playwright proposed; current dependency list still includes Selenium. | Developer; tenant spike. |
| DEC-005 | Package/CLI | `gc_stem` and `gc-stem` proposed; migration required. | Maintainer; packaging increment. |
| DEC-006 | Default audit scope | All-mode, hidden/draft inclusion proposed. | Product owner/operator; scope review. |
| DEC-007 | Load/retention | No agreed operational values or retention period. | Maintainer/institutional contact; before routine use. |
| DEC-008 | Extra tools | Surveys, Checklists, Rubrics, widgets, and others deferred candidates. | Product owner; next scope decision. |

## Evidence Record

| Activity | Evidence / Status |
| --- | --- |
| Fresh source read | `main` resolved with cache-busting query; files pinned to `196cda43adf48a8b3b74b3ea03101763bcb0f67f`. |
| Project history | Earlier project discussions retrieved and compared with current source. |
| Template review | All eleven D2L files reviewed, including empty README/PDL and inherited worksheet. |
| Documentation checks | Internal links/anchors, requirement/test references, placeholder removal, configuration example, diagram XML, and archive contents checked; this does not substitute for product tests. |
| Product tests | Not executed. |
| Live Brightspace access | Not performed. |
| API availability | Unknown. |
| Operational acceptance | Not requested or established by this draft. |

## Getting Help

For project scope or document questions, contact the GC-STEM Automation maintainer/product owner. For permissions, tenant behavior, or API availability, use the institution's Brightspace administration/support channel. Do not place credentials, restricted course material, or quiz answers in public issues.

## Related Documents

[Overview](./00_overview.md) · [Requirements](./10_requirements.md) · [Architecture](./19_architecture.md) · [Design](./20_design.md) · [Construction](./30_construction.md) · [Testing](./40_testing.md)

<!--
title: "GC-STEM D2L Automation | Maintainer Worksheet"
document_type: "Maintainer Worksheet"
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
