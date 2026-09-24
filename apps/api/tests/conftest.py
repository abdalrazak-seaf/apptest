"""Test environment.

The fixtures live in `api.testing`, registered as a pytest plugin in the root pyproject.toml.
This file only sets the environment variables the app reads when settings are first built.
"""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("STORAGE_PROVIDER", "memory")
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 32)
