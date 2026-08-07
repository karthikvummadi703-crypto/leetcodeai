"""
Shared pytest fixtures / configuration.

This module is imported by pytest before any test module, so the
``MEMORY_STORE`` override here is guaranteed to be in place before the
conversation store is selected. Tests must never touch real Firestore.
"""

import os

os.environ["MEMORY_STORE"] = "memory"
os.environ["RATE_LIMIT_ENABLED"] = "false"
