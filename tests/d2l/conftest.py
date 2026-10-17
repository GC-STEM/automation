"""Supply isolated synthetic local fixtures for D2L pipeline tests."""

from pathlib import Path

import pytest
from d2l_test_helpers import Harness


@pytest.fixture
def harness(tmp_path: Path) -> Harness:
    """Create fresh configuration, inventory, and clock for each case."""
    return Harness(tmp_path)
