"""CLI tests: input is scripted, output is captured, nothing touches a terminal."""

import io
import json

import pytest

from task_scheduler import Priority, RoutineTask, TaskManager, TaskStorage
from task_scheduler.cli import CLIInterface, main


@pytest.fixture
def cli(manager, monkeypatch):
    """A CLI wired to a temp-file manager, with ``input`` under our control."""
    interface = CLIInterface(manager, stream=io.StringIO())

    def script(answers):
        queue = list(answers)

        def fake_input(_prompt=""):
            if not queue:
                raise EOFError
            return queue.pop(0)

        monkeypatch.setattr("builtins.input", fake_input)

    interface.script = script
    return interface


def output(cli):
    return cli.stream.getvalue()


class TestAddTask:
    def test_adds_a_plain_task(self, cli):
        cli.script(["Buy milk", "from the corner shop", "4", ""])
        cli.add_task()
        assert len(cli.manager) == 1
        task = cli.manager.tasks[0]
        assert task.title == "Buy milk"
        assert task.priority is Priority.TO_DO
        assert task.due_date is None
        assert "Added" in output(cli)

    def test_adds_a_high_priority_task_with_a_deadline(self, cli):
        cli.script(["Ship release", "cut v1.0", "1", "2026-03-04"])
        cli.add_task()
        task = cli.manager.tasks[0]
        assert task.priority is Priority.URGENT
        assert task.deadline.strftime("%Y-%m-%d") == "2026-03-04"

    def test_adds_a_routine_task(self, cli):
        cli.script(["Standup", "", "5", "daily", ""])
        cli.add_task()
        task = cli.manager.tasks[0]
        assert isinstance(task, RoutineTask)
        assert task.frequency == "daily"

    def test_priority_accepts_a_label(self, cli):
        cli.script(["Read book", "", "personal", ""])
        cli.add_task()
        assert cli.manager.tasks[0].priority is Priority.PERSONAL

    def test_empty_title_cancels(self, cli):
        cli.script([""])
        cli.add_task()
        assert len(cli.manager) == 0
        assert "Cancelled" in output(cli)

    def test_invalid_date_is_re_prompted(self, cli):
        cli.script(["Buy milk", "", "4", "next tuesday", "2026-03-04"])
        cli.add_task()
        assert cli.manager.tasks[0].due_date.strftime("%Y-%m-%d") == "2026-03-04"
        assert "Could not read" in output(cli)

    def test_invalid_priority_is_re_prompted(self, cli):
        cli.script(["Buy milk", "", "99", "4", ""])
        cli.add_task()
        assert cli.manager.tasks[0].priority is Priority.TO_DO
        assert "Enter a number between" in output(cli)

    def test_invalid_frequency_is_re_prompted(self, cli):
        cli.script(["Standup", "", "5", "hourly", "weekly", ""])
        cli.add_task()
        assert cli.manager.tasks[0].frequency == "weekly"
        assert "Please choose one of" in output(cli)


class TestViews:
    def test_view_all_lists_every_task(self, populated, cli):
        cli.view_all()
        text = output(cli)
        for title in ("Ship release", "Read book", "Water plants"):
            assert title in text

    def test_view_all_on_an_empty_list(self, cli):
        cli.view_all()
        assert "No tasks found." in output(cli)

    def test_view_by_priority(self, populated, cli):
        cli.script(["1"])
        cli.view_by_priority()
        text = output(cli)
        assert "Ship release" in text
        assert "Read book" not in text

    def test_view_by_empty_priority(self, populated, cli):
        cli.script(["3"])  # Work
        cli.view_by_priority()
        assert "No tasks with priority Work." in output(cli)

    def test_view_completed_and_pending(self, populated, cli):
        populated.complete_task("2")
        cli.view_completed()
        cli.view_pending()
        text = output(cli)
        assert text.index("COMPLETED TASKS") < text.index("PENDING TASKS")
        assert "Read book" in text
        assert "Ship release" in text

    def test_statistics_render(self, populated, cli):
        cli.show_statistics()
        text = output(cli)
        assert "Total Tasks: 3" in text
        assert "Completion Rate: 0.0%" in text
        for priority in Priority:
            assert priority.value in text

    def test_help_mentions_the_data_file(self, cli, clean_env):
        cli.show_help()
        assert "tasks.json" in output(cli)


