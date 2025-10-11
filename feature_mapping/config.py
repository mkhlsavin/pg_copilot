from __future__ import annotations

from pathlib import Path
from typing import Optional


DEFAULT_POSTGRES_SRC: Path = Path(r"C:\Users\user\postgres-REL_17_6\src")
DEFAULT_JOERN_HOME: Path = Path(r"C:\Users\user\joern")
DEFAULT_CPG_PATH: Path = DEFAULT_JOERN_HOME / "workspace" / "pg17_full.cpg"


def locate_joern_binary() -> Path:
    """Return the Joern executable path for the local workstation."""
    candidates = [
        DEFAULT_JOERN_HOME / "joern.bat",
        DEFAULT_JOERN_HOME / "joern.cmd",
        DEFAULT_JOERN_HOME / "joern",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path("joern")


DEFAULT_JOERN_BINARY: Path = locate_joern_binary()


def validate_environment() -> Optional[str]:
    """Return a warning string if the expected local setup is incomplete."""
    missing = []
    if not DEFAULT_POSTGRES_SRC.exists():
        missing.append(f"PostgreSQL sources at '{DEFAULT_POSTGRES_SRC}'")
    if not DEFAULT_JOERN_BINARY.exists():
        missing.append(f"Joern executable at '{DEFAULT_JOERN_BINARY}'")
    if not DEFAULT_CPG_PATH.exists():
        missing.append(f"Joern CPG at '{DEFAULT_CPG_PATH}'")
    if not missing:
        return None
    return "Missing expected resources: " + ", ".join(missing)
