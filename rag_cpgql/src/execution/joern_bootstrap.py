"""Utility helpers to keep the Joern server bootstrapped for workflow execution."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SCRIPT = PROJECT_ROOT / "scripts" / "bootstrap_joern.ps1"

_JOERN_BOOTSTRAPPED = False


def verify_joern_connection(
    server_endpoint: str = "localhost:8080",
    retries: int = 5,
    delay_seconds: float = 2.0,
) -> bool:
    """Verify a Joern server is reachable by issuing a lightweight query.

    Returns:
        True when the server responds successfully within the allotted retries.
    """
    try:
        from src.execution.joern_client import JoernClient
    except Exception as exc:  # pragma: no cover
        logger.error("Unable to import JoernClient: %s", exc)
        return False

    for attempt in range(1, retries + 1):
        client = JoernClient(server_endpoint=server_endpoint)
        try:
            if client.connect():
                client.close()
                return True
        finally:
            client.close()

        if attempt < retries:
            logger.info(
                "Joern connection attempt %s/%s failed; retrying in %.1fs",
                attempt,
                retries,
                delay_seconds,
            )
            time.sleep(delay_seconds)

    logger.error("Unable to verify Joern connection at %s", server_endpoint)
    return False


def ensure_joern_ready(
    force_restart: bool = False,
    execution_policy: str = "Bypass",
    server_endpoint: str = "localhost:8080",
) -> bool:
    """Ensure the Joern server is running and the PostgreSQL workspace is loaded."""
    global _JOERN_BOOTSTRAPPED

    if _JOERN_BOOTSTRAPPED and not force_restart:
        if verify_joern_connection(server_endpoint=server_endpoint, retries=1, delay_seconds=0.0):
            return True
        logger.warning(
            "Previous Joern bootstrap appears stale; attempting to re-run bootstrap script."
        )
        _JOERN_BOOTSTRAPPED = False

    if not BOOTSTRAP_SCRIPT.exists():
        logger.error("Joern bootstrap script not found at %s", BOOTSTRAP_SCRIPT)
        return False

    command = [
        "powershell",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        execution_policy,
        "-File",
        str(BOOTSTRAP_SCRIPT),
    ]

    if force_restart:
        command.append("-ForceRestart")

    logger.info("Bootstrapping Joern server via %s", BOOTSTRAP_SCRIPT)

    try:
        result = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover
        logger.error("PowerShell not available to run Joern bootstrap: %s", exc)
        return False

    if result.returncode != 0:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if stdout:
            logger.error("Joern bootstrap stdout:\n%s", stdout)
        if stderr:
            logger.error("Joern bootstrap stderr:\n%s", stderr)
        logger.error("Joern bootstrap script exited with code %s", result.returncode)
        return False

    if result.stdout:
        logger.debug("Joern bootstrap output:\n%s", result.stdout.strip())

    if not verify_joern_connection(server_endpoint=server_endpoint):
        logger.error("Joern bootstrap completed, but the server is still unreachable.")
        return False

    _JOERN_BOOTSTRAPPED = True
    logger.info("Joern server is ready for queries.")
    return True


def reset_bootstrap_state():
    """Reset cached bootstrap state (useful for tests or forced restarts)."""
    global _JOERN_BOOTSTRAPPED
    _JOERN_BOOTSTRAPPED = False
