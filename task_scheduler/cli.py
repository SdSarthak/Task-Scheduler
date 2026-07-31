"""The interactive command-line interface (view/controller layer).

``CLIInterface`` owns presentation and input handling only; every state change
is delegated to :class:`~task_scheduler.manager.TaskManager`.
"""

import sys

from .config import FREQUENCY_DAYS, PRIORITY_ORDER, Priority, get_data_file
from .dates import now as clock_now, parse_datetime
from .exceptions import TaskSchedulerError
from .factory import TaskFactory
from .manager import TaskManager
from .models import HighPriorityTask, RoutineTask
from .storage import TaskStorage

SEPARATOR = "=" * 50
THIN = "-" * 30

MENU = (
    ("1", "Add New Task"),
    ("2", "View All Tasks"),
    ("3", "View Tasks by Priority"),
    ("4", "View Completed Tasks"),
    ("5", "View Pending Tasks"),
    ("6", "Complete Task"),
    ("7", "Remove Task"),
    ("8", "Transfer Task Priority"),
    ("9", "Search Tasks"),
    ("10", "View Statistics"),
    ("11", "Help"),
    ("0", "Exit"),
)

HELP_TEXT = """\
Task Scheduler help
{thin}
Tasks belong to one of eight priority categories. The category decides which
kind of task is created:

  Urgent, High Priority -> deadline tracking and escalation
  Routine               -> recurring; completing it schedules the next run
  everything else       -> a plain task

Referring to a task
  Any prompt that asks for a task accepts either the task id shown in
  square brackets or the number next to it in the most recent listing.

Dates
  Enter due dates as YYYY-MM-DD or 'YYYY-MM-DD HH:MM'. Leave the prompt
  empty to skip an optional date.

Storage
  Tasks are saved to '{data_file}' after every change. Override the location
  with the TASK_SCHEDULER_DATA_FILE environment variable.
"""


