"""Convenience launcher for the Official Dashboard, runnable from the repository root:

    python edge/run_dashboard.py [--host 127.0.0.1] [--port 8000]

Equivalent to ``cd edge && python -m msfc.dashboard`` (see OFFICIAL_DASHBOARD_USER_GUIDE.md) --
this wrapper only exists so the dashboard can be launched without first ``cd``-ing into
``edge/``, which matters for tooling (e.g. .claude/launch.json) that runs from the repo root.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from msfc.dashboard.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
