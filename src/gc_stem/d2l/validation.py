"""Validate local scan inputs without opening or importing a browser backend."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from .config import ConfigurationError, Settings
from .courses import Inventory, load_courses
from .search import SearchPlan, compile_targets


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Hold prepared inputs and the successfully probed output ancestor."""

    settings: Settings
    inventory: Inventory
    plan: SearchPlan
    output_ancestor: Path


def validate_inputs(settings: Settings) -> ValidationReport:
    """Validate inventory, targets, and local output creatability.

    Args:
        settings: Validated result of load_settings().

    Returns:
        Inputs suitable for a future supplied-client scan. No persistent
        report directory is created; an empty temporary permission probe is
        removed from the nearest existing output ancestor.

    Raises:
        InventoryError: If any course input is invalid.
        ConfigurationError: If targets/output paths cannot be used.

    A successful local preflight does not verify Brightspace access or
    guarantee that later filesystem/network operations will succeed.
    """
    inventory = load_courses(settings)
    try:
        plan = compile_targets(
            settings.search.terms, settings.search.ignore_case
        )
    except (TypeError, ValueError):
        raise ConfigurationError("Invalid literal search targets.") from None
    ancestor = settings.output.directory
    try:
        while not ancestor.exists():
            if ancestor.parent == ancestor:
                raise OSError
            ancestor = ancestor.parent
        if not ancestor.is_dir():
            raise OSError
        with NamedTemporaryFile(dir=ancestor, prefix="d2l-validation-"):
            pass
    except OSError:
        raise ConfigurationError(
            "Output directory cannot be created or written."
        ) from None
    return ValidationReport(settings, inventory, plan, ancestor)
