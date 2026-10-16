# GC-STEM D2L Automation | Software Construction Plan

> **Implementation plan, not a completion report.** Only the workbook extractor currently contains active new D2L source. No crawler implementation, tenant pilot, or D2L test execution is claimed.

## Table of Contents <!-- omit from toc -->

* [Purpose and Scope](#purpose-and-scope)
* [Construction Approach](#construction-approach)
* [Development Environment](#development-environment)
* [Source-Code Organization](#source-code-organization)
* [Work Breakdown and Construction Order](#work-breakdown-and-construction-order)
* [Integration Strategy](#integration-strategy)
* [Version Control and Change Management](#version-control-and-change-management)
* [Dependency and Supply-Chain Management](#dependency-and-supply-chain-management)
* [Build and Packaging](#build-and-packaging)
* [Construction Testing](#construction-testing)
* [Code Review and Static Verification](#code-review-and-static-verification)
* [Security During Construction](#security-during-construction)
* [Construction Quality Gates](#construction-quality-gates)
* [Automation and Continuous Integration](#automation-and-continuous-integration)
* [Roles and Responsibilities](#roles-and-responsibilities)
* [Milestones and Schedule](#milestones-and-schedule)
* [Construction Measures and Progress Tracking](#construction-measures-and-progress-tracking)
* [Construction Risks and Mitigations](#construction-risks-and-mitigations)
* [Construction Deliverables](#construction-deliverables)
* [Traceability and Handoff](#traceability-and-handoff)
* [Open Issues](#open-issues)
* [References](#references)

## Purpose and Scope

### Purpose

Guide incremental construction of a reusable D2L library and broader authored-content search. Resolve packaging and repository prerequisites before treating example commands or generic CI as proof of a working product.

### Construction Scope

Migrate the existing workbook utility into an importable package; implement configuration, course inputs, browser session, seven tool adapters, matching, coverage, reports, and CLI. API, regex, persistent sessions, resume/cache, binary-file parsing, and modification tools remain deferred.

### Construction Inputs

* [Requirements](./10_requirements.md), [architecture](./19_architecture.md), and [design](./20_design.md).
* [PDL](./29_pdl.md), [pseudocode](./26_pseudocode.txt), and [test plan](./40_testing.md).
* Current repository at [196cda4](https://github.com/GC-STEM/automation/tree/196cda43adf48a8b3b74b3ea03101763bcb0f67f).
* Confirmed browser-first direction and broader search; remaining detailed decisions are proposed.

## Construction Approach

### Development Method

Use small vertical increments. Establish an offline end-to-end path with a fake client, then prove one real browser read before expanding tool coverage. Keep each increment reviewable and capable of producing meaningful evidence.

Do not begin by adapting every legacy script or building all selectors. Prove the SNHU session/read boundary first.

### Construction Principles

* Prefer clear functions, dataclasses, and small protocols.
* Keep institutional values and operator data out of code.
* Preserve the workbook utility's established cell behavior.
* Treat incomplete scope as a first-class result.
* Keep new production code independent of legacy experiments.
* Separate source review, automated tests, and live pilot evidence.

### Definition of Construction Complete

A component is complete when its contract is implemented, meaningful positive/negative cases pass, errors remain observable, documentation matches behavior, and no secrets or internal scan artifacts enter the change.

The search feature is construction-complete only after all required adapters are integrated and offline checks pass. Operational acceptance additionally requires the controlled live evidence and owner review specified in the test plan.

## Development Environment

### Languages and Runtimes

Use Python 3.12 as the initial development/CI baseline; the proposed package declares a minimum of 3.12. Declare additional tested versions explicitly before support claims. The browser provider needs a compatible installed browser binary.

PowerShell is the user's chosen Windows terminal for this internal automation workspace. Bash/POSIX equivalents remain usable on Linux/macOS; the course-template instruction to require Git Bash does not apply.

### Development Tools

VS Code, Git/GitHub, a project virtual environment, pytest/pytest-cov, Ruff, and Draw.io. Playwright is the proposed new browser backend; Selenium is present in legacy requirements but is not proof that the new browser provider exists.

### Environment Setup

The current `requirements.txt` can bootstrap the existing source review environment. In a Windows PowerShell terminal opened at the checkout:

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

Selecting the workspace interpreter in VS Code can use this environment. Activation is optional when invoking its Python directly. Do not prescribe execution-policy changes or assume a particular checkout drive.

**After package metadata and development extras have been implemented**, the proposed install path is:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m playwright install chromium
~~~

These later commands are not currently supported by the baseline `pyproject.toml`. Unix-like environments use the corresponding virtual-environment Python path. A clean-install test must exercise the actual supported instructions.

Prepare nonsecret local configuration and synthetic fixtures. Live login remains manual. No live credentials belong in test settings.

### Coding and Documentation Standards

Apply PEP 8 and PEP 257. Use four-space Python indentation, meaningful type annotations, concise public docstrings, and the repository's 80-column preference where practical. Use UTF-8/LF text and the established CRLF exceptions for Windows batch files.

Name the import package `gc_stem`. Do not use global browser instances or perform filesystem/network work at import time. Public APIs document expected exceptions. Keep requirements, design, pseudocode, and tests synchronized.

## Source-Code Organization

| Planned location | Purpose |
| --- | --- |
| `src/gc_stem/cli.py` | Thin CLI and operation dispatch. |
| `src/gc_stem/d2l/models.py`, `config.py`, `client.py` | Core records, settings, read contracts. |
| `src/gc_stem/d2l/courses.py`, `extract_course_urls.py` | Inventory adapters and local workbook preparation. |
| `src/gc_stem/d2l/auth.py`, `browser.py` | Interactive login, isolated session, guarded reads. |
| `src/gc_stem/d2l/tools/` | Seven required tool adapters. |
| `src/gc_stem/d2l/content.py`, `search.py`, `reports.py` | Coordinator, matching, and reports. |
| `src/gc_stem/d2l/api.py` | Explicitly unavailable future provider seam. |
| `tests/d2l/` | Product unit, fixture, contract, integration, and explicit live cases. |
| `tests/fixtures/d2l/` | Synthetic workbooks, HTML, read events, and expected reports. |
| `config/` | Nonsecret example settings; ignored local instance overrides. |
| `docs/d2l/` | This documentation set. |

The current `src/gc-stem` and empty files are the starting structure, not the intended import package. Keep legacy experiments excluded from imports, packaging, and normal test collection; archive relocation can be a separate reviewed change.

## Work Breakdown and Construction Order

| Order | Work Item | Dependencies / Prerequisites | Completion Evidence |
| ---: | --- | --- | --- |
| 1 | Confirm proposed tool matrix; inspect SNHU content experience, pilot access, and permitted read behavior. | Operator/administrator input. | Recorded capability/read-route spike; no source/coverage promises yet. |
| 2 | Rename package; add build/project metadata and CLI registration; isolate legacy tests. | Review current imports and tooling. | Clean import/install from outside checkout; no accidental browser launch. |
| 3 | Implement settings, path origins, records, and inventory validation. | Stable contracts. | TC-001–TC-003, TC-018, TC-026. |
| 4 | Migrate and harden workbook extraction while preserving cell behavior. | Package/paths. | TC-004 with synthetic workbook round-trip evidence. |
| 5 | Build pure matching, coverage aggregation, and report writer with a fake client. | Records and schemas. | Offline end-to-end findings and truthful partial results. |
| 6 | Implement headed login/session guard and one native Content read. | Verified pilot route/marker. | TC-005, TC-021, TC-023; operator demonstrates normal login. |
| 7 | Complete Content and Manage Files adapters. | Session/provider. | Nested topics/folders, source/DOM/text/URL gaps, and limits proven. |
| 8 | Add Announcements, Assignments, and Discussions adapters. | Shared adapter contract. | Independent discovery and authored-only field tests. |
| 9 | Add Quizzes and Question Library adapters. | Safe authoring/read views; question-type inventory. | All requested question/pool fields accounted for; no attempts or edits. |
| 10 | Integrate CLI, cancellation, recovery, deterministic reports, and product CI. | All services/adapters. | All offline Must cases pass; documented invocation works. |
| 11 | Run seeded multiple-tool pilot and owner review. | Accepted local gates and operational decisions. | Recorded live evidence; release recommendation or explicit no-release gaps. |

No calendar dates or staffing commitments have been supplied. Use these dependency checkpoints rather than invented deadlines.

## Integration Strategy

### Integration Order

Integrate local services against a fake read client first. Add the browser lifecycle next, then adapters one at a time. Run shared contract tests for every adapter/provider.

Complete matching/reporting without a tenant dependency so faults can be injected predictably. Reuse the same records in browser and fake-client tests.

### Integration Verification

At each increment verify its changed contracts, targeted tests, and one representative integrated workflow. Re-run broader checks only for new changes or unresolved concerns. The full planned release suite is required once the integrated feature is ready.

A Content-only demonstration is an early increment, not completion of the broader release.

## Version Control and Change Management

### Branching and Commit Practices

Proposed workflow: small topic branches and pull requests into `main`, with commits describing observable changes. Do not claim branch protection, mandatory independent approval, or a merge strategy that has not been configured.

Keep documentation-only changes separate from code/config migration where practical. Never commit generated course scan outputs or session artifacts.

### Change Control

Preserve requirement/test IDs. A changed scope, mode, field contract, status rule, or output column must update the relevant requirements, design, pseudocode, tests, and examples together. Record new decisions in the worksheet or architecture table.

### Configuration Items

Version source, synthetic fixtures, documented schemas/examples, packaging metadata, declared dependencies, CI, and lifecycle docs. Track actual software/browser versions in test evidence. Keep internal inventories and operational reports under the maintainer's approved handling decision; do not untrack existing files automatically as part of a documentation update.

## Dependency and Supply-Chain Management

| Dependency | Version / Constraint | Purpose | License | Security / Maintenance Notes |
| --- | --- | --- | --- | --- |
| Python | Proposed `>=3.12`; declared tested versions only. | Runtime. | Verify distribution terms. | Record actual interpreter version in evidence. |
| Playwright + browser binary | Select compatible range after spike; not yet declared. | Browser reads. | Verify selected package and browser terms. | Record both package and browser versions; update with adapter regression tests. |
| openpyxl | Present but unbounded in current requirements; define tested range during packaging. | XLSX input/output. | Verify installed metadata. | Test workbook features actually supported; do not promise arbitrary Excel fidelity. |
| pytest / pytest-cov / Ruff | Development dependencies; define compatible tested ranges. | Tests, coverage, static checks. | Verify installed metadata. | Keep developer tools separate from runtime requirements. |
| Beautiful Soup / requests / Selenium | Existing list; retain only for active needs after review. | Optional parsing / future API / legacy code. | Verify each selected package. | Prefer direct `beautifulsoup4` dependency if used rather than relying on the `bs4` shim. |
| Standard library SQLite | Part of the supported Python build. | Temporary report spool. | Covered by runtime distribution. | Persist only bounded report metadata; clean up orderly. |

Do not invent dependency versions or licenses. Resolve the distribution/license position before external redistribution. Dependency maintenance and vulnerability checks are proposed practices, not existing automation claims.

## Build and Packaging

Add `[build-system]`, `[project]` metadata, package discovery, runtime/development dependencies, Python requirement, and a `gc-stem = gc_stem.cli:main` script entry. Choose the distribution name during packaging; the command name and import name serve different purposes.

Build a wheel and test it in a fresh environment from a directory outside the checkout. Exclude operational data, session artifacts, legacy experiments, and internal reports from the distribution. Do not claim `pip install -e .` works before the metadata exists.

## Construction Testing

### Unit Testing

Test validation, path origins, URL parsing, workbook preservation, matching, coverage state transitions, CSV escaping, and output failure handling with synthetic inputs. Keep pure tests independent of a browser or network.

### Integration Testing

Use fake-client runs for end-to-end outputs and fixture-driven browser views for adapters. Mark any actual tenant interaction explicitly; it must not run on a normal unit-test command.

### Test-First / Test-Driven Practices

No mandatory test-first methodology is imposed. For each behavior, establish its expected result before declaring the implementation complete. Add regression cases for meaningful defects, especially false negatives, incorrect coverage, or unsafe actions.

## Code Review and Static Verification

Review scope boundaries, mutation guard, secret handling, representation labels, report schema, and error propagation. Run targeted Ruff/compilation/tests for active new code.

Do not blindly run inherited global pytest discovery: the current pattern includes `*_test.py`, and legacy experiment filenames match it. First restrict product test paths and exclude the legacy directory.

## Security During Construction

Use synthetic fixtures and suitable pilot material. No password/MFA automation, saved browser-state file, raw HAR/trace dump, or real learner data enters fixtures, logs, build artifacts, or CI.

Before operational output exists, add reviewed ignore rules for local configuration and generated data, such as `config/*.local.toml`, session artifacts, `data/interim/d2l/`, `data/processed/d2l-search/`, and `output/`. Existing ignore rules cover common environments but not all proposed scan locations. Ignore rules do not secure files or remove already tracked data.

Validate UI/network effects in the pilot. Keep unsafe actions fatal and diagnostic. Do not add a generic `--apply` switch to the read-only search tool.

## Construction Quality Gates

| Gate | Required Evidence | Failure Response |
| --- | --- | --- |
| Package boundary | Clean import/install; no import-time checkout requirement. | Fix packaging/side effects before CLI integration. |
| Local input and search | Meaningful positive/negative unit cases pass. | Fix contract or implementation; retain failing case. |
| Provider safety | Verified login and read-route/side-effect evidence. | Do not expand live adapter use. |
| Adapter completion | Each required tool enumerates/extracts declared fields or clearly fails coverage. | Keep release scope unfulfilled; do not count a stub as support. |
| Reporting integrity | Complete/partial/error/cancel/write-failure cases and formula safety pass. | Block operational reports. |
| Release handoff | Required tests and seeded pilot pass; unresolved issues are recorded. | Recommend no release or a clearly narrower explicitly accepted release. |

## Automation and Continuous Integration

**Observed:** the existing `tests.yml` validates shared configuration and CI helpers on Python 3.12. It does not run a D2L product suite. Empty `ci.yml`/`release.yml` files do not provide those workflows.

**Planned:** add offline D2L unit/integration tests, targeted Ruff, package-build/install checks, and synthetic adapter tests. Do not run institutional login or live scans in pull-request CI. Keep live pilot execution an explicit separate activity.

The inherited policy currently requires a `LICENSE` that is absent from the snapshot, and root documentation retains course-template paths. Treat generic repository validation failures separately from D2L correctness; record and resolve relevant inherited blockers before claiming a clean project build.

## Roles and Responsibilities

| Role | Responsibility |
| --- | --- |
| Product owner / lead maintainer | Confirm scope and operational decisions; review acceptance evidence. |
| Developer / maintainer | Implement, document, integrate, and diagnose. |
| Tester / reviewer | Verify fixtures, contracts, negative cases, and evidence; an independent person is desirable when available, not assumed. |
| Authorized operator | Complete login, run pilot, review course locations and gaps. |
| Brightspace administrator / institutional contact | Clarify available access, integration constraints, and service expectations. |

Names and staffing have not been assigned. One person may hold several roles; record actual participants in execution evidence.

## Milestones and Schedule

1. Scope and tenant spike recorded.
2. Package/local pipeline works with a fake client.
3. Browser session and first read verified.
4. Each required adapter passes its contract suite.
5. Integrated offline gates pass.
6. Seeded pilot and acceptance review complete.

Dates remain unassigned; the worksheet tracks readiness and evidence.

## Construction Measures and Progress Tracking

Track implemented/verified requirements, adapter field coverage, test pass/fail/block counts, open severity-ranked defects, clean-install status, and pilot coverage gaps. Do not use lines of code or empty module count as completion measures.

## Construction Risks and Mitigations

| Risk | Likelihood / Impact | Mitigation | Trigger / Contingency |
| --- | --- | --- | --- |
| UI/source behavior differs from assumptions. | Unmeasured / High | Tenant spike before many adapters. | Revise adapter strategy; preserve unsupported gaps. |
| Existing package/CI inheritance misleads developers. | Known / High | Package migration and separate product checks. | Fix or record inherited blockers before a release claim. |
| Quiz pools/hidden fields cannot be enumerated safely. | Unmeasured / High | Question-type/pool fixtures and safe pilot reads. | Report partial; revise accepted scope rather than sample attempts. |
| Course data or session state enters Git/builds. | Unmeasured / High | Explicit exclusions, review, synthetic CI. | Remove exposed artifacts through the appropriate incident/change process; prevent recurrence. |
| Broad scope exceeds available effort. | Unmeasured / Medium | Incremental adapters and evidence-based progress. | Owner explicitly revises release scope; documentation/status rules remain truthful. |

## Construction Deliverables

Installable source package, thin CLI, seven adapter implementations, validated example configuration, workbook utility, synthetic fixtures, meaningful tests, product CI, updated docs, and execution evidence. The documentation draft itself does not supply these implementations.

## Traceability and Handoff

Map source modules and tests to requirement/decision IDs. Handoff includes exact source commit, environment/browser versions, configuration schema, test results, adapter capability matrix, pilot report, known gaps, and owner decisions.

## Open Issues

Use REQ-ISSUE-001–REQ-ISSUE-006 and the [worksheet](./worksheet.md). Do not invent API access, tool permissions, production authorization, retention, or acceptable load.

## References

* [Source and confirmed decisions](./README.md).
* [Current pyproject.toml](https://github.com/GC-STEM/automation/blob/196cda43adf48a8b3b74b3ea03101763bcb0f67f/pyproject.toml), [dependencies](https://github.com/GC-STEM/automation/blob/196cda43adf48a8b3b74b3ea03101763bcb0f67f/requirements.txt), and [core workflow](https://github.com/GC-STEM/automation/blob/196cda43adf48a8b3b74b3ea03101763bcb0f67f/.github/workflows/tests.yml).
* [PEP 8](https://peps.python.org/pep-0008/), [PEP 257](https://peps.python.org/pep-0257/), [venv](https://docs.python.org/3/library/venv.html), and [Packaging Python Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

<!--
title: "GC-STEM D2L Automation | Software Construction Plan"
document_type: "Software Construction Plan (SCP)"
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
