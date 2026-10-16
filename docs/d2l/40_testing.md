# GC-STEM D2L Automation | Software Test Plan

> **Planned verification.** No product tests or live Brightspace tests were executed for this documentation task. TC identifiers below name planned case groups, not completed test implementations.

## Table of Contents <!-- omit from toc -->

* [Purpose and Scope](#purpose-and-scope)
* [Test Objectives](#test-objectives)
* [Test Scope](#test-scope)
* [Test Strategy](#test-strategy)
* [Requirements Traceability](#requirements-traceability)
* [Test Environment](#test-environment)
* [Test Data](#test-data)
* [Test Tools and Automation](#test-tools-and-automation)
* [Test Case and Procedure Design](#test-case-and-procedure-design)
* [Pass / Fail Criteria](#pass--fail-criteria)
* [Entry, Suspension, Resumption, and Completion Criteria](#entry-suspension-resumption-and-completion-criteria)
* [Defect and Test-Incident Management](#defect-and-test-incident-management)
* [Regression and Retesting Strategy](#regression-and-retesting-strategy)
* [Specialized Quality Testing](#specialized-quality-testing)
* [Roles and Responsibilities](#roles-and-responsibilities)
* [Test Schedule and Milestones](#test-schedule-and-milestones)
* [Test Risks and Contingencies](#test-risks-and-contingencies)
* [Test Metrics and Reporting](#test-metrics-and-reporting)
* [Test Deliverables](#test-deliverables)
* [Test Evidence and Reproducibility](#test-evidence-and-reproducibility)
* [Approval and Release Recommendation](#approval-and-release-recommendation)
* [Open Issues](#open-issues)
* [References](#references)

## Purpose and Scope

### Purpose

Establish whether the proposed search safely finds course-authored targets, reports their locations accurately, and describes incomplete coverage truthfully. Support construction feedback and an evidence-based release recommendation.

### System Under Test

The planned `gc_stem.d2l` package, CLI, local workbook utility, browser read client, seven required tool adapters, matcher, coverage aggregation, and CSV/JSON outputs.

The repository baseline has an implemented workbook utility and empty new crawler/test scaffolds. It is not a tested search release.

### Test Basis

[Requirements](./10_requirements.md), [architecture](./19_architecture.md), [design](./20_design.md), [pseudocode](./26_pseudocode.txt), [PDL](./29_pdl.md), and the source observations/decisions in [README.md](./README.md).

## Test Objectives

* Find known targets in authored visible text, source HTML, and embedded URLs across every required tool area.
* Prove selected course/tool/visibility/representation boundaries.
* Prevent missing access, unsupported fields, limits, and interrupted enumeration from becoming clean negatives.
* Verify no authoring, publication, attempt, submission, grade, or settings changes.
* Preserve the existing workbook workflow and support package execution outside a checkout.
* Produce useful, reproducible, bounded, spreadsheet-safe reports without secrets or learner data.

## Test Scope

### Features to Be Tested

All Must requirements, NFR-001–NFR-012, the seven-tool scope matrix, configuration/input errors, normal/negative/partial flows, session handling, request/navigation guards, output failure, cancellation, and installation.

Test each adapter's authored-field families and visibility/representation combinations, not just whether its listing page opens.

### Features Not to Be Tested

API integration, regex execution, persisted sessions, cross-run resume/cache, additional tool adapters, document/media parsing, SCORM/LTI execution, writes/remediation, scheduling, and dashboards. FR-022 receives only an interface/capability review in this increment.

No penetration testing, institutional load testing, or probing outside authorized pilot scope is part of this plan.

### Test Assumptions and Constraints

Live tests require a suitable pilot shell, permitted access, and known seeded material. No such environment has been supplied or used for this task. UI and permission differences must be recorded rather than assumed equivalent.

Offline tests must not collect the legacy `*_test.py` experiments or open a live session accidentally. Use a bounded explicitly selected product test path before enabling broader discovery.

## Test Strategy

### Test Levels

| Test Level | Objective | Scope | Responsible Role |
| --- | --- | --- | --- |
| Unit | Verify local rules and state transitions. | Settings, identity, workbook behavior, matching, coverage, serialization. | Developer/tester. |
| Contract | Verify normalized provider/adapter behavior. | Discovery endings, field outcomes, typed failures, object identity. | Developer/reviewer. |
| Offline integration | Verify the whole local pipeline. | Fake client, synthetic browser views, writer and CLI. | Developer/tester. |
| Controlled system pilot | Verify actual SNHU login/read behavior and scope. | Suitable pilot courses and selected tools. | Authorized operator + developer. |
| Acceptance | Judge whether evidence satisfies declared release scope. | All Must/NFRs and operational decisions. | Product owner/maintainer. |

### Test Types

Functional, boundary, negative, interface, installation, compatibility, data integrity, security/privacy, cancellation/recovery, and bounded-resource tests. Use actual performance measurements for planning, without inventing a throughput or duration SLA.

### Test Techniques

Use explicit expected results from synthetic fixtures, equivalence classes for valid/invalid inventory, boundary values for limits, and fault injection for retrieval/session/output failures. Use seeded end-to-end scenarios for independently discoverable tool objects and URL-only targets.

Use fake clocks for waits/backoff so offline suites do not sleep in real time. Review network effects and object state separately from returned match rows.

### Test Prioritization

Highest priority: unsafe actions or data leakage; false negatives; incomplete coverage labeled complete; incorrect course identity; output corruption. Next: login/recovery, independent tool enumeration, path/install behavior, and operator usability.

## Requirements Traceability

| Requirement / Objective | Test ID(s) | Test Level / Type | Expected Evidence |
| --- | --- | --- | --- |
| FR-001 | TC-001 | Unit/configuration | Precedence, origin, type, and redaction assertions. |
| FR-002 | TC-002 | Unit/integration | Equivalent Excel/CSV normalized inventories. |
| FR-003 | TC-003 | Unit/negative | Tenant/ID conflicts fail before live access; duplicates diagnosed. |
| FR-004 | TC-004 | Unit/workbook integration | Workbook round-trip assertions for values, hyperlinks, styles, sheets, and destination behavior. |
| FR-005 | TC-005 | Fixture + controlled live authentication | Normal SSO/MFA, tenant/sentinel verification, no credential program input. |
| FR-006 | TC-006 | Contract/system | Independent enumeration and seeded positive locations in all seven tools. |
| FR-007 | TC-007 | Contract/privacy | Declared authored fields only; visibility behavior and gap evidence. |
| FR-008 | TC-008 | Contract/boundary | Complete nested/paged enumeration, cycle detection, truthful limits. |
| FR-009 | TC-009 | Unit/adapter integration | Source/DOM/text/URL distinctions and missing-representation coverage. |
| FR-010 | TC-010 | Unit/functional | Independent literal, case, and occurrence behavior. |
| FR-011 | TC-011 | Integration/security | URL-only findings with no external destination reads. |
| FR-012 | TC-012 | Unit/system | Correct field/provenance, count/context, and verified review links. |
| FR-013 | TC-013 | Integration/output | Required files, fixed columns, parseable schema, stable final order. |
| FR-014 | TC-014 | Unit/fault scenarios | Findings/coverage truth table, including empty tools. |
| FR-015 | TC-015 | Fault/recovery | Correct retry/cooldown/session behavior with bounded attempts. |
| FR-016 | TC-016 | Integration/cancellation | Preserved acquired data; unfinished scope; cleanup; nonzero outcome. |
| FR-017 | TC-017 | Integration/reproducibility | Actual software/config/input/scope/timing metadata. |
| FR-018 | TC-001, TC-018 | Unit/negative | Unsupported/unsafe settings rejected; no live effects. |
| FR-019 | TC-019 | Integration/filesystem/security | No overwrite; final-manifest-last behavior; safe CSV; honest output-failure status. |
| FR-020 | TC-018 | CLI/integration | Validation-only checks local inputs without browser/network. |
| FR-021 | TC-020 | Contract/architecture | Reusable client interfaces; pure logic does not import provider. |
| FR-022 | TC-020 | Deferred-provider review | Capability seam documented; API selection explicitly unsupported. |
| NFR-001 | TC-015, TC-022 | Fault/performance | Bounded pace, waits, retries, and limits. |
| NFR-002 | TC-014–TC-016, TC-019 | Reliability | No false completion or loss of orderly acquired results. |
| NFR-003 | TC-021 | Safety | Guards and before/after evidence show no prohibited state changes. |
| NFR-004 | TC-005, TC-023 | Security | No deliberate auth persistence/logging or credential configuration. |
| NFR-005 | TC-007, TC-011, TC-023 | Privacy/security | No learner data; minimal excerpts; external blocking. |
| NFR-006 | TC-018, TC-024 | Usability/accessibility | Textual help, errors, progress, cancellation, and exit meanings. |
| NFR-007 | TC-020, TC-025 | Structure/quality | Offline seams, clean imports, meaningful static/documentation review. |
| NFR-008 | TC-017, TC-023 | Diagnostics | Useful structured sanitized events. |
| NFR-009 | TC-026 | Portability | Paths behave from different CWDs and installed layouts. |
| NFR-010 | TC-025–TC-026 | Installation/compatibility | Recorded supported OS/Python/browser evidence. |
| NFR-011 | TC-008, TC-022 | Resource/boundary | Object-at-a-time processing, spool, and explicit truncation. |
| NFR-012 | TC-017, TC-027 | Freshness | New retrieval per run and scan interval recorded. |

## Test Environment

### Hardware and Infrastructure

Offline tests run locally or in CI without institutional connectivity. Browser fixture tests use an isolated local server. Live tests use an operator workstation and suitable pilot shell(s), not learner submissions or live assessments.

No server deployment is required. Record actual hardware/resource context for performance measurements.

### Software and Versions

Initial target: Python 3.12 and the selected compatible Playwright/browser version. Record exact versions used; no browser version has been selected by this draft. The existing core CI's Python 3.12 setting is not a D2L product compatibility result.

Test Windows first, then each additional advertised platform. Record untested platforms as unverified.

### Environment Configuration

Use synthetic configuration/inventories, fake clients, verified local UI fixtures, and explicit live markers. The product test suite must disable live network/login unless deliberately selected.

Local settings contain no secrets. Live login is interactive. Never provide cookies or MFA secrets through CI variables for this release.

### Monitoring and Logging

Capture sanitized structured test events, expected/actual report rows, request/action categories, elapsed time, counts, and final state. Use local synthetic browser traces if needed; do not retain real login HAR/state or restricted screenshots as normal evidence.

For live read-only verification, record permitted route/action categories and before/after object-state observations without exporting credentials or complete assessment bodies.

## Test Data

### Test Data Requirements

Prepare synthetic datasets covering:

* Excel `D2L` worksheet with and without `CourseURL`; external hyperlinks; empty hyperlinks; preexisting URL cells; internal links/formulas; extra sheets; representative formatting.
* Valid/invalid tenant course URLs, IDs, duplicates, contradictory identity rows, and CSV equivalents.
* Nested modules/files, more than one listing page, hidden/draft/date-filtered objects, genuinely empty tools, denied tools, and unexpected view markup.
* Tool objects not linked from Content, unused Question Library entries, quiz pools with more members than displayed questions, and several question/feedback field types.
* Targets in text, source-only comments/attributes, entity-encoded URLs, relative URLs, `srcset` candidates, CSS URLs, frames/open shadow fragments, and unsupported representations.
* Unicode, literal regex metacharacters, repeated occurrences, multiline fields, oversized fields, and CSV formula-leading values.
* Transient failures, cooldowns, session expiry, cancellation, object limits, and disk/permission/rename failures.

### Test Data Preparation

Store synthetic fixtures with source and expected outcomes under product fixture paths. Assign stable IDs and annotate intentional duplicates, exclusions, and unsupported states.

Create fresh temporary workbooks, output directories, and local spool files per test. Restore fixture state between browser cases. Do not modify the repository's internal course inventory to create tests.

### Sensitive or Regulated Test Data

Do not copy real learner records or assessment banks into CI. Prefer synthetic/explicitly suitable pilot content. Live match excerpts and location reports may still be restricted; use the agreed operational handling and remove temporary evidence when no longer needed. No retention period is supplied by this plan.

## Test Tools and Automation

Use pytest for product tests, pytest-cov where useful to identify untested branches, Ruff for static checks, standard temporary files/mocking, and Playwright for local browser fixtures. These are planned product checks; the current repository's generic CI does not execute them.

Manual activities remain normal institutional login, live permissions/view confirmation, read-only side-effect checks, and final operator acceptance. Do not automate around MFA.

## Test Case and Procedure Design

Each case records ID, source requirement, version/environment, fixture identity, preconditions, steps, expected result, actual result, status, and evidence location. Parameterize a case group where behavior varies by tool, field, mode, or platform.

| Test ID | Objective / Requirement | Preconditions | Inputs / Steps | Expected Result | Automation |
| --- | --- | --- | --- | --- | --- |
| TC-001 | Settings precedence / FR-001, FR-018 | Local settings parser. | Conflict CLI/env/TOML/default values; unknown keys/types; empty targets; unsafe flags. | Documented precedence/origins; invalid settings fail specifically; no browser. | pytest, planned. |
| TC-002 | Inventory formats / FR-002 | Synthetic Excel/CSV equivalents. | Read configured worksheet/columns and normalized CSV; include optional metadata. | Same validated course identities and source-row diagnostics. | pytest. |
| TC-003 | Identity/scope / FR-003 | URL parser and inventory validation. | Wrong host, userinfo, malformed route, fractional ID, ID/URL mismatch, repeated course, empty inventory. | Conflicts/invalid rows fail preflight; valid duplicates scanned once and reported. | pytest. |
| TC-004 | Workbook contract / FR-004 | Synthetic workbook with extra sheet/styles. | Run existing-column and missing-column variants; include no-target rows and internal/formula links; missing header/sheet; destination conflicts/failure. | Targets copied; column added as needed; unrelated data retained; missing-target values unchanged; safe destination handling. | pytest + openpyxl round trip. |
| TC-005 | Login/session / FR-005, NFR-004 | Local auth fixture; suitable live pilot for final evidence. | Complete normal login/MFA; test wrong tenant, stale marker, timeout, canceled login. | Only verified tenant session starts reads; no credential config or auth artifacts. | Fixture automation; live manual. |
| TC-006 | Independent tool scope / FR-006 | All seven synthetic tool adapters. | Seed text/URL targets in every area; include assignment/quiz/library items absent from Content links. | Each selected tool independently finds expected locations and emits a terminal enumeration result. | Offline contract; live seeded pilot. |
| TC-007 | Authored fields / FR-007, NFR-005 | Field-family and visibility fixtures. | Hidden/draft settings; learner records beside authored metadata; unavailable quiz type/model-answer field. | Only documented authored fields searched; explicit exclusions/gaps; no learner extraction. | Fixtures + pilot spot checks. |
| TC-008 | Traversal / FR-008, NFR-011 | Nested/paged fixtures. | Multiple pages, repeated cursor, cycles, inaccessible folder, unknown pool membership, zero-item confirmed tool, limits. | Complete traversal or truthful gaps; no infinite loop or silent truncation. | pytest/fake client. |
| TC-009 | Representation fidelity / FR-009 | Paired source/rendered/text/URL fixtures. | Source differs from DOM; visible text differs from hidden HTML; iframe/shadow content; missing source; empty and plain-text fields. | Mode selects required applicable representations; labels/offsets correct; missing HTML representations affect coverage. | pytest + local browser. |
| TC-010 | Literal matching / FR-010 | Pure matcher. | Multiple terms, case variants, metacharacters, repeated/adjacent occurrences, whitespace, Unicode. | Independent literal matches/counts; case rule documented; blank terms rejected; no regex execution. | pytest. |
| TC-011 | URL-only match / FR-011, NFR-005 | External request trap on local server. | Target only in href/src/link topic; entity and relative variants; srcset/CSS cases. | Expected raw/resolved URL findings; zero external destination requests; unsupported parse cases are explicit. | Local browser + matcher. |
| TC-012 | Location/provenance / FR-012 | Known objects/fields. | Multiple occurrences and containing paths; question without direct URL. | Correct course/tool/object/field; one row per key; count/first offset; <=200-code-point context; verified direct or labeled container location. | pytest + pilot links. |
| TC-013 | Output contract / FR-013 | Complete fake-client run. | Serialize and parse all files twice with stable input order. | Fixed schemas/order; required files; unique run directory; counts distinguish rows and unique locations. | pytest. |
| TC-014 | Coverage truth table / FR-014 | Coverage aggregator. | Found+partial; zero+complete; zero+partial/error; confirmed empty; NOT_APPLICABLE; NOT_SELECTED; missing menu without proof. | FOUND/PARTIAL can coexist; only complete zero becomes NOT_FOUND; uncertain zero is UNKNOWN. | pytest. |
| TC-015 | Retry/session recovery / FR-015, NFR-001 | Fake clock/read client. | Timeout then success; exhausted retries; 403; unknown view; cooldown > wait bound; session expiry and reauth exhaustion. | Appropriate bounded reads only; no retry of denied/unsafe work; no premature cooldown retry; truthful gaps. | Fault-injection pytest; pilot session confirmation. |
| TC-016 | Cancellation/cleanup / FR-016 | In-progress run with acquired match. | Cancel during discovery/read/auth; simulate cleanup issue. | Acquired results retained when finalizable; unfinished work labeled; resources closed; 130 or 1 for output failure. | Offline integration. |
| TC-017 | Metadata / FR-017, NFR-008, NFR-012 | Known input/version/config. | Complete and partial runs. | Actual versions/known commit or explicit null; input digest; redacted settings; scope; UTC interval; consistent counts. | pytest. |
| TC-018 | Validation/help/unsupported mode / FR-018, FR-020 | CLI and no-network trap. | --validate-only; bad paths; empty courses; API/regex/unsafe flags; --help. | Useful text; no browser/network; clear exit code 2 for invalid settings. | CLI integration. |
| TC-019 | Atomic/safe output / FR-019, NFR-002 | Filesystem fault injection. | Existing run; write/rename failure; formula-leading title/context/target including leading controls. | Prior runs preserved; no false complete manifest; safe CSV fields; exit 1 and actual partial paths on failure. | pytest. |
| TC-020 | Reuse/provider seam / FR-021–FR-022 | Fake read client; import inspection. | Use another read operation without matcher/writer imports; run shared client contracts. | Access components reusable; no provider objects leak; API unavailability explicit. | Contract tests + review. |
| TC-021 | Read-only effects / NFR-003 | Guard fixture; controlled pilot with baseline state. | Attempt prohibited save/publish/delete/start-attempt/submit/evaluate routes/actions; run permitted reads. | Prohibited actions blocked/fatal; no course, assessment-attempt, submission, grade, or settings changes. | Guard automation + live before/after review. |
| TC-022 | Load/resource bounds / NFR-001, NFR-011 | Fake clock and scalable fixtures. | Grow course/object counts; exceed page/object/field bounds; inspect concurrent reads/spool. | One active read; pacing and bounds honored; raw HTML not accumulated; truncation visible. | Automated resource experiment. |
| TC-023 | Secret/privacy artifacts / NFR-004–NFR-005, NFR-008 | Synthetic secret sentinels. | Put tokens/auth-like data in shell/error/redirect contexts; inspect logs/files/temp cleanup/build artifacts. | No credential/cookie/header persistence or learner/raw-page output; bounded snippets only; sanitized diagnostics. | Automated artifact checks + review. |
| TC-024 | Operator usability / NFR-006 | Usable CLI and pilot operator. | Run from help through complete/partial/canceled outcomes without color; inspect errors and progress. | Scope/gaps/exit meanings clear; no mouse dependence outside normal login; operator can locate a match. | CLI assertions + manual review. |
| TC-025 | Package/code quality / NFR-007, NFR-010 | Packaging increment complete. | Build/install in clean environment; inspect distribution and imports; run targeted static/product checks. | Importable package/CLI; no import side effects; no operational data/legacy tests in build; declared runtime evidence. | CI/local automation. |
| TC-026 | Path/platform behavior / NFR-009–NFR-010 | Config tree with spaces/relative paths. | Invoke from multiple CWDs; explicit CLI/env paths; installed package without checkout; supported OS matrix. | Config-relative and invocation-relative rules hold; no hardcoded user path or pyproject discovery. | pytest + platform checks. |
| TC-027 | Fresh runs / NFR-012 | Mutable synthetic content source. | Run once; change source; run again with same settings. | Second run reads new content; separate run IDs/intervals; no silent previous-run cache. | Offline integration. |

The table is a planned specification. Automated implementations and actual outcomes must be added during construction.

## Pass / Fail Criteria

### Test Case Pass Criteria

**Pass:** observed behavior matches the stated expectation with adequate evidence. **Fail:** behavior contradicts it. **Blocked:** environment or prerequisite prevents execution. **Skipped:** deliberately outside the selected test scope with a recorded reason. **Inconclusive:** evidence does not establish the result.

Blocked, skipped, and inconclusive cases do not count as passing coverage. An exception without a useful report may still fail the case even if the process exits nonzero.

### Test Suite Acceptance Criteria

All applicable Must requirements and NFRs need passing evidence. No unresolved defect may permit prohibited writes, secret/learner-data exposure, wrong-course access, false clean negatives, or corrupted/false-complete output.

Every required adapter must pass its declared field/representation cases and seeded pilot evidence. No arbitrary code-coverage percentage substitutes for behavior. Use branch coverage to identify untested critical paths.

A fixture-only pass is insufficient for tenant compatibility or safe live behavior.

## Entry, Suspension, Resumption, and Completion Criteria

### Entry Criteria

Offline entry requires stable local contracts, suitable fixtures, and live-network isolation. Browser fixture entry requires the selected package/browser. Live entry requires suitable pilot access/content, known scope, local gates, and an operator.

### Suspension Criteria

Stop live testing for suspected mutation, credential exposure, unauthorized navigation, uncontrolled traffic, unusable identity/session, or unexpected learner-data retrieval. Suspend affected offline groups when fixtures or expected outcomes are invalid.

### Resumption Criteria

Resolve and review the cause, correct fixtures/guards/implementation, reset the controlled environment if needed, and rerun the relevant safety/local cases before live work resumes.

### Completion / Exit Criteria

Required cases have meaningful results, release-blocking defects are resolved, evidence identifies remaining scope limits, and the owner has enough information to accept or decline the release. Scope reduction requires explicit owner agreement and updated requirements; it cannot be hidden by skipping tests.

## Defect and Test-Incident Management

Record reproducible input/fixture, source commit, environment, expected/actual behavior, severity, related requirement/test, and sanitized evidence. Distinguish product defects from environment, permission, and inherited repository issues.

Prioritize unsafe actions/exposure and false negatives first. Retest the specific fix and the related integration paths. Do not paste real tokens, full assessment content, or learner data into public issues.

## Regression and Retesting Strategy

Keep local matching/coverage/inventory/report contracts in the normal offline regression suite. Add a case for each meaningful escaped defect. Re-run adapter fixtures after browser/UI changes and targeted live confirmation when safe-read assumptions or tenant views change.

Do not rerun broad live scans merely because a documentation typo or unrelated local change occurred.

## Specialized Quality Testing

### Performance and Scalability Testing

Measure elapsed time, objects/fields processed, retries, rate behavior, memory, and spool size on synthetic and suitable pilot workloads. Verify bounded resource behavior and pacing first. Record observed throughput without presenting it as an agreed SLA.

A total-course completion-time or maximum load target remains an operational decision. No institution-wide load test is authorized by this plan.

### Security Testing

Verify configuration rejection of credential/unsafe options, session artifact handling, route/action guards, course/tenant boundaries, CSV formula neutralization, and minimized outputs. Review dependencies and build contents. Keep scope to the product and suitable pilot; do not probe identity services for vulnerabilities.

### Reliability, Recovery, and Resilience Testing

Inject session expiry, denied areas, transient service failures, enumeration loops, incomplete pools, cancellation, cleanup trouble, and output faults. Validate acquired results, final states, and non-success codes independently.

### Usability and Accessibility Testing

Verify readable text in help/errors/progress, keyboard operation of the CLI, non-color status communication, and a clear partial-coverage summary. Use the normal accessible institutional login flow; this tool does not replace it or claim its compliance.

## Roles and Responsibilities

The developer owns automated fixtures and defect fixes. The authorized operator performs live login and pilot review. The maintainer/reviewer assesses independent evidence and data handling. The product owner decides release scope and acceptance. No individual staffing or independent testing team is assumed.

## Test Schedule and Milestones

Tests follow construction increments: local contracts → fake-client pipeline → browser/session spike → each adapter → integrated regressions → controlled seeded pilot → release review. Dates are not assigned.

## Test Risks and Contingencies

| Risk | Impact on Testing / Product | Mitigation | Contingency |
| --- | --- | --- | --- |
| No suitable tenant/pilot access. | Live behavior unverified. | Complete offline contracts and document environment need. | Keep live cases blocked; no operational-release claim. |
| UI or permissions differ across shells. | Fixture coverage may not generalize. | Record content experience/role; test representative variants. | Declare verified capability boundaries and partial results. |
| Question pools cannot be enumerated. | False confidence if a sample is used. | Explicit pool fixtures and evidence. | Keep coverage incomplete; do not start attempts. |
| Generic CI appears green without D2L tests. | Product readiness overstated. | Separate product workflow and result report. | Record inherited checks separately from product evidence. |
| Sensitive evidence accidentally retained. | Privacy/security exposure. | Synthetic fixtures and minimized artifacts. | Stop affected testing and use the institution's appropriate response process. |

## Test Metrics and Reporting

Report planned/executed/pass/fail/block/skip counts, Must/NFR evidence coverage, required adapter/field coverage, safety defects, false-negative defects, and unresolved operational gaps. Keep actual results separate from planned case counts.

At each implementation milestone, provide the maintainer a concise status with evidence links and blockers. The current state is **planned, not executed**; the 27 groups above are not a passing-test count.

## Test Deliverables

Synthetic fixtures, automated product tests, environment/version record, sanitized logs/report examples, defect records, adapter capability matrix, controlled pilot evidence, and a test-completion/release-recommendation record.

These deliverables are construction outputs. This documentation package supplies the plan, not those results.

## Test Evidence and Reproducibility

For each important result retain test ID, source commit, runtime/browser/OS versions, fixture or inventory digest, redacted effective settings, exact procedure, expected/actual outcome, UTC time, and responsible person/workflow.

Live course changes mean a run is a scan interval, not a reproducible transactional snapshot. Record relevant state/limitations and use stable synthetic fixtures for exact regression reproduction.

## Approval and Release Recommendation

The product owner/lead maintainer reviews evidence against declared scope and open decisions. A release recommendation requires passing required evidence and no release-blocking issues. Missing live access or an unverified required adapter supports a no-release recommendation for the broader scope, not an inferred pass.

This document does not request or grant production approval.

## Open Issues

Confirm the seven-tool matrix, pilot environment/role, safe read behaviors, question-field coverage, tested platform/browser list, and operational load/output handling. API availability remains unknown and is deferred.

## References

* [Requirements](./10_requirements.md), [architecture](./19_architecture.md), [design](./20_design.md), and [construction](./30_construction.md).
* [Source baseline and decisions](./README.md).
* Playwright, [Authentication](https://playwright.dev/python/docs/auth) and [Locators](https://playwright.dev/python/docs/locators), consulted October 16, 2026.

<!--
title: "GC-STEM D2L Automation | Software Test Plan"
document_type: "Software Test Plan (STP)"
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
