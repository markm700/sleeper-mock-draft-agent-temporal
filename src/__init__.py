"""Sleeper Mock Draft Agent - Temporal Version.

This package groups Temporal workflows, activities, and supporting code.

FastAPI (`api` module) is intentionally *not* imported at package-import time
so that non-HTTP processes (like the Temporal worker service) do not require
FastAPI to be installed. Import `src.api` directly in HTTP services instead of
relying on `src` side effects.
"""