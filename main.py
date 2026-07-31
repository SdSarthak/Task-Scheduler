"""Launcher for the Task Scheduler CLI.

    python main.py [path/to/tasks.json]

All behaviour lives in the ``task_scheduler`` package; this file only wires
the package up so it can be run directly from a checkout.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from task_scheduler.cli import main  # noqa: E402  (path set up above)

if __name__ == "__main__":
    sys.exit(main())