class TestActions:
    def test_complete_by_number(self, populated, cli):
        cli.script(["2"])
        cli.complete_task()
        assert populated.resolve("2").completed is True
        assert "Completed 'Read book'." in output(cli)

    def test_complete_by_id(self, populated, cli):
        task = populated.tasks[1]
        cli.script([task.task_id])
        cli.complete_task()
        assert task.completed is True

    def test_complete_a_routine_reports_the_next_occurrence(self, populated, cli):
        cli.script(["3"])
        cli.complete_task()
        assert "Next occurrence due" in output(cli)

    def test_complete_reports_already_done(self, populated, cli):
        populated.complete_task("2")
        cli.script(["2"])
        cli.complete_task()
        assert "was already complete" in output(cli)

    def test_unknown_task_reference_is_reported(self, populated, cli):
        cli.script(["57"])
        cli.complete_task()
        assert "out of range" in output(cli)

    def test_remove_requires_confirmation(self, populated, cli):
        cli.script(["2", "n"])
        cli.remove_task()
        assert len(populated) == 3
        assert "Kept." in output(cli)

    def test_remove_confirmed(self, populated, cli, data_file):
        cli.script(["2", "y"])
        cli.remove_task()
        assert len(populated) == 2
        assert len(json.loads(data_file.read_text(encoding="utf-8"))) == 2

    def test_transfer(self, populated, cli):
        cli.script(["2", "3"])  # task 2 -> Work
        cli.transfer_task()
        assert populated.resolve("2").priority is Priority.WORK
        assert "is now Work" in output(cli)

    def test_search_reports_matches(self, populated, cli):
        cli.script(["book"])
        cli.search_tasks()
        text = output(cli)
        assert "1 match for 'book'." in text
        assert "Read book" in text

    def test_search_with_no_matches(self, populated, cli):
        cli.script(["zzz"])
        cli.search_tasks()
        assert "Nothing matched." in output(cli)


class TestRunLoop:
    def test_exit_saves_and_returns_zero(self, populated, cli, data_file):
        cli.script(["0"])
        assert cli.run() == 0
        assert "Goodbye." in output(cli)
        assert len(json.loads(data_file.read_text(encoding="utf-8"))) == 3

    def test_invalid_option_is_reported_then_the_loop_continues(self, cli):
        cli.script(["42", "0"])
        assert cli.run() == 0
        assert "Invalid option" in output(cli)

    def test_eof_exits_cleanly(self, cli):
        cli.script([])
        assert cli.run() == 0

    def test_menu_lists_every_option(self, cli):
        cli.script(["0"])
        cli.run()
        text = output(cli)
        for label in ("Add New Task", "Transfer Task Priority", "View Statistics", "Exit"):
            assert label in text

    def test_run_escalates_overdue_tasks_on_startup(self, populated, cli):
        cli.script(["0"])
        cli.run()
        assert "escalated" in output(cli)
        assert populated.resolve("1").escalation_level == 1

    def test_run_surfaces_load_warnings(self, data_file, monkeypatch):
        data_file.write_text(json.dumps([{"title": ""}]), encoding="utf-8")
        manager = TaskManager(TaskStorage(str(data_file)))
        interface = CLIInterface(manager, stream=io.StringIO())
        monkeypatch.setattr("builtins.input", lambda _prompt="": "0")
        interface.run()
        assert "Warning:" in interface.stream.getvalue()

    def test_workflow_add_complete_and_persist(self, cli, data_file):
        cli.script(["1", "Buy milk", "from the shop", "4", "2026-03-04", "6", "1", "0"])
        assert cli.run() == 0
        payload = json.loads(data_file.read_text(encoding="utf-8"))
        assert len(payload) == 1
        assert payload[0]["completed"] is True


class TestEntryPoint:
    def test_help_flag(self, capsys):
        assert main(["--help"]) == 0
        assert "Usage:" in capsys.readouterr().out

    def test_main_uses_the_path_argument(self, tmp_path, monkeypatch, capsys):
        target = tmp_path / "elsewhere.json"
        answers = iter(["1", "Buy milk", "", "4", "", "0"])
        monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
        assert main([str(target)]) == 0
        capsys.readouterr()
        assert json.loads(target.read_text(encoding="utf-8"))[0]["title"] == "Buy milk"
