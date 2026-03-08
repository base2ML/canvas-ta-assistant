"""Pytest configuration for Canvas TA Dashboard tests."""

import sys
from pathlib import Path


# Add project root to sys.path so backend modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))
