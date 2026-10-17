# D2L Implementation Status

This batch completes the provider-independent search pipeline and local CLI.
It was prepared against repository commit
`0c4dd5e3f07690b57b957262a850996214f200a6`. That commit identifies the input
baseline, not a commit containing these new files.

**Live Brightspace search is not available yet.** The browser provider,
authentication verification, and seven tenant-specific adapters still need
SNHU route, view, and side-effect evidence. A normal live search command exits
with code 2 before opening a browser or creating a report run. Test clients
identify themselves as synthetic in report metadata.

## Available code

| Module | Implemented behavior |
| --- | --- |
| `models.py` | Immutable identities, authored fields, representation outcomes, discovery/read results, and bounded matches. Previously delivered. |
| `config.py` | Strict nonsecret settings, schema, precedence, and path origins. Previously delivered. |
| `courses.py` | Validated Excel/CSV inventories, tenant identities, duplicates, and input digest. Previously delivered. |
| `extract_course_urls.py` | Workbook preparation with preserved source, configurable headers/sheet, and protected output. Previously delivered. |
| `search.py` | Escaped literal targets, stable IDs, per-representation matching, bounded context, and explicit gaps. |
| `client.py` | Read protocol, capabilities, typed failures, pacing, retry/cooldown handling, and bounded reauthentication. Live factory explicitly unavailable. |
| `coverage.py` | Tool/course coverage and independent FOUND/NOT_FOUND/UNKNOWN aggregation. |
| `content.py` | Sequential supplied-client scan, independent tool enumeration, replay/deduplication, limits, cancellation, cleanup, and report finalization. |
| `reports.py` | Unique run directory, SQLite spool, deterministic CSV, formula protection, and JSON manifest published last. |
| `validation.py` | Local input/target validation and temporary output-permission probe. |
| `gc_stem.cli` / `gc_stem.__main__` | Workbook preparation, local validation, documented exit codes, and a supplied-provider scan path. |

The existing browser/auth/API placeholder files are not live implementations.
No API availability or parity is assumed. No replacement/authoring operation
is included in this search batch.

## Install and check

