"""Configuration, formats and the priority vocabulary.

Every value that used to be hardcoded in ``main.py`` lives here and can be
overridden through environment variables (see ``.env.example``).
"""

import os
from enum import Enum

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

#: Formats accepted when parsing a user supplied due date, in priority order.
INPUT_DATE_FORMATS = (DATETIME_FORMAT, "%Y-%m-%d %H:%M", DATE_FORMAT)

DEFAULT_DATA_FILE = "tasks.json"
DEFAULT_UPCOMING_DAYS = 3


class Priority(Enum):
    """The eight task categories the scheduler supports."""

    HIGH_PRIORITY = "High Priority"
    LOW_PRIORITY = "Low Priority"
    TO_DO = "To Do"
    PREFER_TO_DO = "Prefer To Do"
    URGENT = "Urgent"
    ROUTINE = "Routine"
    PERSONAL = "Personal"
    WORK = "Work"

    def __str__(self):
        return self.value

    @classmethod
    def from_value(cls, value):
        """Resolve a ``Priority`` from a member, label, or member name.

        Matching is case and separator insensitive so ``"high priority"``,
        ``"High Priority"`` and ``"HIGH_PRIORITY"`` all resolve.
        Returns ``None`` when nothing matches; callers decide whether that
        is an error.
        """
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            return None
        needle = value.strip().lower().replace("_", " ")
        for member in cls:
            if needle in (member.value.lower(), member.name.lower().replace("_", " ")):
                return member
        return None


#: Ordering used whenever tasks are sorted by importance (most urgent first).
PRIORITY_ORDER = (
    Priority.URGENT,
    Priority.HIGH_PRIORITY,
    Priority.WORK,
    Priority.TO_DO,
    Priority.ROUTINE,
    Priority.PERSONAL,
    Priority.PREFER_TO_DO,
    Priority.LOW_PRIORITY,
)

#: Priorities whose tasks carry deadline management and escalation.
DEADLINE_PRIORITIES = (Priority.URGENT, Priority.HIGH_PRIORITY)

#: Recurrence intervals supported by routine tasks, in days.
FREQUENCY_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

#: Legacy ``main.py`` stored priorities as integers 1 (most urgent) to 5.
LEGACY_PRIORITY_MAP = {
    1: Priority.URGENT,
    2: Priority.HIGH_PRIORITY,
    3: Priority.TO_DO,
    4: Priority.PREFER_TO_DO,
    5: Priority.LOW_PRIORITY,
}


def priority_rank(priority):
    """Return the sort rank of ``priority`` (lower means more important)."""
    try:
        return PRIORITY_ORDER.index(priority)
    except ValueError:
        return len(PRIORITY_ORDER)


def _env_flag(name, default):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("", "0", "false", "no", "off")


def get_data_file():
    """Path of the JSON file tasks are persisted to."""
    return os.environ.get("TASK_SCHEDULER_DATA_FILE") or DEFAULT_DATA_FILE


def get_upcoming_days():
    """How many days ahead counts as an upcoming deadline."""
    raw = os.environ.get("TASK_SCHEDULER_UPCOMING_DAYS")
    if raw is None:
        return DEFAULT_UPCOMING_DAYS
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_UPCOMING_DAYS
    return days if days >= 0 else DEFAULT_UPCOMING_DAYS


def backup_corrupt_files():
    """Whether an unreadable tasks file is preserved before being replaced."""
    return _env_flag("TASK_SCHEDULER_BACKUP_CORRUPT", True)
