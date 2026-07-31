"""Exception hierarchy for the task scheduler.

A single base class lets callers (notably the CLI) catch every expected
failure with one ``except`` clause while still allowing precise handling
where it matters.
"""


class TaskSchedulerError(Exception):
    """Base class for every error raised by this package."""


class ValidationError(TaskSchedulerError):
    """Raised when task data fails validation."""


class TaskNotFoundError(TaskSchedulerError):
    """Raised when an operation references an unknown task id."""


class StorageError(TaskSchedulerError):
    """Raised when tasks cannot be read from or written to disk."""


class UnknownPriorityError(ValidationError):
    """Raised when a priority label cannot be resolved."""
