"""Shared fixtures. Every test runs against a temporary file, never real data."""

import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from task_scheduler import Priority, TaskManager, TaskStorage  # noqa: E402

#: Fixed "now" so nothing in the suite depends on the wall clock.
NOW = datetime(2026, 3, 1, 9, 0, 0)


@pytest.fixture
def data_file(tmp_path):
    return tmp_path / "tasks.json"


@pytest.fixture
def storage(data_file):
    return TaskStorage(str(data_file))


@pytest.fixture
def manager(storage):
    return TaskManager(storage)


@pytest.fixture
def populated(manager):
    """Three tasks covering all three task classes."""
    manager.add_task("Ship release", "cut v1.0", Priority.URGENT, due_date="2026-02-01")
    manager.add_task("Read book", "chapter 4", Priority.PERSONAL)
    manager.add_task("Water plants", "", Priority.ROUTINE, frequency="weekly",
                     due_date="2026-03-03")
    return manager


@pytest.fixture
def clean_env(monkeypatch):
    for name in (
        "TASK_SCHEDULER_DATA_FILE",
        "TASK_SCHEDULER_UPCOMING_DAYS",
        "TASK_SCHEDULER_BACKUP_CORRUPT",
    ):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch
