from datetime import datetime, timedelta

import pytest

from task_scheduler import HighPriorityTask, Priority, RoutineTask, Task, ValidationError
from task_scheduler.exceptions import UnknownPriorityError

from .conftest import NOW


class TestTask:
    def test_defaults(self):
        task = Task("Tidy desk")
        assert task.title == "Tidy desk"
        assert task.description == ""
        assert task.priority is Priority.TO_DO
        assert task.due_date is None
        assert task.completed is False
        assert task.completed_at is None
        assert task.task_id.startswith("task_")

    def test_title_is_stripped_and_required(self):
        assert Task("  Tidy desk  ").title == "Tidy desk"
        with pytest.raises(ValidationError):
            Task("   ")
        with pytest.raises(ValidationError):
            Task(None)

    def test_priority_accepts_labels_and_names(self):
        assert Task("t", priority="urgent").priority is Priority.URGENT
        assert Task("t", priority="High Priority").priority is Priority.HIGH_PRIORITY
        assert Task("t", priority="LOW_PRIORITY").priority is Priority.LOW_PRIORITY
        with pytest.raises(UnknownPriorityError):
            Task("t", priority="nonsense")

    def test_task_id_is_read_only(self):
        task = Task("Tidy desk")
        with pytest.raises(AttributeError):
            task.task_id = "hacked"

    def test_private_state_is_name_mangled(self):
        task = Task("Tidy desk")
        assert not hasattr(task, "__title")
        assert task._Task__title == "Tidy desk"

    def test_due_date_parsing(self):
        assert Task("t", due_date="2026-03-04").due_date == datetime(2026, 3, 4)
        assert Task("t", due_date="2026-03-04 17:30").due_date == datetime(2026, 3, 4, 17, 30)
        assert Task("t", due_date="").due_date is None
        with pytest.raises(ValidationError):
            Task("t", due_date="04/03/2026")

    def test_complete_is_idempotent(self):
        task = Task("Tidy desk")
        assert task.complete(NOW) is True
        assert task.completed is True
        assert task.completed_at == NOW
        assert task.complete(NOW + timedelta(days=1)) is False
        assert task.completed_at == NOW

    def test_reopen(self):
        task = Task("Tidy desk", completed=True, completed_at=NOW)
        assert task.reopen() is True
        assert task.completed is False and task.completed_at is None
        assert task.reopen() is False

    def test_completed_without_timestamp_gets_one(self):
        task = Task("Tidy desk", completed=True, created_at=NOW)
        assert task.completed_at == NOW
        assert task.validate() is True

    def test_is_overdue(self):
        assert Task("t", due_date="2026-02-01").is_overdue(NOW) is True
        assert Task("t", due_date="2026-04-01").is_overdue(NOW) is False
        assert Task("t").is_overdue(NOW) is False
        done = Task("t", due_date="2026-02-01")
        done.complete(NOW)
        assert done.is_overdue(NOW) is False

    def test_status_label(self):
        assert Task("t").status_label(NOW) == "Pending"
        assert Task("t", due_date="2026-01-01").status_label(NOW) == "Overdue"
        done = Task("t")
        done.complete(NOW)
        assert done.status_label(NOW) == "Completed"

    def test_matches_is_case_insensitive(self):
        task = Task("Buy Milk", "from the Corner shop")
        assert task.matches("milk") and task.matches("CORNER")
        assert not task.matches("bread")
        assert not task.matches("")
        assert not task.matches(None)

    def test_equality_is_by_id(self):
        a = Task("a")
        b = Task("b")
        assert a != b
        assert a == Task("a", task_id=a.task_id)
        assert len({a, Task("z", task_id=a.task_id)}) == 1

    def test_round_trip(self):
        task = Task("Tidy desk", "under the stairs", Priority.WORK, due_date="2026-03-04")
        restored = Task.from_dict(task.to_dict())
        assert restored.to_dict() == task.to_dict()
        assert restored.task_id == task.task_id

    def test_display_includes_key_fields(self):
        task = Task("Tidy desk", "under the stairs", Priority.WORK, due_date="2026-02-01")
        text = task.display(NOW)
        assert "Tidy desk" in text
        assert "under the stairs" in text
        assert "Work" in text
        assert "[OVERDUE]" in text


