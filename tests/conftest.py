import sys
from pathlib import Path

# Add repo root to sys.path so `core` and `tools` are importable as top-level packages
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))