class CLIInterface:
    """Renders menus, collects input and reports results."""

    def __init__(self, manager=None, stream=None):
        self.manager = manager if manager is not None else TaskManager()
        self.stream = stream or sys.stdout
        self._running = False
        #: Set once stdin is exhausted so the menu loop stops instead of spinning.
        self.input_closed = False

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------
    def write(self, text=""):
        print(text, file=self.stream)

    def heading(self, title):
        self.write()
        self.write(title.center(len(SEPARATOR)))
        self.write(SEPARATOR)

    # ------------------------------------------------------------------
    # Input helpers
    # ------------------------------------------------------------------
    def prompt(self, message):
        """Read a line, treating EOF/Ctrl-C as an empty answer.

        Exhausted input also flips :attr:`input_closed` so the menu loop
        exits rather than re-prompting a stream that can never answer.
        """
        try:
            return input(message).strip()
        except (EOFError, KeyboardInterrupt):
            self.input_closed = True
            self.write()
            return ""

    def prompt_required(self, message):
        """Read a non-empty line; an empty answer aborts and returns ``None``."""
        value = self.prompt(message)
        if not value:
            self.write("Cancelled.")
            return None
        return value

    def prompt_date(self, message, required=False):
        """Read an optional date. Returns ``None`` when skipped or cancelled."""
        while True:
            raw = self.prompt(message)
            if not raw:
                if required:
                    self.write("Cancelled.")
                return None
            try:
                return parse_datetime(raw, "due date")
            except TaskSchedulerError as exc:
                self.write(str(exc))

    def prompt_choice(self, message, options):
        """Read one of ``options`` (case-insensitive). ``None`` when cancelled."""
        lowered = {option.lower(): option for option in options}
        while True:
            raw = self.prompt(message).lower()
            if not raw:
                self.write("Cancelled.")
                return None
            if raw in lowered:
                return lowered[raw]
            self.write("Please choose one of: {}.".format(", ".join(options)))

    def prompt_priority(self, message="Select a priority (1-8): "):
        """Show the priority menu and return the chosen ``Priority``."""
        for number, priority in enumerate(PRIORITY_ORDER, 1):
            self.write("{}. {}".format(number, priority))
        while True:
            raw = self.prompt(message)
            if not raw:
                self.write("Cancelled.")
                return None
            if raw.isdigit() and 1 <= int(raw) <= len(PRIORITY_ORDER):
                return PRIORITY_ORDER[int(raw) - 1]
            resolved = Priority.from_value(raw)
            if resolved is not None:
                return resolved
            self.write("Enter a number between 1 and {}.".format(len(PRIORITY_ORDER)))

    def confirm(self, message):
        return self.prompt("{} [y/N]: ".format(message)).lower() in ("y", "yes")

    def prompt_task(self, message="Task id or number: "):
        """Resolve a task from user input, or ``None`` if cancelled/not found."""
        raw = self.prompt(message)
        if not raw:
            self.write("Cancelled.")
            return None
        try:
            return self.manager.resolve(raw)
        except TaskSchedulerError as exc:
            self.write(str(exc))
            return None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def show_tasks(self, tasks, empty_message="No tasks found."):
        if not tasks:
            self.write(empty_message)
            return
        now = clock_now()
        for number, task in enumerate(tasks, 1):
            self.write()
            self.write("{}. {}".format(number, task.display(now).replace("\n", "\n   ")))

    def show_menu(self):
        self.heading("MAIN MENU")
        for key, label in MENU:
            self.write("{:<3} {}".format(key + ".", label))
        self.write(SEPARATOR)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def add_task(self):
        self.heading("ADD NEW TASK")
        title = self.prompt_required("Title: ")
        if title is None:
            return
        description = self.prompt("Description (optional): ")
        priority = self.prompt_priority()
        if priority is None:
            return

        extras = {}
        target = TaskFactory.class_for_priority(priority)
        if target is HighPriorityTask:
            deadline = self.prompt_date("Deadline (YYYY-MM-DD, blank to skip): ")
            if deadline is not None:
                extras["due_date"] = deadline
        elif target is RoutineTask:
            frequency = self.prompt_choice(
                "Frequency ({}): ".format("/".join(sorted(FREQUENCY_DAYS))),
                sorted(FREQUENCY_DAYS),
            )
            if frequency is None:
                return
            extras["frequency"] = frequency
            first_due = self.prompt_date("First due date (YYYY-MM-DD, blank for auto): ")
            if first_due is not None:
                extras["due_date"] = first_due
        else:
            due = self.prompt_date("Due date (YYYY-MM-DD, blank to skip): ")
            if due is not None:
                extras["due_date"] = due

        task = self.manager.add_task(title, description, priority, **extras)
        self.write("Added [{}] {}.".format(task.task_id, task.title))

    def view_all(self):
        self.heading("ALL TASKS")
        self.show_tasks(self.manager.sorted_tasks("priority"))

    def view_by_priority(self):
        self.heading("TASKS BY PRIORITY")
        priority = self.prompt_priority()
        if priority is None:
            return
        tasks = self.manager.filter(priority=priority)
        self.write()
        self.write("{} ({} task{})".format(priority, len(tasks), "" if len(tasks) == 1 else "s"))
        self.show_tasks(tasks, "No tasks with priority {}.".format(priority))

    def view_completed(self):
        self.heading("COMPLETED TASKS")
        self.show_tasks(self.manager.completed(), "No completed tasks yet.")

    def view_pending(self):
        self.heading("PENDING TASKS")
        pending = [task for task in self.manager.sorted_tasks("due_date") if not task.completed]
        self.show_tasks(pending, "Nothing pending. Well done.")

    def complete_task(self):
        self.heading("COMPLETE TASK")
        self.show_tasks(self.manager.tasks)
        task = self.prompt_task()
        if task is None:
            return
        task, changed = self.manager.complete_task(task.task_id)
        if not changed:
            self.write("'{}' was already complete.".format(task.title))
        elif isinstance(task, RoutineTask):
            self.write(
                "Logged '{}'. Next occurrence due {}.".format(
                    task.title, task.due_date.strftime("%Y-%m-%d %H:%M")
                )
            )
        else:
            self.write("Completed '{}'.".format(task.title))

    def remove_task(self):
        self.heading("REMOVE TASK")
        self.show_tasks(self.manager.tasks)
        task = self.prompt_task()
        if task is None:
            return
        if not self.confirm("Delete '{}'?".format(task.title)):
            self.write("Kept.")
            return
        self.manager.remove_task(task.task_id)
        self.write("Removed '{}'.".format(task.title))

    def transfer_task(self):
        self.heading("TRANSFER TASK PRIORITY")
        self.show_tasks(self.manager.tasks)
        task = self.prompt_task()
        if task is None:
            return
        self.write("Current priority: {}".format(task.priority))
        priority = self.prompt_priority("Move to (1-8): ")
        if priority is None:
            return
        moved = self.manager.transfer_task(task.task_id, priority)
        self.write("'{}' is now {}.".format(moved.title, moved.priority))

    def search_tasks(self):
        self.heading("SEARCH TASKS")
        term = self.prompt_required("Search term: ")
        if term is None:
            return
        results = self.manager.search(term)
        self.write("{} match{} for '{}'.".format(len(results), "" if len(results) == 1 else "es", term))
        self.show_tasks(results, "Nothing matched.")

    def show_statistics(self):
        stats = self.manager.statistics()
        self.heading("TASK STATISTICS")
        self.write("Total Tasks: {}".format(stats["total"]))
        self.write("Completed Tasks: {}".format(stats["completed"]))
        self.write("Pending Tasks: {}".format(stats["pending"]))
        self.write("Completion Rate: {:.1f}%".format(stats["completion_rate"]))
        self.write("Overdue Tasks: {}".format(stats["overdue"]))
        self.write()
        self.write("Tasks by Priority:")
        self.write(THIN)
        for priority in PRIORITY_ORDER:
            self.write("{}: {}".format(priority, stats["by_priority"][priority.value]))

        upcoming = self.manager.upcoming()
        self.write()
        if upcoming:
            self.write("Upcoming deadlines:")
            self.write(THIN)
            for task in upcoming:
                self.write("- {} (due {})".format(task.title, task.due_date.strftime("%Y-%m-%d %H:%M")))
        else:
            self.write("No deadlines in the days ahead.")

    def show_help(self):
        self.heading("HELP")
        self.write(HELP_TEXT.format(thin=THIN, data_file=get_data_file()))

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------
    def _actions(self):
        return {
            "1": self.add_task,
            "2": self.view_all,
            "3": self.view_by_priority,
            "4": self.view_completed,
            "5": self.view_pending,
            "6": self.complete_task,
            "7": self.remove_task,
            "8": self.transfer_task,
            "9": self.search_tasks,
            "10": self.show_statistics,
            "11": self.show_help,
        }

    def announce_warnings(self):
        for warning in self.manager.load_warnings:
            self.write("Warning: {}".format(warning))
        self.manager.load_warnings = []

    def run(self):
        """Run the menu loop until the user exits. Returns a process exit code."""
        self.heading("TASK SCHEDULER")
        self.announce_warnings()
        escalated = self.manager.escalate_overdue()
        if escalated:
            self.write("{} overdue task(s) escalated.".format(len(escalated)))

        actions = self._actions()
        self._running = True
        while self._running:
            self.show_menu()
            choice = self.prompt("Select an option (0-11): ")
            if choice == "0" or self.input_closed:
                self._running = False
                break
            action = actions.get(choice)
            if action is None:
                self.write("Invalid option. Choose a number from 0 to 11.")
                continue
            try:
                action()
            except TaskSchedulerError as exc:
                self.write("Error: {}".format(exc))

        try:
            self.manager.save()
        except TaskSchedulerError as exc:
            self.write("Could not save tasks: {}".format(exc))
            return 1
        self.write("Goodbye.")
        return 0


def main(argv=None):
    """Entry point used by ``main.py`` and ``python -m task_scheduler``."""
    argv = list(sys.argv[1:] if argv is None else argv)
    data_file = None
    if argv:
        if argv[0] in ("-h", "--help"):
            print("Usage: python main.py [path/to/tasks.json]")
            return 0
        data_file = argv[0]

    try:
        manager = TaskManager(TaskStorage(data_file or get_data_file()))
    except TaskSchedulerError as exc:
        print("Could not start: {}".format(exc), file=sys.stderr)
        return 1
    return CLIInterface(manager).run()
