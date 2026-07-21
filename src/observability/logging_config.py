"""
Centralized logging configuration for workers and FastAPI .

Call :func:`setup_logging` once at process startup (each worker's ``main()`` and
the FastAPI ``lifespan``). This routes Python's standard ``logging`` — which the
Temporal SDK's ``workflow.logger`` / ``activity.logger`` adapters write to — to
stdout at the configured level, so ``.info()`` logs actually surface (the root
logger defaults to WARNING otherwise).

Configuration is environment-driven:

* ``LOG_LEVEL``  — root level (default ``INFO``); e.g. ``DEBUG``, ``WARNING``.
* ``LOG_FORMAT`` — ``console`` (default, human-readable) or ``json`` (structured;
  one JSON object per line, including any ``extra`` fields and the Temporal
  workflow/activity context the SDK attaches to each record).
"""

import json
import logging
import os
import sys
from typing import Optional

# Attributes present on every LogRecord — anything else in JSON output.
# Temporal's injected workflow/activity context surfacing as extra fields.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime", "taskName"}

_CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# Repeated calls (tests, reloads) do not stack duplicate handlers
_CONFIGURED = False


class JSONFormatter(logging.Formatter):
    """Render log records as single-line JSON objects, including extra fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Merge any non-standard attributes (logger `extra=...` and the
        # workflow_id / activity context the Temporal SDK attaches).
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str)


def setup_logging(level: Optional[str] = None, fmt: Optional[str] = None) -> None:
    """
    Configure root logging for the current process. Idempotent.

    Args:
        level: Log level name (e.g. "INFO"). Defaults to ``LOG_LEVEL`` env var, then "INFO".
        fmt: "console" or "json". Defaults to ``LOG_FORMAT`` env var, then "console".
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    fmt_name = (fmt or os.getenv("LOG_FORMAT", "console")).lower()
    formatter: logging.Formatter = (
        JSONFormatter() if fmt_name == "json" else logging.Formatter(_CONSOLE_FORMAT)
    )

    # Hijack root logger to stdout 
    # Temporal SDK loggers propagate to root
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    # Replace any pre-existing handlers
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)

    # Temporal SDK loggers propagate to root; quiet the noisier gRPC/core internals unless DEBUG requested.
    logging.getLogger("temporalio").setLevel(log_level)
    if log_level > logging.DEBUG:
        logging.getLogger("temporalio.worker").setLevel(logging.INFO)

    _CONFIGURED = True
    root.info("Logging configured (level=%s, format=%s)", level_name, fmt_name)