"""Run: ``python -m msfc.dashboard`` (from ``edge/``, with ``src`` on PYTHONPATH -- see
OFFICIAL_DASHBOARD_USER_GUIDE.md). Starts the Official Dashboard locally; no cloud deployment,
no external services (section 3)."""

from __future__ import annotations

import argparse

import uvicorn

from msfc.dashboard.api import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="S1 Mini Smart Factory Cell -- Official Dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_app()
    print(f"S1 Official Dashboard -- SOFTWARE SIMULATION, no hardware -- http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
