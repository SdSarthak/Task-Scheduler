"""Task models: the abstract contract, the base task and its specialisations.

Hierarchy::

    TaskInterface (ABC)
        |
        Task
        |-- HighPriorityTask
        |-- RoutineTask
"""

import itertools
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from .config import DATETIME_FORMAT, FREQUENCY_DAYS, Priority
from .dates import coerce_datetime, format_datetime, humanize_delta
from .exceptions import UnknownPriorityError, ValidationError

_id_counter = itertools.count(1)


def generate_task_id():
    """Return a unique, sortable task identifier."""
    return "task_{}_{}".format(int(time.time() * 1000), next(_id_counter))


class TaskInterface(ABC):
    """Contract every task type must fulfil."""

    @abstractmethod
    def display(self):
        """Return a human readable, multi-line rendering of the task."""

    @abstractmethod
    def to_dict(self):
        """Return a JSON-serialisable representation of the task."""

    @abstractmethod
    def validate(self):
        """Raise :class:`ValidationError` if the task is inconsistent."""


class Task(TaskInterface):
    """A general task.

    Attributes are kept private and exposed through properties so that every
    mutation runs through validation.
    """

    task_type = "task"

    def __init__(
        self,
        title,
        description="",
        priority=Priority.TO_DO,
        due_date=None,
        completed=False,
        created_at=None,
        completed_at=None,
        task_id=None,
    ):
        self.__task_id = task_id or generate_task_id()
        self.__created_at = coerce_datetime(created_at, "creation date") or datetime.now()
        self.__completed = bool(completed)
        self.__completed_at = coerce_datetime(completed_at, "completion date")
        self.title = title
        self.description = description
        self.priority = priority
        self.due_date = due_date
        if self.__completed and self.__completed_at is None:
            self.__completed_at = self.__created_at

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def task_id(self):
        """Immutable identifier assigned at creation time."""
        return self.__task_id

    @property
    def created_at(self):
        return self.__created_at

    @property
    def completed_at(self):
        return self.__completed_at

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("Task title cannot be empty.")
        self.__title = value.strip()

    @property
    def description(self):
        return self.__description

    @description.setter
    def description(self, value):
        self.__description = (value or "").strip()

    @property
    def priority(self):
        return self.__priority

    @priority.setter
    def priority(self, value):
        resolved = Priority.from_value(value)
        if resolved is None:
            raise UnknownPriorityError("Unknown priority: {!r}".format(value))
        self.__priority = resolved

    @property
    def due_date(self):
        """Optional deadline for the task, or ``None``."""
        return self.__due_date

    @due_date.setter
    def due_date(self, value):
        self.__due_date = coerce_datetime(value, "due date")

    @property
    def completed(self):
        return self.__completed

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def complete(self, when=None):
        """Mark the task done. Returns ``True`` if this call changed it."""
        if self.__completed:
            return False
        self.__completed = True
        self.__completed_at = coerce_datetime(when, "completion date") or datetime.now()
        return True

    def reopen(self):
        """Undo completion. Returns ``True`` if this call changed the task."""
        if not self.__completed:
            return False
        self.__completed = False
        self.__completed_at = None
        return True

    def is_overdue(self, now=None):
        """True when the task has a past deadline and is not yet complete."""
        if self.__completed or self.__due_date is None:
            return False
        return self.__due_date < (now or datetime.now())

    def matches(self, term):
        """Case-insensitive substring search over title and description."""
        needle = (term or "").strip().lower()
        if not needle:
            return False
        return needle in self.__title.lower() or needle in self.__description.lower()

    def status_label(self, now=None):
        if self.__completed:
            return "Completed"
        return "Overdue" if self.is_overdue(now) else "Pending"

    # ------------------------------------------------------------------
    # TaskInterface
    # ------------------------------------------------------------------
    def display(self, now=None):
        now = now or datetime.now()
        marker = "x" if self.__completed else "o"
        lines = [
            "[{}] {}".format(self.__task_id, self.__title),
            "Priority: {}".format(self.__priority),
            "Created: {}".format(format_datetime(self.__created_at)),
            "Status: {} {}".format(marker, self.status_label(now)),
        ]
        if self.__description:
            lines.insert(1, "Description: {}".format(self.__description))
        if self.__due_date is not None:
            suffix = " [OVERDUE]" if self.is_overdue(now) else ""
            lines.append("Due: {}{}".format(format_datetime(self.__due_date), suffix))
        if self.__completed_at is not None:
            lines.append("Completed: {}".format(format_datetime(self.__completed_at)))
        return "\n".join(lines)

    def to_dict(self):
        return {
            "task_id": self.__task_id,
            "task_type": self.task_type,
            "title": self.__title,
            "description": self.__description,
            "priority": self.__priority.value,
            "due_date": format_datetime(self.__due_date),
            "completed": self.__completed,
            "created_at": format_datetime(self.__created_at),
            "completed_at": format_datetime(self.__completed_at),
        }

    def validate(self):
        if not self.__title:
            raise ValidationError("Task title cannot be empty.")
        if not isinstance(self.__priority, Priority):
            raise ValidationError("Task priority must be a Priority member.")
        if self.__completed and self.__completed_at is None:
            raise ValidationError("A completed task must record a completion time.")
        return True

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    @classmethod
    def base_kwargs(cls, data):
        """Extract the constructor arguments shared by every task type."""
        return {
            "task_id": data.get("task_id"),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "priority": data.get("priority", Priority.TO_DO),
            "due_date": data.get("due_date"),
            "completed": data.get("completed", False),
            "created_at": data.get("created_at"),
            "completed_at": data.get("completed_at"),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**cls.base_kwargs(data))

    def __str__(self):
        return self.display()

    def __repr__(self):
        return "<{} {} {!r}>".format(type(self).__name__, self.__task_id, self.__title)

    def __eq__(self, other):
        if not isinstance(other, Task):
            return NotImplemented
        return self.task_id == other.task_id

    def __hash__(self):
        return hash(self.task_id)


