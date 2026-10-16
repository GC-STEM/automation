# Optional Course Repository Components

This directory contains optional files, folders, and configuration templates for use when developing individual GC-STEM course repositories.

These components are intended **only for repository maintainers and course Subject Matter Experts (SMEs)**. The `optional/` directory is part of the CS000 master template and must not appear in published course repositories.

## Table of Contents <!-- omit from toc -->

1. [Purpose](#purpose)
2. [Using Optional Components](#using-optional-components)
3. [Important Considerations](#important-considerations)

## Purpose

Not every course requires the same development tools, configurations, or directory structure. This directory provides reusable components that course developers can selectively incorporate based on course requirements.

- **Optional:** Include only components needed for the course.
- **Inactive:** Files stored here are not intended to serve as active course configurations.
- **Customizable:** Some files are empty placeholders or minimal configurations that require customization before use.
- **Temporary:** The entire `optional/` directory must be removed before publishing a course repository.

## Using Optional Components

When preparing an individual course repository:

1. **Select:** Identify the optional files and folders needed for the course.
2. **Move:** Copy selected components to their intended locations relative to the repository root, preserving any required directory structure.
3. **Configure:** Complete placeholder files and customize settings for the course's languages, tools, platforms, and requirements.
4. **Validate:** Confirm that selected components work correctly and do not conflict with existing repository settings.
5. **Clean up:** Delete the entire `optional/` directory, including all unused components.
6. **Publish:** Verify that the repository contains only approved course content and configuration.

For example, a course requiring Ruff could copy `optional/config/linting/ruff.toml` to `/ruff.toml` and configure its Python linting rules.

## Important Considerations

- Do not assume that an optional file is ready for use simply because it exists or passes a syntax check.
- Do not copy all optional components into a course repository by default.
- Follow the course's approved development environment and configuration standards.
- Confirm that no required course materials or configurations remain in `optional/` before deleting it.

**Publication requirement:** The final course repository must be self-contained and must not depend on any files or folders within `optional/`.

---

*Maintainer note: This directory is a development resource in `GC-STEM/cs000`, not part of the student-facing course repository structure.*
