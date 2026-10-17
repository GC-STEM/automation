# D2L Reference Data

Versioned JSON catalogs for navigation templates and Brightspace replace
strings. Load them with Python's standard-library `json` module. They add no
runtime dependency.

## Files

| File | Contents |
| --- | --- |
| [course_routes.json](course_routes.json) | All 40 course-tool URL templates and reported student-access flags from the source document. |
| [replace_strings.json](replace_strings.json) | All 18 source placeholders, their scopes, and documentation context. |

Both files use `schema_version = 1` and record their source commit, Git blob,
section, and row line numbers. Consumers should check `schema_version` and
`catalog_type` before reading records. Record IDs, token names, and property
names are case-sensitive JSON strings.

Source: [d2l_replace_strings.md](../../../docs/d2l/d2l_replace_strings.md).
The source link in each JSON file points to the immutable version converted.

## Route catalog

Each route contains:

- `id`: unique identifier derived from the source page label.
- `label`: source page label, with HTML entities decoded.
- `path_template`: root-relative path, query, and fragment.
- `student_accessible_reported`: Boolean conversion of the source SA column.
- `source_line`: row location in the pinned source file.

Build a candidate URL by adding the validated course's tenant origin to the
template after substituting its validated `OrgUnitId`. The original SNHU
origin is retained as provenance; operational origins come from configuration.

Query parameters, path case, and fragments are preserved, including the
trailing `#` on the Awards view route. HTML `&amp;` is decoded to `&`.

These are reference URLs awaiting live verification. The reported SA flag
does not establish permissions, read-only behavior, or safe crawler access.
Several entries lead to administration, creation, grading, or learner-data
views. Providers must separately verify permitted routes and safe reads.

These tool-entry URLs are distinct from the inventory's `CourseURL` values.
The current inventory loader accepts course-home URLs using
`/d2l/home/ID` or `/d2l/p/home/ID`. Its validation remains unchanged.
The source table supplies no Manage Files route; none has been invented.

## Replace-string catalog

Each token records its exact brace-delimited spelling, normalized scope,
original table group, concise description, documented contexts, exclusions,
and source line.

The source's Current Value cells contain unresolved placeholder text. This
catalog stores definitions. Actual organization, course, and user values
belong in a separate run context.

These are Brightspace personalization variables, not find-and-replace
instructions. The catalog contains no replacement actions.

The current [D2L documentation](https://community.d2l.com/brightspace/kb/articles/6105-automatically-customize-course-content-using-replace-strings)
documents these distinctions:

- Content topics evaluate applicable strings when entered and retain no
  record of the original placeholder.
- Other tools evaluate supported strings when viewed.
- User and role strings are unavailable in Content topics.
- Supported contexts vary. `documented_contexts` records examples from the
  documentation, not an exhaustive SNHU support matrix.

`FirstName` includes `course_banner` because the documentation demonstrates
that use in its example. Its table lists Metadata.

Two source descriptions need qualification. D2L describes `UserName` as a
full name or login username, and `Email` as an internal email address. The
catalog uses those meanings and preserves the earlier descriptions in
`source_description`.

Preserve token spelling when generating content. The catalog does not claim
that alternate capitalization is accepted by Brightspace. Literal searches
can find authored tokens; a rendered or previously substituted value needs
its own search target.

## Consume from Python

Run this example from the repository root after installing the project:

```python
import json
from pathlib import Path

from gc_stem.d2l.config import load_settings
from gc_stem.d2l.courses import load_courses
from gc_stem.d2l.search import compile_targets

reference = Path("data/reference/d2l")
routes = json.loads(
    (reference / "course_routes.json").read_text(encoding="utf-8")
)
strings = json.loads(
    (reference / "replace_strings.json").read_text(encoding="utf-8")
)

if (
    routes.get("schema_version") != 1
    or routes.get("catalog_type") != "brightspace_course_routes"
    or strings.get("schema_version") != 1
    or strings.get("catalog_type") != "brightspace_replace_strings"
):
    raise ValueError("Unsupported reference catalog.")

settings = load_settings("config/d2l.toml")
course = load_courses(settings).courses[0]
content = next(row for row in routes["routes"] if row["id"] == "content")
candidate_url = course.tenant_origin + content["path_template"].format(
    OrgUnitId=course.org_unit_id
)

plan = compile_targets(
    [row["token"] for row in strings["tokens"]],
    ignore_case=False,
)
```

This example prepares a candidate URL and literal search targets locally.
It makes no service request.

The current CLI does not automatically load these catalogs. Keep them
separate from `config/d2l.toml`, whose schema rejects unknown settings.
A future provider can load routes explicitly; search callers can pass token
strings to the existing matcher.

## Maintenance

Update the JSON catalogs alongside changes to their source definitions.
Retain stable IDs, preserve source provenance, and increment the schema
version when the format changes. Keep live verification evidence separate
from source-reported access claims.
