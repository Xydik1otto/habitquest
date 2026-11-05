"""Console-script entry point: `habitquest` starts the local server."""
from __future__ import annotations

import argparse
import webbrowser
from functools import partial

import uvicorn

from .main import app  # noqa: F401  (uvicorn target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="habitquest",
        description="HabitQuest — local gamified habit tracker (FastAPI + SQLite).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true",
                        help="do not open the browser automatically")
    args = parser.parse_args(argv)
    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass  # headless systems — the URL is printed below anyway
    print(f"HabitQuest running at {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
