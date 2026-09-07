"""Test fixtures and Hermes stubs for standalone testing."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add repo root to sys.path so plugin becomes a package
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub hermes_constants when running outside Hermes
if "hermes_constants" not in sys.modules:
    mock = MagicMock()
    mock.get_hermes_home.return_value = Path("/tmp/test-hermes")
    sys.modules["hermes_constants"] = mock

# Import plugin package (triggers __init__.py which imports the stub)
import plugin  # noqa: E402, F401
