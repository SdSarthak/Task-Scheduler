import json
from datetime import datetime, timedelta

import pytest

from task_scheduler import (
    HighPriorityTask,
    Priority,
    RoutineTask,
    Task,
    TaskManager,
    TaskNotFoundError,
    TaskStorage,
    UnknownPriorityError,
    ValidationError,
)

from .conftest import NOW


class TestAddAndPersist:
    def test_add_task_persists_immediately(self, manager, data_file):
        manager.add_task("Ship release", "cut v1.0", Priority.URGENT, due_date="2026-03-04")
        payload = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(payload) == 1
        assert payload[0]["title"] == "Ship release"

    def test_add_task_picks_the_class_from_priority(self, manager):
        assert isinstance(manager.add_task("a", priority=Priority.URGENT), HighPriorityTask)
        assert isinstance(
            manager.add_task("b", priority=Priority.ROUTINE, frequency="daily"), RoutineTask
        )
        plain = manager.add_task("c", priority=Priority.WORK)
        assert type(plain) is Task

    def test_autosave_can_be_disabled(self, storage, data_file):
        manager = TaskManager(storage, autosave=False)
        manager.add_task("Ship release", priority=Priority.WORK)
        assert not data_file.exists()
        manager.save()
        assert data_file.exists()

    def test_state_survives_a_restart(self, populated, storage):
        reloaded = TaskManager(TaskStorage(storage.path))
        assert len(reloaded) == 3
        assert [type(t).__name__ for t in reloaded] == [
            "HighPriorityTask",
            "Task",
            "RoutineTask",
        ]

    def test_invalid_task_is_rejected_before_storage(self, manager, data_file):
        with pytest.raises(ValidationError):
            manager.add_task("", priority=Priority.WORK)
        assert len(manager) == 0
        assert not data_file.exists()

    def test_load_warnings_surface_skipped_records(self, data_file):
        data_file.write_text(json.dumps([{"title": ""}]), encoding="utf-8")
        manager = TaskManager(TaskStorage(str(data_file)))
        assert len(manager) == 0
        assert len(manager.load_warnings) == 1


class TestLookup:
    def test_get_by_id(self, populated):
        task = populated.tasks[0]
        assert populated.get(task.task_id) is task
        with pytest.raises(TaskNotFoundError):
            populated.get("task_does_not_exist")

    def test_by_index_is_one_based(self, populated):
        assert populated.by_index(1) is populated.tasks[0]
        assert populated.by_index("3") is populated.tasks[2]
        for bad in (0, 4, "abc", None):
            with pytest.raises(TaskNotFoundError):
                populated.by_index(bad)

    def test_resolve_accepts_id_or_position(self, populated):
        task = populated.tasks[1]
        assert populated.resolve(task.task_id) is task
        assert populated.resolve("2") is task

    def test_tasks_property_returns_a_copy(self, populated):
        snapshot = populated.tasks
        snapshot.clear()
        assert len(populated) == 3


class TestFilteringAndSearch:
    def test_filter_by_priority(self, populated):
        assert len(populated.filter(priority=Priority.URGENT)) == 1
        assert len(populated.filter(priority="personal")) == 1
        assert populated.filter(priority=Priority.WORK) == []
        with pytest.raises(UnknownPriorityError):
            populated.filter(priority="nope")

    def test_completed_and_pending(self, populated):
        target = populated.filter(priority=Priority.PERSONAL)[0]
        populated.complete_task(target.task_id, when=NOW)
        assert [t.title for t in populated.completed()] == ["Read book"]
        assert len(populated.pending()) == 2

    def test_overdue(self, populated):
        overdue = populated.overdue(now=NOW)
        assert [t.title for t in overdue] == ["Ship release"]

    def test_search_matches_title_and_description(self, populated):
        assert [t.title for t in populated.search("ship")] == ["Ship release"]
        assert [t.title for t in populated.search("chapter")] == ["Read book"]
        assert populated.search("nothing here") == []

    def test_sorted_by_priority_puts_urgent_first(self, populated):
        order = [t.title for t in populated.sorted_tasks("priority")]
        assert order[0] == "Ship release"

    def test_sorted_by_due_date_places_undated_last(self, populated):
        order = [t.title for t in populated.sorted_tasks("due_date", now=NOW)]
        assert order == ["Ship release", "Water plants", "Read book"]

    def test_completed_tasks_sort_last(self, populated):
        populated.complete_task("1", when=NOW)
        order = [t.title for t in populated.sorted_tasks("priority")]
        assert order[-1] == "Ship release"

    def test_unknown_sort_key_rejected(self, populated):
        with pytest.raises(ValidationError):
            populated.sorted_tasks("colour")

    def test_sort_persists_the_new_order(self, populated, data_file):
        populated.sort("title")
        titles = [record["title"] for record in json.loads(data_file.read_text(encoding="utf-8"))]
        assert titles == ["Read book", "Ship release", "Water plants"]


