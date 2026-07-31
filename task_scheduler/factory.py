"""Factory that maps a priority (or a stored record) to the right task class."""

from .config import DEADLINE_PRIORITIES, LEGACY_PRIORITY_MAP, Priority
from .exceptions import UnknownPriorityError, ValidationError
from .models import HighPriorityTask, RoutineTask, Task

#: Registry of ``task_type`` -> class, used when rebuilding stored tasks.
TASK_TYPES = {
    Task.task_type: Task,
    HighPriorityTask.task_type: HighPriorityTask,
    RoutineTask.task_type: RoutineTask,
}


class TaskFactory:
    """Creates the appropriate task object for a given priority."""

    @staticmethod
    def class_for_priority(priority):
        """Return the task class that implements ``priority``."""
        resolved = Priority.from_value(priority)
        if resolved is None:
            raise UnknownPriorityError("Unknown priority: {!r}".format(priority))
        if resolved in DEADLINE_PRIORITIES:
            return HighPriorityTask
        if resolved is Priority.ROUTINE:
            return RoutineTask
        return Task

    @staticmethod
    def create(title, description="", priority=Priority.TO_DO, **kwargs):
        """Build a task, dropping options the chosen class does not accept.

        Passing ``frequency`` for a non-routine priority (or ``escalation_level``
        for a plain task) is silently ignored rather than raising, so the CLI can
        collect optional fields without branching first.
        """
        resolved = Priority.from_value(priority)
        if resolved is None:
            raise UnknownPriorityError("Unknown priority: {!r}".format(priority))
        cls = TaskFactory.class_for_priority(resolved)

        if cls is not RoutineTask:
            kwargs.pop("frequency", None)
            kwargs.pop("occurrences", None)
        if cls is not HighPriorityTask:
            kwargs.pop("escalation_level", None)
        if "deadline" in kwargs:
            deadline = kwargs.pop("deadline")
            kwargs.setdefault("due_date", deadline)

        task = cls(title=title, description=description, priority=resolved, **kwargs)
        task.validate()
        return task

    @staticmethod
    def from_dict(data):
        """Rebuild a task from its serialised form.

        Handles both the current format and the legacy ``main.py`` format,
        which stored an integer priority and a ``due_date`` only.
        """
        if not isinstance(data, dict):
            raise ValidationError("Task records must be JSON objects.")

        data = TaskFactory._migrate(data)
        task_type = data.get("task_type")
        cls = TASK_TYPES.get(task_type)
        if cls is None:
            cls = TaskFactory.class_for_priority(data.get("priority", Priority.TO_DO))
        task = cls.from_dict(data)
        task.validate()
        return task

    @staticmethod
    def _migrate(data):
        """Upgrade a legacy record in place-safe fashion (returns a new dict)."""
        record = dict(data)
        priority = record.get("priority")

        if isinstance(priority, bool) or not isinstance(priority, (int, str)):
            priority = None
        if isinstance(priority, int):
            mapped = LEGACY_PRIORITY_MAP.get(priority)
            if mapped is None:
                mapped = Priority.TO_DO
            record["priority"] = mapped.value
        elif priority is None:
            record["priority"] = Priority.TO_DO.value

        if "task_type" not in record:
            resolved = Priority.from_value(record["priority"]) or Priority.TO_DO
            record["priority"] = resolved.value
            record["task_type"] = TaskFactory.class_for_priority(resolved).task_type

        return record