class TestHighPriorityTask:
    def test_deadline_aliases_due_date(self):
        task = HighPriorityTask("Ship", priority=Priority.URGENT, due_date="2026-03-04")
        assert task.deadline == datetime(2026, 3, 4)
        task.deadline = "2026-03-05"
        assert task.due_date == datetime(2026, 3, 5)

    def test_escalation(self):
        task = HighPriorityTask("Ship", priority=Priority.HIGH_PRIORITY, due_date="2026-02-01")
        assert task.escalation_level == 0
        assert task.escalate() == 1
        assert task.escalate() == 2

    def test_auto_escalate_only_once_and_only_when_overdue(self):
        overdue = HighPriorityTask("Ship", priority=Priority.URGENT, due_date="2026-02-01")
        assert overdue.auto_escalate(NOW) is True
        assert overdue.auto_escalate(NOW) is False
        assert overdue.escalation_level == 1

        future = HighPriorityTask("Ship", priority=Priority.URGENT, due_date="2026-04-01")
        assert future.auto_escalate(NOW) is False
        assert future.escalation_level == 0

    def test_time_remaining(self):
        task = HighPriorityTask("Ship", priority=Priority.URGENT, due_date="2026-03-04")
        assert task.time_remaining(NOW) == "in 2 days"
        task.deadline = "2026-02-27"
        assert task.time_remaining(NOW) == "2 days ago"
        assert HighPriorityTask("Ship", priority=Priority.URGENT).time_remaining(NOW) is None

    def test_round_trip_preserves_escalation(self):
        task = HighPriorityTask("Ship", priority=Priority.URGENT, due_date="2026-02-01")
        task.escalate()
        restored = HighPriorityTask.from_dict(task.to_dict())
        assert restored.escalation_level == 1
        assert restored.deadline == datetime(2026, 2, 1)

    def test_negative_escalation_fails_validation(self):
        task = HighPriorityTask("Ship", priority=Priority.URGENT, escalation_level=-1)
        with pytest.raises(ValidationError):
            task.validate()


class TestRoutineTask:
    def test_default_due_date_follows_frequency(self):
        task = RoutineTask("Standup", priority=Priority.ROUTINE, frequency="daily",
                           created_at=NOW)
        assert task.due_date == NOW + timedelta(days=1)

    def test_invalid_frequency_rejected(self):
        with pytest.raises(ValidationError):
            RoutineTask("Standup", priority=Priority.ROUTINE, frequency="hourly")
        with pytest.raises(ValidationError):
            RoutineTask("Standup", priority=Priority.ROUTINE, frequency=None)

    def test_completion_reschedules_instead_of_finishing(self):
        task = RoutineTask("Water plants", priority=Priority.ROUTINE, frequency="weekly",
                           due_date=NOW)
        assert task.complete(NOW) is True
        assert task.completed is False
        assert task.occurrences == 1
        assert task.due_date == NOW + timedelta(days=7)

    def test_completion_skips_missed_occurrences(self):
        task = RoutineTask("Water plants", priority=Priority.ROUTINE, frequency="daily",
                           due_date=NOW - timedelta(days=10))
        task.complete(NOW)
        assert task.due_date > NOW
        assert task.due_date == NOW + timedelta(days=1)

    def test_next_due_is_one_interval_ahead(self):
        task = RoutineTask("Pay rent", priority=Priority.ROUTINE, frequency="monthly",
                           due_date=NOW)
        assert task.next_due == NOW + timedelta(days=30)

    def test_round_trip_preserves_frequency_and_count(self):
        task = RoutineTask("Standup", priority=Priority.ROUTINE, frequency="daily",
                           due_date=NOW)
        task.complete(NOW)
        restored = RoutineTask.from_dict(task.to_dict())
        assert restored.frequency == "daily"
        assert restored.occurrences == 1
        assert restored.due_date == task.due_date


class TestPolymorphism:
    def test_every_task_type_satisfies_the_interface(self):
        tasks = [
            Task("Plain"),
            HighPriorityTask("Urgent one", priority=Priority.URGENT, due_date="2026-03-04"),
            RoutineTask("Routine one", priority=Priority.ROUTINE, frequency="weekly"),
        ]
        for task in tasks:
            assert task.validate() is True
            assert isinstance(task.display(NOW), str)
            assert task.to_dict()["task_id"] == task.task_id
            assert task.to_dict()["task_type"] == type(task).task_type

    def test_interface_cannot_be_instantiated_incompletely(self):
        from task_scheduler.models import TaskInterface

        class Broken(TaskInterface):
            pass

        with pytest.raises(TypeError):
            Broken()
