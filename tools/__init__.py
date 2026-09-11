"""Story Architect tools package."""
import sys
from pathlib import Path

# Ensure repo root is on sys.path so core/ and tools/ are importable
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