class TestMutations:
    def test_complete_task_reports_change(self, populated):
        task, changed = populated.complete_task("2", when=NOW)
        assert changed is True and task.completed is True
        _, changed_again = populated.complete_task("2", when=NOW)
        assert changed_again is False

    def test_completing_a_routine_reschedules_it(self, populated):
        routine = populated.filter(priority=Priority.ROUTINE)[0]
        original_due = routine.due_date
        task, changed = populated.complete_task(routine.task_id, when=NOW)
        assert changed is True
        assert task.completed is False
        assert task.due_date > original_due
        assert task.occurrences == 1

    def test_reopen(self, populated):
        populated.complete_task("2", when=NOW)
        task, changed = populated.reopen_task("2")
        assert changed is True and task.completed is False

    def test_remove_task(self, populated, data_file):
        removed = populated.remove_task("2")
        assert removed.title == "Read book"
        assert len(populated) == 2
        assert len(json.loads(data_file.read_text(encoding="utf-8"))) == 2
        with pytest.raises(TaskNotFoundError):
            populated.remove_task(removed.task_id)

    def test_clear_completed(self, populated):
        populated.complete_task("2", when=NOW)
        assert [t.title for t in populated.clear_completed()] == ["Read book"]
        assert len(populated) == 2
        assert populated.clear_completed() == []

    def test_escalate_overdue_only_touches_high_priority(self, populated):
        escalated = populated.escalate_overdue(now=NOW)
        assert [t.title for t in escalated] == ["Ship release"]
        assert escalated[0].escalation_level == 1
        assert populated.escalate_overdue(now=NOW) == []


class TestTransfer:
    def test_transfer_within_the_same_class_keeps_the_object(self, populated):
        task = populated.resolve("2")
        moved = populated.transfer_task(task.task_id, Priority.WORK)
        assert moved is task
        assert moved.priority is Priority.WORK

    def test_transfer_to_the_same_priority_is_a_no_op(self, populated):
        task = populated.resolve("2")
        assert populated.transfer_task(task.task_id, Priority.PERSONAL) is task

    def test_transfer_rebuilds_when_the_class_changes(self, populated):
        task = populated.resolve("2")
        moved = populated.transfer_task(task.task_id, Priority.URGENT)
        assert isinstance(moved, HighPriorityTask)
        assert moved.task_id == task.task_id
        assert moved.title == task.title
        assert moved.created_at == task.created_at
        assert populated.get(task.task_id) is moved
        assert len(populated) == 3

    def test_transfer_to_routine_gets_a_default_frequency(self, populated):
        moved = populated.transfer_task("2", Priority.ROUTINE)
        assert isinstance(moved, RoutineTask)
        assert moved.frequency == "weekly"

    def test_transfer_away_from_high_priority_drops_escalation(self, populated):
        populated.escalate_overdue(now=NOW)
        moved = populated.transfer_task("1", Priority.LOW_PRIORITY)
        assert type(moved) is Task
        assert "escalation_level" not in moved.to_dict()

    def test_transfer_preserves_completion(self, populated):
        populated.complete_task("2", when=NOW)
        moved = populated.transfer_task("2", Priority.URGENT)
        assert moved.completed is True
        assert moved.completed_at == NOW

    def test_transfer_rejects_unknown_priority(self, populated):
        with pytest.raises(UnknownPriorityError):
            populated.transfer_task("1", "somewhere")


class TestReporting:
    def test_statistics(self, populated):
        populated.complete_task("2", when=NOW)
        stats = populated.statistics(now=NOW)
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["pending"] == 2
        assert stats["completion_rate"] == pytest.approx(33.333, rel=1e-3)
        assert stats["overdue"] == 1
        assert stats["by_priority"]["Urgent"] == 1
        assert stats["by_priority"]["Work"] == 0
        assert set(stats["by_priority"]) == {p.value for p in Priority}

    def test_statistics_on_an_empty_manager(self, manager):
        stats = manager.statistics(now=NOW)
        assert stats["total"] == 0
        assert stats["completion_rate"] == 0.0
        assert sum(stats["by_priority"].values()) == 0

    def test_upcoming_uses_the_window(self, populated):
        assert [t.title for t in populated.upcoming(days=3, now=NOW)] == ["Water plants"]
        assert populated.upcoming(days=1, now=NOW) == []

    def test_upcoming_excludes_overdue_and_completed(self, manager):
        manager.add_task("Late", priority=Priority.URGENT, due_date="2026-01-01")
        soon = manager.add_task("Soon", priority=Priority.WORK, due_date="2026-03-02")
        manager.add_task("Done", priority=Priority.WORK, due_date="2026-03-02")
        manager.complete_task("3", when=NOW)
        assert [t.title for t in manager.upcoming(days=5, now=NOW)] == [soon.title]

    def test_upcoming_is_ordered_by_due_date(self, manager):
        manager.add_task("Later", priority=Priority.WORK, due_date="2026-03-04")
        manager.add_task("Sooner", priority=Priority.WORK, due_date="2026-03-02")
        assert [t.title for t in manager.upcoming(days=10, now=NOW)] == ["Sooner", "Later"]

    def test_upcoming_window_defaults_to_configuration(self, manager, clean_env):
        manager.add_task("Next week", priority=Priority.WORK,
                         due_date=(NOW + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"))
        assert manager.upcoming(now=NOW) == []
        clean_env.setenv("TASK_SCHEDULER_UPCOMING_DAYS", "7")
        assert len(manager.upcoming(now=NOW)) == 1


def test_manager_iterates_in_stored_order(populated):
    assert [t.title for t in populated] == ["Ship release", "Read book", "Water plants"]


def test_manager_reload_discards_unsaved_changes(storage):
    manager = TaskManager(storage, autosave=False)
    manager.add_task("Temporary", priority=Priority.WORK)
    manager.load()
    assert len(manager) == 0


def test_queries_default_to_the_wall_clock(manager):
    long_past = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    manager.add_task("Way overdue", priority=Priority.URGENT, due_date=long_past)
    assert len(manager.overdue()) == 1
    assert manager.statistics()["overdue"] == 1
