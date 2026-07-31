"""Task Scheduler - an OOP command-line task manager.

Public entry points::

    from task_scheduler import TaskManager, TaskStorage, Priority

    manager = TaskManager(TaskStorage("tasks.json"))
    manager.add_task("Write docs", "Cover setup and usage", Priority.WORK)
"""

from .config import Priority
from .exceptions import (
    StorageError,
    TaskNotFoundError,
    TaskSchedulerError,
    UnknownPriorityError,
    ValidationError,
)
from .factory import TaskFactory
from .manager import TaskManager
from .models import HighPriorityTask, RoutineTask, Task, TaskInterface
from .storage import TaskStorage

__version__ = "1.0.0"

__all__ = [
    "HighPriorityTask",
    "Priority",
    "RoutineTask",
    "StorageError",
    "Task",
    "TaskFactory",
    "TaskInterface",
    "TaskManager",
    "TaskNotFoundError",
    "TaskSchedulerError",
    "TaskStorage",
    "UnknownPriorityError",
    "ValidationError",
    "__version__",
]