class HighPriorityTask(Task):
    """A task that carries a deadline and can be escalated."""

    task_type = "high_priority"

    def __init__(self, *args, **kwargs):
        self.__escalation_level = int(kwargs.pop("escalation_level", 0) or 0)
        super().__init__(*args, **kwargs)

    @property
    def deadline(self):
        """Alias for :attr:`Task.due_date` using the high-priority wording."""
        return self.due_date

    @deadline.setter
    def deadline(self, value):
        self.due_date = value

    @property
    def escalation_level(self):
        return self.__escalation_level

    def escalate(self):
        """Raise the escalation level by one and return the new level."""
        self.__escalation_level += 1
        return self.__escalation_level

    def auto_escalate(self, now=None):
        """Escalate once if the deadline has passed. Returns True if escalated."""
        if self.is_overdue(now) and self.__escalation_level == 0:
            self.escalate()
            return True
        return False

    def time_remaining(self, now=None):
        """Readable time to the deadline, or ``None`` when there is no deadline."""
        if self.deadline is None:
            return None
        return humanize_delta(self.deadline, now)

    def display(self, now=None):
        now = now or datetime.now()
        text = super().display(now)
        if self.deadline is not None and not self.completed:
            text += "\nDeadline: {} ({})".format(
                self.deadline.strftime(DATETIME_FORMAT), self.time_remaining(now)
            )
        if self.__escalation_level:
            text += "\nEscalation: level {}".format(self.__escalation_level)
        return text

    def to_dict(self):
        data = super().to_dict()
        data["escalation_level"] = self.__escalation_level
        return data

    def validate(self):
        super().validate()
        if self.__escalation_level < 0:
            raise ValidationError("Escalation level cannot be negative.")
        return True

    @classmethod
    def from_dict(cls, data):
        kwargs = cls.base_kwargs(data)
        kwargs["escalation_level"] = data.get("escalation_level", 0)
        return cls(**kwargs)


class RoutineTask(Task):
    """A recurring task that reschedules itself when completed."""

    task_type = "routine"

    def __init__(self, *args, **kwargs):
        frequency = kwargs.pop("frequency", "weekly")
        self.__occurrences = int(kwargs.pop("occurrences", 0) or 0)
        self.__frequency = self._normalise_frequency(frequency)
        super().__init__(*args, **kwargs)
        if self.due_date is None:
            self.due_date = self.created_at + self.interval

    @staticmethod
    def _normalise_frequency(value):
        text = (value or "").strip().lower() if isinstance(value, str) else ""
        if text not in FREQUENCY_DAYS:
            raise ValidationError(
                "Frequency must be one of: {}.".format(", ".join(sorted(FREQUENCY_DAYS)))
            )
        return text

    @property
    def frequency(self):
        return self.__frequency

    @frequency.setter
    def frequency(self, value):
        self.__frequency = self._normalise_frequency(value)

    @property
    def occurrences(self):
        """How many times this routine has been completed."""
        return self.__occurrences

    @property
    def interval(self):
        return timedelta(days=FREQUENCY_DAYS[self.__frequency])

    @property
    def next_due(self):
        """The due date this task will move to after the current occurrence."""
        base = self.due_date or self.created_at
        return base + self.interval

    def complete(self, when=None):
        """Record the occurrence and roll the due date forward.

        A routine task never stays completed: completing it counts the
        occurrence and schedules the next one.
        """
        moment = coerce_datetime(when, "completion date") or datetime.now()
        self.__occurrences += 1
        upcoming = self.next_due
        while upcoming <= moment:
            upcoming += self.interval
        self.due_date = upcoming
        return True

    def display(self, now=None):
        now = now or datetime.now()
        text = super().display(now)
        text += "\nRepeats: {}".format(self.__frequency)
        if self.__occurrences:
            text += "\nCompleted occurrences: {}".format(self.__occurrences)
        return text

    def to_dict(self):
        data = super().to_dict()
        data["frequency"] = self.__frequency
        data["occurrences"] = self.__occurrences
        return data

    def validate(self):
        super().validate()
        if self.__frequency not in FREQUENCY_DAYS:
            raise ValidationError("Unsupported routine frequency: {}".format(self.__frequency))
        if self.due_date is None:
            raise ValidationError("A routine task must have a next due date.")
        return True

    @classmethod
    def from_dict(cls, data):
        kwargs = cls.base_kwargs(data)
        kwargs["frequency"] = data.get("frequency", "weekly")
        kwargs["occurrences"] = data.get("occurrences", 0)
        return cls(**kwargs)


__all__ = [
    "TaskInterface",
    "Task",
    "HighPriorityTask",
    "RoutineTask",
    "generate_task_id",
]
