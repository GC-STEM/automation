# GC-STEM Automation

Reusable Python tools, scripts, and workflows for GC-STEM course
administration, repository management, and maintenance.

This project is intended for administrators, maintainers, and course
developers. It provides a shared Python library and the `gc-stem`
command-line interface. D2L Brightspace is the first toolset; additional
capabilities will be added as requirements are defined.

## Contents

1. [Contents](#contents)
2. [Project status](#project-status)
3. [Get started](#get-started)
4. [D2L tools](#d2l-tools)
5. [Repository structure](#repository-structure)
6. [Development and checks](#development-and-checks)
7. [Configuration and data](#configuration-and-data)
8. [Contributing and support](#contributing-and-support)

## Project status

**Active development.** Availability varies by toolset.

| Capability | Current status |
| --- | --- |
| D2L workbook preparation | Available: extract course hyperlinks into a `CourseURL` column. |
| D2L configuration and course inventory validation | Available for supported Excel and CSV inputs. |
| D2L search, coverage, and reporting components | Implemented and tested with synthetic clients. |
| Live Brightspace search | Pending browser authentication and tenant-specific tool adapters. |

See the [D2L documentation](docs/d2l/README.md) for requirements and design.
The [implementation status](docs/d2l/50_implementation_status.md) identifies
available commands and remaining work.

## Get started

You need Git and Python 3.12 or later.

Run these commands in a terminal. Examples use `python` for the required
Python version; use `python3` before activating the virtual environment if
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

Editable installation makes changes under `src/` available in the active
environment. Reinstall after changing dependencies or package entry points.

You can also run the CLI as `python -m gc_stem`.

## D2L tools

Run the following commands from the repository root.

View workbook preparation options:

```bash
gc-stem d2l courses extract-urls --help
```

Review [config/d2l.toml](config/d2l.toml), including the course inventory path,
worksheet, column names, and example search terms. Paths inside this TOML
file are relative to the configuration file's directory.

Validate the local configuration and course inventory:

```bash
gc-stem d2l search --config config/d2l.toml --validate-only
```

Validation checks local inputs and output access. It does not connect to
Brightspace or establish search coverage.

For workbook extraction commands, supported overrides, and search behavior,
see [D2L implementation status](docs/d2l/50_implementation_status.md).
Live Brightspace search will become available after the browser provider and
tool adapters are implemented and verified.

## Repository structure

| Location | Purpose |
| --- | --- |
| [src/gc_stem/](src/gc_stem/) | Importable Python package and shared CLI. |
| [src/gc_stem/d2l/](src/gc_stem/d2l/) | D2L Brightspace toolset. |
| [scripts/](scripts/) | Standalone scripts and operational entry points. |
| [config/](config/) | Nonsecret configuration and examples. |
| [data/](data/) | Source inputs, intermediate files, and processed outputs. |
| [docs/](docs/) | Requirements, design, usage, and implementation documentation. |
| [tests/](tests/) | Automated tests organized by toolset. |
| [.github/](.github/) | Repository workflows, CI checks, and maintainer configuration. |
| [pyproject.toml](pyproject.toml) | Package metadata, dependencies, and development settings. |

## Development and checks

With the development environment active, run:

```bash
python -m ruff check src/gc_stem tests
python -m pytest tests -q
python -m build
```

The build command creates a wheel and source distribution in `dist/`.

GitHub Actions provides these checks and packaging workflows:

| Workflow | Purpose |
| --- | --- |
| [Core Validation](.github/workflows/ci.yml) | Validate repository configuration, CI safeguards, and workflow syntax. |
| [D2L local checks](.github/workflows/d2l.yml) | Lint, test, build, and check CLI entry points on Windows and Linux. |
| [Documentation Command Syntax](.github/workflows/readme-commands.yml) | Check documented Bash command syntax. |
| [Internal Links](.github/workflows/internal-links.yml) | Check local documentation links and supported heading anchors. |
| [External Links](.github/workflows/external-links.yml) | Check external documentation links. |
| [Release preparation](.github/workflows/release.yml) | Manually build, verify installation, and upload downloadable distributions. |

Review results on the project's
[Actions page](https://github.com/GC-STEM/automation/actions).
Release preparation produces artifacts for review; publication is a separate
step.

## Configuration and data

Keep service addresses, input paths, search terms, and other operational
settings outside source code. Store only nonsecret settings in committed
configuration files.

Keep credentials, session cookies, browser profiles, and restricted inputs or
reports out of version control. Review `.gitignore` and staged changes before
committing local data. A file's location under `data/` does not automatically
exclude it from Git.

Run service automation with authorized access. Review generated reports
before sharing them.

## Contributing and support

Use [GitHub Issues](https://github.com/GC-STEM/automation/issues) to report
bugs, request features, or discuss proposed changes. Include the relevant
tool, Python version, command, and redacted error output.

When adding a toolset:

- Organize reusable code under `src/gc_stem/<toolset>/`.
- Add matching tests, configuration examples, and documentation.
- Extend the CLI and CI checks as needed.
- Follow PEP 8 and PEP 257 for Python code and docstrings.
- Update this README and the toolset's implementation status when
  availability changes.

Keep service access, configuration, processing, and reporting separate so
future tools can reuse shared components.
