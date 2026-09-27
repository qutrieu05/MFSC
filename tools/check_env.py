"""Check the development environment for MSFC (stdlib only).

Usage:
    python tools/check_env.py

Reports what is installed and which phase needs it. It never installs or changes
anything, and it does not fail the build: it prints a table and an exit code
(0 = every Phase 0/1 requirement present, 1 = something required is missing).
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

TIMEOUT_S = 8


@dataclass(frozen=True)
class Check:
    name: str
    needed_from_phase: int
    required: bool
    hint: str
    # How to detect it: "path" = executable on PATH, "module" = importable Python module.
    probe: str = "path"


CHECKS: tuple[tuple[Check, str | None], ...] = (
    (Check("python", 0, True, "Python 3.11+ (tomllib needed by the config loader)"), None),
    (Check("pytest", 0, True, "python -m pip install pytest", probe="module"), "python -m pytest --version"),
    (Check("git", 0, True, "https://git-scm.com/download/win"), "git --version"),
    (Check("nvidia-smi", 1, False, "NVIDIA driver; needed for GPU inference/training"), "nvidia-smi --version"),
    (Check("mosquitto", 1, True, "MQTT broker; install Mosquitto for Windows"), "mosquitto -h"),
    (Check("idf.py", 1, True, "ESP-IDF 5.x (ADR-0006); open the ESP-IDF terminal"), "idf.py --version"),
    (Check("gcc", 1, True, "MSYS2 MinGW-w64 gcc, for firmware host unit tests"), "gcc --version"),
    (Check("cmake", 1, False, "Needed by some firmware test setups"), "cmake --version"),
)


def run_version(command: str) -> str | None:
    try:
        completed = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=TIMEOUT_S
        )
    except (subprocess.SubprocessError, OSError):
        return None
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0].strip() if output else ""


def main() -> int:
    print(f"MSFC environment check - {platform.platform()}")
    print(f"Python {sys.version.split()[0]} ({sys.executable})\n")
    print(f"{'Tool':<12} {'Phase':<6} {'Req':<5} {'Status':<10} Detail")
    print("-" * 90)

    missing_required: list[Check] = []
    for check, version_cmd in CHECKS:
        if check.name == "python":
            present = sys.version_info >= (3, 11)
            detail = f"{sys.version_info.major}.{sys.version_info.minor}"
        else:
            if check.probe == "module":
                present = importlib.util.find_spec(check.name) is not None
            else:
                present = shutil.which(check.name) is not None
            detail = ""
            if present and version_cmd:
                detail = run_version(version_cmd) or ""
        status = "OK" if present else ("MISSING" if check.required else "optional")
        if not present and check.required:
            missing_required.append(check)
            detail = check.hint
        print(f"{check.name:<12} {check.needed_from_phase:<6} {str(check.required):<5} {status:<10} {detail[:60]}")

    print("-" * 90)
    if missing_required:
        print("\nMissing required tools:")
        for check in missing_required:
            print(f"  - {check.name} (needed from Phase {check.needed_from_phase}): {check.hint}")
        print("\nPhase 0 only needs python + pytest + git; the rest is needed before Phase 1 integration.")
        return 1
    print("\nAll required tools present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
