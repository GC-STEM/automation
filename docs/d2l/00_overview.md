# GC-STEM D2L Automation | Software Solution Overview

> **Draft for review.** Browser-first, broader course-tool search. The full search tool is proposed; the existing workbook utility is the current implementation.

## Table of Contents <!-- omit from toc -->

1. [Problem or Need](#problem-or-need)
2. [Solution Purpose](#solution-purpose)
3. [Users and Stakeholders](#users-and-stakeholders)
4. [Solution Overview](#solution-overview)
5. [Inputs](#inputs)
6. [Processing](#processing)
7. [Outputs](#outputs)
8. [Major Workflow](#major-workflow)
9. [Assumptions and Constraints](#assumptions-and-constraints)
10. [Success Criteria](#success-criteria)
11. [Related Documents](#related-documents)
12. [References](#references)

## Problem or Need

GC-STEM needs to identify courses and pages that contain particular text or embedded URLs. The target may appear in a page's visible wording, in a hyperlink, or elsewhere in its HTML. Opening course shells and checking each location manually is slow and makes omissions difficult to detect.

Course material also lives outside Brightspace's Content tool. Assignment instructions, discussion prompts, announcements, and quiz questions can contain the same target. A search that only follows Content links can miss these locations.

Earlier browser experiments demonstrated useful automation at another institution, but their login assumptions and task logic are not a reusable foundation for SNHU. The project needs a clearer separation of responsibilities and configuration that can change without editing the program.

## Solution Purpose

Provide a reusable set of D2L Brightspace tools, starting with a read-only course-content search. An authorized operator supplies a course inventory, target strings, selected tool areas, and output location. The tool searches the supported course-authored material and reports where each target appears.

The result should help maintainers find and review affected material. It must also explain what was searched and what could not be searched, so missing access or failed retrievals do not look like successful searches with no matches.

## Users and Stakeholders

| User or Stakeholder | Role or Need |
| --- | --- |
| GC-STEM administrators and course maintainers | Search authorized course shells and use results to plan follow-up work. |
| Course subject matter experts and developers | Locate affected instructions, resources, and assessment material. |
| Automation developers and maintainers | Reuse authentication, course access, content extraction, and reporting across future tools. |
| Brightspace administrators and institutional support | Clarify permissions, available integrations, and acceptable operational load. |
| Instructors and students | Benefit from corrected course material; they are not direct users of this administrative tool. |

## Solution Overview

The first release uses a browser that the operator signs into through the institution's normal login process. The operator completes SSO and MFA directly. The program does not ask for passwords or verification codes.

Separate adapters read each supported Brightspace tool. They return course-authored material in a common format. A shared search component finds the target strings, and a reporting component records matches and search coverage. A later API provider can implement the same contract if API access becomes available.

### Major Capabilities

* Prepare the existing Excel course inventory by extracting `CourseName` hyperlinks into `CourseURL`.
* Search a validated, explicit course list without discovering unrelated courses.
* Search supported authored material across multiple Brightspace tools.
* Find visible text and strings in HTML or URL attributes.
* Return course identity, tool area, object location, page URL, target, and bounded match context.
* Report incomplete searches and preserve useful results when one area fails.

## Inputs

| Input | Source | Purpose |
| --- | --- | --- |
| Course inventory | Existing Excel workflow; proposed normalized CSV alternative | Identify the courses to inspect. |
| Search targets | Operator configuration or explicit command options | Define the strings to locate. |
| Instance and crawl settings | TOML file, supported environment variables, command options | Set tenant, tool scope, matching mode, pacing, limits, and destinations. |
| Authenticated session | Operator's interactive browser login | Provide access under the operator's existing permissions. |
| Course-authored HTML and text | Supported Brightspace tool views | Supply searchable material. |

## Processing

1. Validate configuration, course identifiers, URLs, targets, and output access.
2. Open a browser and let the operator complete normal institutional login.
3. Visit only the selected courses and discover each selected tool independently.
4. Read authorized authored fields, following tool pagination and nested structures.
5. Search the requested representations and record match locations.
6. Assess coverage independently of matches, then save reports and close the session.

## Outputs

| Output | Destination | Purpose |
| --- | --- | --- |
| Processed workbook with `CourseURL` | Specified local workbook destination | Make embedded course links available for reuse. |
| `matches.csv` | Unique local run directory | Review and filter individual match locations. |
| `coverage.csv` | Same run directory | Review each course/tool's completeness, counts, exclusions, and failures. |
| `summary.json` | Same run directory | Preserve run settings, scope, version information, counts, statuses, and diagnostics. |
| Progress and exit status | Terminal | Show progress and whether the declared scan completed. |

No course changes, messages, student work, or grades are produced or modified.

## Major Workflow

1. A maintainer prepares the course list and search configuration.
2. The tool validates inputs before opening Brightspace.
3. The maintainer signs in through the displayed browser.
4. The tool searches the selected course/tool areas and records any gaps.
5. The maintainer reviews matches and coverage, then decides what course maintenance is needed.

See [23_diagram.drawio](./23_diagram.drawio), page **Search workflow**, for the proposed process.

## Assumptions and Constraints

### Assumptions

* The operator has appropriate access to the supplied courses.
* API availability is unknown; the first implementation must work through the browser.
* SNHU's content experience and tool views can be inspected in a suitable pilot shell.
* The proposed broader scope means course-authored material, not learner activity.

### Constraints

* The first search release is read-only: it must not edit content, publish items, start quiz attempts, submit work, or change grades or settings. Normal view/audit logging may still occur.
* Credentials, cookies, and tokens must not be committed or included in reports.
* Search scope and tenant data must be configurable rather than embedded in source.
* The proposed baseline includes Content, Manage Files HTML, Announcements, Assignments, Discussions, Quizzes, and Question Library. Additional tools need separate adapters and tests.
* External links can be inspected as strings, but external websites are not crawled.
* Binary document contents, media, LTI/SCORM execution, student work, and personal communications are excluded.
* Complete coverage is bounded by the declared tool set, visibility, representations, permissions, and scan period.

## Success Criteria

* A seeded target is found in each required tool area, including a target present only in an embedded URL.
* Reports identify an accessible review location or a clearly labeled containing page and object path.
* A page failure, denied area, unsupported field, or enforced limit appears as incomplete coverage.
* Unaffected content, quiz attempts, submissions, and grades remain unchanged.
* A future D2L tool can reuse the session and course-access components without copying login code.
* The existing Excel preparation workflow remains available after package migration.

## Related Documents

* [Requirements](./10_requirements.md)
* [Architecture](./19_architecture.md)
* [Design](./20_design.md)
* [Diagram](./23_diagram.drawio)
* [Pseudocode](./26_pseudocode.txt)
* [Program Design Language](./29_pdl.md)
* [Construction](./30_construction.md)
* [Testing](./40_testing.md)
* [Maintainer worksheet](./worksheet.md)

## References

* Project discussions on October 16, 2026: Brightspace Crawler Architecture; Brightspace Content Search; Extract Course URLs with Python; Normalize EOL Settings; Configure VS Code Venv.
* Project-owner clarifications on October 16, 2026: broaden search beyond Content; use browser access first while API availability is unknown; deliver downloadable drafts.
* [Repository baseline, commit 196cda4](https://github.com/GC-STEM/automation/tree/196cda43adf48a8b3b74b3ea03101763bcb0f67f).
* D2L, [Mapping Brightspace Functionality (Higher Education)](https://community.d2l.com/brightspace/kb/articles/6085-mapping-brightspace-functionality-higher-education), consulted October 16, 2026. The selected search scope is a project proposal, not a statement that every tenant exposes every field.

<!--
title: "GC-STEM D2L Automation | Software Solution Overview"
document_type: "Software Solution Overview"
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
