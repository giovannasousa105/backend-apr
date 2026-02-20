from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_LOADED = False


def load_environment() -> None:
    global _LOADED
    if _LOADED:
        return

    root = Path(__file__).resolve().parent
    env_name = os.getenv("ENV", "local").strip().lower()

    # OS/process environment must keep highest priority.
    preexisting = dict(os.environ)

    # Base file first, then environment-specific overrides.
    base = root / ".env"
    scoped = root / f".env.{env_name}"
    if base.exists():
        load_dotenv(base, override=False)
    if scoped.exists():
        load_dotenv(scoped, override=True)

    # Restore variables that already existed before dotenv loading.
    for key, value in preexisting.items():
        os.environ[key] = value

    _LOADED = True
