"""Business logic: the task collection and every operation performed on it.

``TaskManager`` HAS-A :class:`~task_scheduler.storage.TaskStorage` (composition)
and HAS-A list of tasks (aggregation).
"""

from datetime import datetime, timedelta

from .config import Priority, get_upcoming_days, priority_rank
from .exceptions import TaskNotFoundError, UnknownPriorityError, ValidationError
from .factory import TaskFactory
from .models import HighPriorityTask, RoutineTask
from .storage import TaskStorage


class TaskManager:
    """Orchestrates task creation, mutation, querying and persistence."""

    def __init__(self, storage=None, autosave=True):
        self.storage = storage if storage is not None else TaskStorage()
        self.autosave = autosave
        self._tasks = []
        self.load_warnings = []
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def load(self):
        """(Re)load tasks from storage, capturing any records it rejected."""
        self._tasks = self.storage.load()
        self.load_warnings = list(self.storage.skipped)
        return self._tasks

    def save(self):
        """Write the current tasks to storage."""
        return self.storage.save(self._tasks)

    def _touch(self):
        if self.autosave:
            self.save()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def tasks(self):
        """A copy of the task list; mutate through the manager instead."""
        return list(self._tasks)

    def __len__(self):
        return len(self._tasks)

    def __iter__(self):
        return iter(self._tasks)

    def get(self, task_id):
        """Return the task with ``task_id``.

        Raises:
            TaskNotFoundError: when no task matches.
        """
        for task in self._tasks:
            if task.task_id == task_id:
                return task
        raise TaskNotFoundError("No task with id {!r}.".format(task_id))

    def by_index(self, position):
        """Return the task shown at 1-based ``position`` in listings."""
        try:
            index = int(position)
        except (TypeError, ValueError):
            raise TaskNotFoundError("{!r} is not a task number.".format(position)) from None
        if not 1 <= index <= len(self._tasks):
            raise TaskNotFoundError("Task number {} is out of range.".format(index))
        return self._tasks[index - 1]

    def resolve(self, reference):
        """Look a task up by id first, then by its 1-based listing position."""
        text = str(reference).strip()
        for task in self._tasks:
            if task.task_id == text:
                return task
        return self.by_index(text)

    def filter(self, priority=None, completed=None, overdue=None, now=None):
        """Return tasks matching every supplied criterion."""
        now = now or datetime.now()
        resolved = None
        if priority is not None:
            resolved = Priority.from_value(priority)
            if resolved is None:
                raise UnknownPriorityError("Unknown priority: {!r}".format(priority))

        results = []
        for task in self._tasks:
            if resolved is not None and task.priority is not resolved:
                continue
            if completed is not None and task.completed is not bool(completed):
                continue
            if overdue is not None and task.is_overdue(now) is not bool(overdue):
                continue
            results.append(task)
        return results

    def pending(self, now=None):
        return self.filter(completed=False, now=now)

    def completed(self, now=None):
        return self.filter(completed=True, now=now)

    def overdue(self, now=None):
        return self.filter(overdue=True, now=now)

    def search(self, term):
        """Tasks whose title or description contains ``term``."""
        return [task for task in self._tasks if task.matches(term)]

    def sorted_tasks(self, by="priority", now=None):
        """Return tasks ordered by ``priority``, ``due_date``, ``title`` or ``created``.

        Pending tasks always sort ahead of completed ones. Tasks without a due
        date sort last within the ``due_date`` ordering.
        """
        now = now or datetime.now()
        far_future = now + timedelta(days=365 * 100)

        keys = {
            "priority": lambda t: (t.completed, priority_rank(t.priority), t.title.lower()),
            "due_date": lambda t: (t.completed, t.due_date or far_future, t.title.lower()),
            "title": lambda t: (t.completed, t.title.lower()),
            "created": lambda t: (t.completed, t.created_at),
        }
        key = keys.get(by)
        if key is None:
            raise ValidationError(
                "Cannot sort by {!r}. Choose one of: {}.".format(by, ", ".join(sorted(keys)))
            )
        return sorted(self._tasks, key=key)

    def sort(self, by="priority"):
        """Sort the stored task order in place and persist it."""
        self._tasks = self.sorted_tasks(by)
        self._touch()
        return self._tasks

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    def add_task(self, title, description="", priority=Priority.TO_DO, **kwargs):
        """Create, store and return a new task."""
        task = TaskFactory.create(title, description=description, priority=priority, **kwargs)
        self._tasks.append(task)
        self._touch()
        return task

    def remove_task(self, reference):
        """Delete a task and return the removed object."""
        task = self.resolve(reference)
        self._tasks.remove(task)
        self._touch()
        return task

    def complete_task(self, reference, when=None):
        """Mark a task complete. Returns ``(task, changed)``.

        Routine tasks reschedule instead of staying completed, so ``changed``
        is always ``True`` for them.
        """
        task = self.resolve(reference)
        changed = task.complete(when)
        if changed:
            self._touch()
        return task, changed

    def reopen_task(self, reference):
        """Undo a completion. Returns ``(task, changed)``."""
        task = self.resolve(reference)
        changed = task.reopen()
        if changed:
            self._touch()
        return task, changed

    def transfer_task(self, reference, new_priority):
        """Move a task to another priority category.

        The task class is chosen by priority, so a transfer may need to
        rebuild the object (for example To Do -> Routine). Identity, timestamps
        and completion state are carried over; the returned task keeps the same
        ``task_id``.
        """
        task = self.resolve(reference)
        resolved = Priority.from_value(new_priority)
        if resolved is None:
            raise UnknownPriorityError("Unknown priority: {!r}".format(new_priority))
        if resolved is task.priority:
            return task

        target_cls = TaskFactory.class_for_priority(resolved)
        if type(task) is target_cls:
            task.priority = resolved
            self._touch()
            return task

        data = task.to_dict()
        data["priority"] = resolved.value
        data["task_type"] = target_cls.task_type
        if target_cls is RoutineTask:
            data.setdefault("frequency", "weekly")
        if target_cls is not HighPriorityTask:
            data.pop("escalation_level", None)
        replacement = TaskFactory.from_dict(data)
        self._tasks[self._tasks.index(task)] = replacement
        self._touch()
        return replacement

    def escalate_overdue(self, now=None):
        """Escalate every overdue high-priority task once. Returns those tasks."""
        escalated = [
            task
            for task in self._tasks
            if isinstance(task, HighPriorityTask) and task.auto_escalate(now)
        ]
        if escalated:
            self._touch()
        return escalated

    def clear_completed(self):
        """Remove every completed task and return them."""
        removed = [task for task in self._tasks if task.completed]
        if removed:
            self._tasks = [task for task in self._tasks if not task.completed]
            self._touch()
        return removed

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def upcoming(self, days=None, now=None):
        """Pending tasks due within ``days`` (default from configuration)."""
        now = now or datetime.now()
        window = now + timedelta(days=get_upcoming_days() if days is None else int(days))
        return sorted(
            (
                task
                for task in self._tasks
                if not task.completed and task.due_date is not None and now <= task.due_date <= window
            ),
            key=lambda t: t.due_date,
        )

    def statistics(self, now=None):
        """Aggregate counts used by the statistics view."""
        now = now or datetime.now()
        total = len(self._tasks)
        completed = len(self.completed(now))
        pending = total - completed
        by_priority = {priority.value: 0 for priority in Priority}
        for task in self._tasks:
            by_priority[task.priority.value] += 1
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total else 0.0,
            "overdue": len(self.overdue(now)),
            "upcoming": len(self.upcoming(now=now)),
            "by_priority": by_priority,
        }
