"""
SAFIR-Dashboard · bokeh_app.server
====================================
CLI launcher for the SAFIR Bokeh dashboard.

Usage
-----
::

    python -m SAFIR-Dashboard.bokeh_app.server --db path/to/results.db [OPTIONS]

    # or, from the repo root:
    python SAFIR-Dashboard/bokeh_app/server.py --db path/to/results.db

Options
-------
``--db PATH``
    Path to the SAFIR SQLite results database (required).

``--port PORT``
    TCP port for the Bokeh server (default: ``5006``).

``--host HOST``
    Hostname/IP to bind to (default: ``localhost``).

``--no-browser``
    Do not open a browser tab automatically.

``--cache-dir DIR``
    Directory for the temporary cache database (defaults to the OS temp
    directory).

``--log-level LEVEL``
    Python logging level: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``
    (default: ``INFO``).

Lifecycle
---------
1. Build a temporary cache database from the source DB.
2. Export the cache path as the ``SAFIR_CACHE_DB`` environment variable.
3. Launch ``bokeh serve`` as a subprocess, pointing at :mod:`main`.
4. Block until the subprocess exits (user closes browser / presses Ctrl+C).
5. Delete the temporary cache database.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from .cache_db import CacheDatabase

logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="safir-bokeh",
        description="Launch the SAFIR Bokeh dashboard with a temporary cache database.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--db", required=True, metavar="PATH", help="Source SAFIR SQLite database path")
    p.add_argument("--port", type=int, default=5006, metavar="PORT", help="Bokeh server port")
    p.add_argument("--host", default="localhost", metavar="HOST", help="Bokeh server hostname")
    p.add_argument("--no-browser", action="store_true", help="Do not open a browser tab automatically")
    p.add_argument("--cache-dir", default=None, metavar="DIR", help="Directory for temporary cache DB")
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Logging level",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Returns the exit code of the Bokeh server subprocess.
    """
    args = _parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    source_path = Path(args.db).resolve()
    if not source_path.exists():
        logger.error("Database not found: %s", source_path)
        return 1

    with CacheDatabase(source_path, cache_dir=args.cache_dir) as cache:
        logger.info("Cache database ready: %s", cache.path)

        env = {**os.environ, "SAFIR_CACHE_DB": cache.path}

        cmd = [
            sys.executable, "-m", "bokeh", "serve",
            str(_HERE / "main.py"),
            "--port", str(args.port),
            "--allow-websocket-origin", f"{args.host}:{args.port}",
        ]
        if not args.no_browser:
            cmd.append("--show")

        logger.info("Starting Bokeh server: %s", " ".join(cmd))
        logger.info("Dashboard URL: http://%s:%s/main", args.host, args.port)

        proc = subprocess.Popen(cmd, env=env)

        # Forward SIGINT/SIGTERM so Ctrl-C cleanly terminates the child
        def _forward_signal(signum, frame):  # noqa: ANN001
            logger.info("Received signal %s – stopping Bokeh server …", signum)
            proc.terminate()

        signal.signal(signal.SIGINT, _forward_signal)
        signal.signal(signal.SIGTERM, _forward_signal)

        try:
            return_code = proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            return_code = proc.wait()

        logger.info("Bokeh server exited with code %s.", return_code)

    # CacheDatabase.__exit__ has already deleted the temp file here.
    logger.info("Temporary cache database removed. Goodbye!")
    return return_code


if __name__ == "__main__":
    sys.exit(main())
