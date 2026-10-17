# GC-STEM Automation

Reusable tools, scripts, and workflows for collecting and comparing data to support GC-STEM course administration, repository management, and
maintenance.

This project serves administrators, maintainers, and course developers. It provides a shared Python library and the `gc-stem` command-line interface. Initial integrations focus on read-only data retrieval through APIs and authenticated browsers.

## Table of Contents <!-- omit from toc -->

1. [Project status](#project-status)
2. [Systems in scope](#systems-in-scope)
3. [Get started](#get-started)
4. [Repository structure](#repository-structure)
5. [Development and checks](#development-and-checks)
6. [Configuration and data](#configuration-and-data)
7. [Contributing and support](#contributing-and-support)

## Project status

**Active development.** Implementation and live access verification vary by system. System documentation is the home for requirements, authentication setup, commands, implementation status, and limitations.

## Systems in scope

These are the identified data sources. Integration work is added as requirements and institutional access are confirmed.

| System | System type | Documentation |
| --- | --- | --- |
| Brightspace | Learning management system (LMS) | [docs/d2l/](docs/d2l/) |
| Kuali | Curriculum management (CM) | [docs/kuali/](docs/kuali/) |
| Banner | Student information system (SIS) | Planned |
| SharePoint | Enterprise content management (ECM) | [docs/sharepoint/](docs/sharepoint/) |
| Power BI | Business intelligence (BI) | [docs/powerbi/](docs/powerbi/) |
| Bookstore | E-commerce | [docs/bookstore/](docs/bookstore/) |
| ServiceNow | IT service management (ITSM) | [docs/servicenow/](docs/servicenow/) |
| GitHub | Source code management (SCM) | [docs/github/](docs/github/) |

## Get started

You need Git and Python 3.12 or later.

Run these commands in a terminal. Examples use `python` for the required Python version; use `python3` before activating the virtual environment if
that is your system's Python command.

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/GC-STEM/automation.git
cd automation
python -m venv .venv
```

Activate the environment using the command for your shell:

| Platform and shell | Command |
| --- | --- |
| Linux or macOS, Bash | `source .venv/bin/activate` |
| Windows, Git Bash | `source .venv/Scripts/activate` |
| Windows, PowerShell | `.\.venv\Scripts\Activate.ps1` |

Install the package and development tools, then check the command interface:

```bash
python -m pip install -e ".[dev]"
gc-stem --help
```

Editable installation makes changes under `src/` available in the active environment. Reinstall after changing dependencies or package entry points.

You can also run the CLI as `python -m gc_stem`.

## Repository structure

| Location | Purpose |
| --- | --- |
| [src/gc_stem/](src/gc_stem/) | Importable Python library and shared CLI. |
| [docs/](docs/) | System requirements, design, usage, and status. |
| [tests/](tests/) | Automated tests organized by system and integration scope. |
| [scripts/](scripts/) | Standalone scripts and operational entry points. |
| [config/](config/) | Nonsecret configuration and examples. |
| [data/](data/) | Source inputs, reference data, intermediate files, and outputs. |
| [.github/](.github/) | Workflows, CI checks, and maintainer configuration. |
| [pyproject.toml](pyproject.toml) | Package metadata and development settings. |

Use matching system folders under `docs/<system>/`,
`src/gc_stem/<system>/`, and `tests/<system>/`. Keep each
system's authentication, API access, and browser access within its package.
Add folders and modules as their documentation, code, and tests are needed.

As workflows are added, place coordination that combines systems under `src/gc_stem/workflows/`, with matching documentation and tests. Extract shared helpers when multiple integrations need them.

## Development and checks

With the development environment active, run:

```bash
python -m ruff check src/gc_stem tests
python -m pytest tests -q
python -m build
```

The build command creates a wheel and source distribution in `dist/`.

GitHub Actions checks repository conventions, documented command syntax, documentation links, and implemented toolsets. See [workflow definitions](.github/workflows/) and [Actions results](https://github.com/GC-STEM/automation/actions).

The [release preparation workflow](.github/workflows/release.yml) builds and verifies downloadable distributions for review before publication.

## Configuration and data

Keep service addresses, input paths, search terms, and other operational settings outside source code. Store only nonsecret settings in committed configuration files.

Keep credentials, session cookies, browser profiles, and restricted inputs or reports out of version control. Review `.gitignore` and staged changes before committing local data. A file's location under `data/` does not automatically exclude it from Git.

Run service automation with authorized access. Review generated reports before sharing them.

## Contributing and support

Use [GitHub Issues](https://github.com/GC-STEM/automation/issues) to report bugs, request features, or discuss proposed changes. Include the relevant system or workflow, Python version, command, and redacted error output.

When adding or extending an integration:

- Document requirements, usage, and implementation status under
  `docs/<system>/`.
- Organize reusable code under `src/gc_stem/<system>/`, including an
  `__init__.py` file for each Python package.
- Add matching tests under `tests/<system>/` using synthetic fixtures or   mocked service responses. Make live tests explicitly opt-in.
- Add nonsecret configuration examples and extend the CLI and CI checks   as needed.
- Follow PEP 8 and PEP 257 for Python code and docstrings.
- Keep this README focused on project scope, shared setup, and navigation.

Keep service access, configuration, processing, and reporting separate so future tools can reuse shared components.