After copying this batch into the repository, refresh editable metadata so
the newly enabled `gc-stem` console entry point is registered:

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/d2l -q
python -m ruff check src/gc_stem tests/d2l
python -m build
```

The module entry point is also available as `python -m gc_stem`.

## Local commands

From the repository root, prepare a new workbook destination:

```powershell
python -m gc_stem d2l courses extract-urls --source "data/raw/gc-stem_d2l_courses.xlsx" --destination "data/processed/gc-stem_d2l_courses.xlsx" --sheet "D2L"
```

An existing destination is refused unless `--overwrite` is explicitly added.
This delegates to the previously delivered workbook utility; the source is
always protected. Use a different destination to retain an older processed
workbook.

Validate configuration and inventory locally:

```powershell
python -m gc_stem d2l search --config "config/d2l.toml" --validate-only
```

The example terms remain placeholders; replace them in TOML or use repeated
`--term` options when preparing a real search. Repeated terms/tools replace
their configured lists. Supported overrides include `--courses`,
`--courses-format`, `--sheet`, `--name-column`, `--url-column`, `--id-column`,
`--output`, `--mode`, and `--case-sensitive`. A file's explicit format and
column mappings remain effective until overridden; changing just the file
path does not silently replace those mappings.

TOML paths use the TOML directory. Environment/CLI paths use the invocation
directory. `D2L_CONFIG` may select the configuration file. Only the previously
documented supported D2L environment variables are accepted.

Local validation reads the complete inventory, compiles targets, and creates
then removes an empty permission probe in the nearest existing output
ancestor. It creates no persistent report directory and does not verify live
Brightspace access.

## Supplied-client library scans

`scan_courses(settings, inventory, client, writer)` now implements the complete
local orchestration path. Supply a client obeying `BrightspaceReadClient` and
a `ReportWriter` for the same settings/inventory. The coordinator authenticates
and closes the client, then finalizes/closes the writer. It returns `RunResult`
with state, exit code, course results, finalized output paths when available,
and paths to actual recoverable artifacts on failure.

The fixture client is confined to `tests/d2l`; it is not shipped as a live
provider or exposed as a command-line scan option. Do not substitute synthetic
course reads when interpreting results as a live audit.

## Matching and counts

* Targets are literal, numbered in first-input order, and deduplicated by
  exact original text. Nonblank leading/trailing characters are preserved.
* Case-insensitive matching uses Python `re.IGNORECASE`, not full Unicode
  case-fold equivalence. Counts are nonoverlapping; offsets refer to original
  Unicode strings. Each match retains at most 200 context characters.
* HTML requires source/DOM/text as selected by mode; explicitly supplied
  applicable URL outcomes also participate in DOM/all modes. Adapters should
  emit URL attributes as separate URL fields, retaining raw/resolved variants
  at distinct paths. Plain text is searched in every mode. URL fields are
  omitted in visible-text mode.
* Missing required representations, invalid not-applicable declarations,
  missing fields, and oversized values produce coverage gaps. Values are not
  silently substituted or truncated.
* `objects_scanned` requires every requested applicable field outcome to
  succeed. Partial/interrupted discovered objects count as failed. A boundary
  lookahead object beyond the object limit is still counted as discovered,
  unattempted failed work.
* `fields_scanned` counts successful field/representation pairs.
  `fields_unavailable` counts representation gaps plus wholly missing field
  entries. Match rows and unique `course/tool/object/field` locations have
  separate counts.
* Object reads are bounded per tool. Discovery events are bounded to
  `2 * max_objects_per_tool + 1` to stop duplicate-only loops. Actual page
  counts, navigation/readiness timeouts, permitted routes, and browser-side
  effects remain obligations of the future concrete provider.
* Server cooldowns apply across operations, including after retries are
  exhausted. A cooldown above the allowed wait stops further service reads
  and finalizes a partial run. Reauthentication has a shared per-run budget.

## Reports and completion

Each scan owns a new run directory. Final outputs are `matches.csv`,
`coverage.csv`, and `summary.json`; all seven baseline tool rows are present
per course, including explicit exclusions. Matching and coverage are separate:
FOUND can coexist with PARTIAL coverage; an uncertain zero is UNKNOWN.

Report records are spooled to SQLite without retaining raw authored fields.
CSV strings that could trigger spreadsheet formulas, including after leading
whitespace/controls, receive an apostrophe prefix. JSON keeps original course
metadata and settings where included; it does not contain full authored pages
or session state. Context remains a bounded CSV match value.

Files are written and flushed through temporary files, then published without
replacement using local hard links. The filesystem must support hard links.
Both CSV files precede `summary.json`; a failed publication cannot leave a
fabricated completion manifest. Unfinished runs retain available CSV/spool
artifacts; successful finalization removes the spool. Power-loss recovery and
resumable scans are not implemented.

| Exit | Meaning |
| ---: | --- |
| 0 | Local command succeeded, or declared scan coverage completed. |
| 1 | Fatal run, cleanup, or output failure. |
| 2 | Invalid input or unavailable live feature; no crawl started. |
| 3 | Scan/deferred run has incomplete declared coverage. |
| 130 | Operator canceled; any finalized manifest explicitly says canceled. |

## Verification for this batch

The combined suite passed **361 tests and 180 subtests** on Python 3.12.14
in the development environment, including 191 new test cases.
Coverage includes complete/partial/failed/canceled runs, seven independent
synthetic tools, retries, shared cooldowns, reauthentication, scope faults,
replayed discovery, size/object bounds, stable report schemas, CSV formula
handling, secret sentinels, and output-failure injection.

Ruff 0.17.1 checks passed, and both source and wheel distributions built.
The wheel was installed separately and exercised outside the checkout:
imports came from the installed package, both command entry points worked,
and local validation accepted the current 186-row inventory without changing
it or creating a report run. An unavailable live scan returned exit code 2.

The new GitHub workflow repeats lint/tests/build checks
on Windows and Linux with Python 3.12 and 3.14. Its remote jobs have not run as
part of preparing these downloadable files; local results do not establish
Windows/Python 3.14 compatibility for the new batch.

## Remaining live work

1. Verify SNHU's tenant return/authenticated marker and permitted read routes
   through a controlled pilot using normal SSO/MFA.
2. Implement the guarded Playwright session/authentication provider, including
   actual navigation budgets, timeouts, external blocking, and cleanup.
3. Implement and verify the seven authored-field adapters: Content, Manage
   Files, Announcements, Assignments, Discussions, Quizzes, and Question Library.
4. Connect the verified browser provider in `client.create_client()` and run
   seeded live acceptance tests, including network/side-effect evidence.

The design/test documents remain the acceptance basis. Synthetic success is
evidence for the shared pipeline, not evidence for SNHU selectors, source
availability, hidden-field access, question enumeration, or live read safety.
