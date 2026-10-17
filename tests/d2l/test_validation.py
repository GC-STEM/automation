"""Test local validation and output probing without any browser/network work."""

import pytest
from d2l_test_helpers import Harness

from gc_stem.d2l.config import ConfigurationError
from gc_stem.d2l.courses import InventoryError
from gc_stem.d2l.validation import validate_inputs


def test_validation_prepares_exact_inventory_and_literal_plan(
    harness: Harness,
) -> None:
    """Successful preflight returns the concrete inputs for a later scan."""
    report = validate_inputs(harness.settings)
    assert report.inventory == harness.inventory
    assert report.plan.targets[0].text == "needle"
    assert report.output_ancestor == harness.root


def test_validation_leaves_no_report_directory_or_probe(
    harness: Harness,
) -> None:
    """Local validation has no persistent report side effects."""
    before = set(harness.root.iterdir())
    original = harness.source.read_bytes()
    validate_inputs(harness.settings)
    assert set(harness.root.iterdir()) == before
    assert not harness.settings.output.directory.exists()
    assert harness.source.read_bytes() == original


def test_existing_output_directory_can_be_probed(harness: Harness) -> None:
    """A valid existing report root is reused without changing its contents."""
    harness.settings.output.directory.mkdir()
    marker = harness.settings.output.directory / "previous-report.txt"
    marker.write_text("keep", encoding="utf-8")
    report = validate_inputs(harness.settings)
    assert report.output_ancestor == marker.parent
    assert list(marker.parent.iterdir()) == [marker]


def test_file_in_output_parent_chain_is_rejected(harness: Harness) -> None:
    """A non-directory ancestor cannot be treated as a creatable destination."""
    harness.configure(**{"output.directory": str(harness.source / "reports")})
    with pytest.raises(ConfigurationError, match="Output directory"):
        validate_inputs(harness.settings)


def test_probe_failure_is_observable_and_sanitized(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Permission/disk failures fail local preflight without leaking details."""
    monkeypatch.setattr(
        "gc_stem.d2l.validation.NamedTemporaryFile",
        lambda **kwargs: (_ for _ in ()).throw(PermissionError("AUTH_SECRET")),
    )
    with pytest.raises(ConfigurationError) as caught:
        validate_inputs(harness.settings)
    assert "AUTH_SECRET" not in str(caught.value)


def test_inventory_failure_precedes_output_probe(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid course identities fail before output or provider work."""
    harness.source.write_text("org_unit_id\ninvalid\n", encoding="utf-8")

    def forbidden_probe(**kwargs: object) -> None:
        """Fail the test if validation reaches output after invalid input."""
        raise AssertionError("Output was probed too early")

    monkeypatch.setattr(
        "gc_stem.d2l.validation.NamedTemporaryFile", forbidden_probe
    )
    with pytest.raises(InventoryError):
        validate_inputs(harness.settings)
