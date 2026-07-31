# Task Scheduler CLI

A command-line task manager built as a study in object-oriented Python. Tasks are
organised into eight priority categories; the category decides which kind of task
object you get, so an urgent item tracks a deadline and escalates while a routine
item reschedules itself every time you complete it.

Standard library only — no runtime dependencies.

## Features

- **Add tasks** in any of eight priority categories
- **Complete tasks** with a recorded timestamp (routine tasks roll forward instead)
- **Remove tasks** with confirmation
- **Transfer tasks** between priority categories, rebuilding the task type as needed
- **Search** by keyword across titles and descriptions
- **View** all, pending, completed, or a single priority
- **Statistics** covering completion rate, overdue counts and a priority breakdown
- **Automatic escalation** of overdue high-priority tasks at startup
- **Crash-safe storage** — atomic writes, and a damaged data file is quarantined
  rather than taking the app down with it

### Priority categories

| Category | Task class | Extra behaviour |
| --- | --- | --- |
| Urgent | `HighPriorityTask` | deadline tracking, escalation |
| High Priority | `HighPriorityTask` | deadline tracking, escalation |
| Work | `Task` | — |
| To Do | `Task` | — |
| Routine | `RoutineTask` | daily/weekly/monthly recurrence |
| Personal | `Task` | — |
| Prefer To Do | `Task` | — |
| Low Priority | `Task` | — |

## Setup

Requires Python 3.8 or newer.

```bash
git clone https://github.com/SdSarthak/Task-Scheduler.git
cd Task-Scheduler

# Only needed to run the tests; the app itself has no dependencies.
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python main.py                      # uses ./tasks.json
python main.py path/to/tasks.json   # or point it somewhere else
python -m task_scheduler            # equivalent entry point
```

The menu:

```
                    MAIN MENU
==================================================
1.  Add New Task
2.  View All Tasks
3.  View Tasks by Priority
4.  View Completed Tasks
5.  View Pending Tasks
6.  Complete Task
7.  Remove Task
8.  Transfer Task Priority
9.  Search Tasks
10. View Statistics
11. Help
0.  Exit
==================================================
```

Any prompt asking for a task accepts either the id in square brackets or the
number beside it in the most recent listing. Dates are entered as `YYYY-MM-DD`
or `YYYY-MM-DD HH:MM`; leave an optional date prompt blank to skip it.

### Sample output

```
1. [task_1785457867532_1] Buy milk
   Description: from the corner shop
   Priority: Urgent
   Created: 2026-07-31 06:01:07
   Status: o Pending
   Due: 2026-08-05 00:00:00
   Deadline: 2026-08-05 00:00:00 (in 4 days)
```

### Using it as a library

The CLI is a thin layer over an importable package, so the same operations are
available from Python:

```python
from task_scheduler import Priority, TaskManager, TaskStorage

manager = TaskManager(TaskStorage("tasks.json"))
manager.add_task("Ship release", "cut v1.0", Priority.URGENT, due_date="2026-08-05")
manager.add_task("Water plants", frequency="weekly", priority=Priority.ROUTINE)

manager.complete_task(1)                 # by listing position, or pass a task id
print(manager.statistics())
print([t.title for t in manager.overdue()])
```

Every mutation is written to disk immediately. Pass `autosave=False` to batch
changes and call `manager.save()` yourself.

## Configuration

All settings are optional environment variables. Copy `.env.example` to `.env`
for reference; the defaults are what the app uses when nothing is set.

| Variable | Default | Purpose |
| --- | --- | --- |
| `TASK_SCHEDULER_DATA_FILE` | `tasks.json` | Where tasks are persisted |
| `TASK_SCHEDULER_UPCOMING_DAYS` | `3` | Look-ahead window for upcoming deadlines |
| `TASK_SCHEDULER_BACKUP_CORRUPT` | `1` | Keep a backup when replacing an unreadable data file |

## Data

There is no dataset to download. The app creates its own `tasks.json` on first
save, and that file is git-ignored — your tasks are yours and never end up in the
repository. Files written by the original version of this project (integer
priorities 1–5) are migrated automatically on load.

## Project layout

```
Task Scheduler/
├── main.py                     # launcher
├── task_scheduler/
│   ├── __init__.py             # public API
│   ├── __main__.py             # python -m task_scheduler
│   ├── config.py               # priorities, formats, environment settings
│   ├── dates.py                # parsing, formatting, relative time
│   ├── exceptions.py           # error hierarchy
│   ├── models.py               # TaskInterface, Task, HighPriorityTask, RoutineTask
│   ├── factory.py              # TaskFactory, legacy-format migration
│   ├── storage.py              # atomic JSON persistence
│   ├── manager.py              # business logic
│   └── cli.py                  # menus and input handling
├── tests/                      # pytest suite
├── requirements.txt
├── pytest.ini
└── .env.example
```

## Architecture

```
TaskInterface (ABC)
    |
    Task
    |-- HighPriorityTask
    |-- RoutineTask
```

- **`TaskInterface`** — abstract base declaring `display()`, `to_dict()` and
  `validate()`.
- **`Task`** — the base task. State is private (`__title`, `__priority`, …) and
  reached through properties, so every assignment is validated; `task_id` and
  `created_at` are read-only.
- **`HighPriorityTask`** — adds `deadline` (an alias of `due_date`),
  `time_remaining()` and escalation.
- **`RoutineTask`** — overrides `complete()` so completing an occurrence counts it
  and advances the due date, skipping any occurrences that were missed.
- **`TaskFactory`** — maps a priority to the right class and rebuilds stored
  records, including the legacy format.
- **`TaskStorage`** — all file I/O, isolated behind `load()`/`save()`.
- **`TaskManager`** — HAS-A `TaskStorage` (composition) and HAS-A list of tasks
  (aggregation); owns all business logic.
- **`CLIInterface`** — presentation and input only; delegates every state change
  to the manager.

The OOP concepts on display: inheritance, method overriding, polymorphic
`display()`/`to_dict()`/`complete()` across three task classes, encapsulation via
name mangling and properties, abstraction through the ABC, the factory pattern,
and composition over inheritance between manager and storage.

## Tests

```bash
python -m pytest
```

138 tests covering the models, factory (including legacy migration), storage
(including corrupt-file recovery), manager and the CLI. The suite is
deterministic — it pins a fixed "now", writes only to pytest temp directories,
and needs no network or database.

## Extending it

To add a task type: subclass `Task`, override `display()`/`to_dict()`/`validate()`
plus a `from_dict()` classmethod, give it a unique `task_type`, register it in
`TASK_TYPES`, and teach `TaskFactory.class_for_priority()` when to pick it.

## License

Educational project — free to use, modify and share.
