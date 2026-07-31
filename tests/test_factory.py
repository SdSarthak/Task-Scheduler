import pytest

from task_scheduler import (
    HighPriorityTask,
    Priority,
    RoutineTask,
    Task,
    TaskFactory,
    UnknownPriorityError,
    ValidationError,
)


@pytest.mark.parametrize(
    "priority, expected",
    [
        (Priority.URGENT, HighPriorityTask),
        (Priority.HIGH_PRIORITY, HighPriorityTask),
        (Priority.ROUTINE, RoutineTask),
        (Priority.TO_DO, Task),
        (Priority.LOW_PRIORITY, Task),
        (Priority.PREFER_TO_DO, Task),
        (Priority.PERSONAL, Task),
        (Priority.WORK, Task),
    ],
)
def test_class_for_priority(priority, expected):
    assert TaskFactory.class_for_priority(priority) is expected
    assert type(TaskFactory.create("t", priority=priority)) is expected


def test_create_rejects_unknown_priority():
    with pytest.raises(UnknownPriorityError):
        TaskFactory.create("t", priority="somewhere else")


def test_create_drops_options_the_class_cannot_use():
    plain = TaskFactory.create("t", priority=Priority.WORK, frequency="daily",
                               escalation_level=3)
    assert type(plain) is Task
    assert not hasattr(plain, "frequency")

    routine = TaskFactory.create("t", priority=Priority.ROUTINE, frequency="daily",
                                 escalation_level=3)
    assert routine.frequency == "daily"


def test_deadline_keyword_maps_to_due_date():
    task = TaskFactory.create("t", priority=Priority.URGENT, deadline="2026-03-04")
    assert task.deadline.strftime("%Y-%m-%d") == "2026-03-04"


def test_from_dict_dispatches_on_task_type():
    original = TaskFactory.create("Ship", priority=Priority.URGENT, due_date="2026-03-04")
    original.escalate()
    restored = TaskFactory.from_dict(original.to_dict())
    assert type(restored) is HighPriorityTask
    assert restored.escalation_level == 1
    assert restored.to_dict() == original.to_dict()


def test_from_dict_rejects_non_objects():
    with pytest.raises(ValidationError):
        TaskFactory.from_dict(["not", "a", "dict"])
    with pytest.raises(ValidationError):
        TaskFactory.from_dict({"title": "", "priority": "Work"})


class TestLegacyMigration:
    """Records written by the original flat main.py must still load."""

    def legacy(self, priority):
        return {
            "title": "Old task",
            "description": "written by the previous version",
            "priority": priority,
            "due_date": "2026-03-04",
            "completed": False,
        }

    @pytest.mark.parametrize(
        "legacy_priority, expected",
        [
            (1, Priority.URGENT),
            (2, Priority.HIGH_PRIORITY),
            (3, Priority.TO_DO),
            (4, Priority.PREFER_TO_DO),
            (5, Priority.LOW_PRIORITY),
        ],
    )
    def test_integer_priorities_map_to_categories(self, legacy_priority, expected):
        task = TaskFactory.from_dict(self.legacy(legacy_priority))
        assert task.priority is expected
        assert task.due_date.strftime("%Y-%m-%d") == "2026-03-04"
        assert task.title == "Old task"
        assert task.task_id.startswith("task_")

    def test_out_of_range_integer_falls_back_to_to_do(self):
        assert TaskFactory.from_dict(self.legacy(99)).priority is Priority.TO_DO

    def test_missing_priority_falls_back_to_to_do(self):
        record = self.legacy(1)
        del record["priority"]
        assert TaskFactory.from_dict(record).priority is Priority.TO_DO

    def test_completed_legacy_task_gains_a_timestamp(self):
        record = self.legacy(3)
        record["completed"] = True
        task = TaskFactory.from_dict(record)
        assert task.completed is True
        assert task.completed_at is not None
