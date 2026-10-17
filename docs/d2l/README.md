# GC-STEM D2L Automation | Documentation

Current code availability, commands, verification, and remaining live-provider work are tracked in [Implementation Status](./50_implementation_status.md).

> **Draft for review — October 16, 2026.** These documents describe the proposed D2L tools and their construction. They do not certify that the crawler is implemented or tested.

## Table of Contents <!-- omit from toc -->

* [Purpose](#purpose)
* [Confirmed Direction](#confirmed-direction)
* [Document Map](#document-map)
* [Repository Baseline](#repository-baseline)
* [Scope and Coverage](#scope-and-coverage)
* [Reading Results Correctly](#reading-results-correctly)
* [Decisions Still Needed](#decisions-still-needed)
* [Updating the Drafts](#updating-the-drafts)

## Purpose

Build reusable Brightspace automation for GC-STEM, beginning with a browser-based search of course-authored HTML, visible text, and embedded URLs across an explicit list of courses. Keep authentication, course discovery, extraction, matching, and reporting separate so later D2L tools can reuse them.

## Confirmed Direction

The project owner requested:

* A reusable Python library and automation tools, with better abstraction than the earlier browser experiments.
* Configuration outside the source code and protection of secrets.
* Search across a supplied course list for target strings in HTML, including visible text and embedded URLs.
* Broader coverage than the Content tool alone.
* Browser access first while SNHU API availability remains unknown.
* Downloadable documentation matching the existing `docs/d2l` filenames.

The exact tool matrix, command names, defaults, report schema, and technology choices below are **proposed implementation decisions**. They make this draft concrete; they are not additional approvals or claims of existing functionality.

## Document Map

| File | Read it to understand |
| --- | --- |
| [00_overview.md](./00_overview.md) | The problem, users, scope, workflow, and expected value. |
| [10_requirements.md](./10_requirements.md) | Proposed functional requirements, quality requirements, acceptance, and scope boundaries. |
| [19_architecture.md](./19_architecture.md) | System boundaries, reusable components, browser/API separation, and major decisions. |
| [20_design.md](./20_design.md) | Interfaces, data models, configuration, search semantics, reports, and error handling. |
| [23_diagram.drawio](./23_diagram.drawio) | Editable architecture and search-workflow diagrams. |
| [26_pseudocode.txt](./26_pseudocode.txt) | Language-independent algorithms for URL extraction and course search. |
| [29_pdl.md](./29_pdl.md) | Python-oriented design contracts and control logic; not executable product code. |
| [30_construction.md](./30_construction.md) | Implementation order, environment, migration work, integration, and quality gates. |
| [40_testing.md](./40_testing.md) | Planned tests, requirement coverage, evidence, and release criteria. |
| [worksheet.md](./worksheet.md) | Maintainer decisions, checkpoints, and handoff record. |

Read the overview and requirements first. Use architecture and design together during implementation. Construction and testing describe planned work; no product test results are implied.

## Repository Baseline

Repository contents were fetched from GitHub on October 16, 2026. The `main` branch was resolved with a cache-busting query, then files were read at immutable commit [196cda4](https://github.com/GC-STEM/automation/commit/196cda43adf48a8b3b74b3ea03101763bcb0f67f).

| Observed item | Meaning for this draft |
| --- | --- |
| `src/gc-stem/d2l/extract_course_urls.py` contains working source code. | It is the existing local workbook utility. Its behavior was reviewed; it was not executed for this documentation task. |
| Other current D2L modules and `tests/d2l` files are empty. | Authentication, crawling, searching, reporting, and D2L tests are planned capabilities. |
| `src/gc-stem/d2l/old` contains earlier experiments. | It is reference material, not the production implementation or an SNHU login solution. |
| `config/d2l.toml` selects browser/interactive access. | It supplies useful draft defaults, but its referenced `data/courses.csv` does not exist in the snapshot. |
| Raw and processed `gc-stem_d2l_courses.xlsx` files exist. | The proposed first inventory adapter supports the existing Excel workflow. |
| `pyproject.toml` configures development tools but has no build or project metadata. | Package installation and the proposed `gc-stem` command require construction work. |
| The package directory is named `gc-stem`. | Rename it to `gc_stem` for normal Python import syntax. |
| The root README and some CI checks retain course-template content. | General repository cleanup is a separate prerequisite, not completed by these drafts. |

## Scope and Coverage

The proposed first release covers **instructor- or course-authored material** in Content, Manage Files HTML files, Announcements, Assignments, Discussions, Quizzes, and Question Library. Each selected tool needs its own validated adapter. This is broader than following links in Content.

Survey, Checklist, Rubric, custom-widget, and other tool adapters are extension candidates. Their absence must remain visible in the run's declared scope. The release must not advertise a search of “all Brightspace content.”

Student submissions, discussion contributions, quiz attempts, grades, personal messages, external websites, and the contents of PDF/Office/media/SCORM/LTI resources are outside this draft's search scope. A link to such a resource can still match.

## Reading Results Correctly

A result has two independent dimensions:

* **Match status:** `FOUND`, `NOT_FOUND`, or `UNKNOWN`.
* **Coverage status:** `COMPLETE`, `PARTIAL`, or `ERROR` for a course.

A course may have `FOUND` matches and `PARTIAL` coverage at the same time. `NOT_FOUND` is valid only when the declared scope was completely searched. A denied tool, unavailable HTML field, failed page, unfinished question pool, or page limit cannot become a clean negative.

See the authoritative [status rules](./20_design.md#state-and-mode-behavior).

## Decisions Still Needed

| Decision | Resolution needed before |
| --- | --- |
| Confirm the proposed seven-tool matrix and any additional tool areas. | Freezing release scope. |
| Identify a suitable SNHU pilot shell, test identity, content experience, and safe read routes. | Live browser testing. |
| Determine API availability, supported versions, and approved authentication. | Implementing the deferred API provider. |
| Agree acceptable crawl load and output handling/retention. | Routine operational use. |
| Validate access to hidden/draft content and every quiz/question-library field. | Claiming complete coverage for those areas. |

These are recorded with owners and triggers in the requirements and worksheet. None requires guessing institutional policy.

## Updating the Drafts

Preserve requirement, decision, and test identifiers when wording changes. Update related documents together when a contract changes. Record the new source commit and actual test evidence during construction.

This package contains only the eleven replacement files under `docs/d2l`. It does not change source code, shared templates, configuration, GitHub branches, or Brightspace.

<!--
title: "GC-STEM D2L Automation | Documentation"
document_type: "Documentation Index"
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
