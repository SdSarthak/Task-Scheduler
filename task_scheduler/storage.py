"""JSON persistence for tasks.

Writes go through a temporary file and an atomic replace so an interrupted
save cannot leave a truncated ``tasks.json`` behind.
"""

import json
import os
import tempfile
from datetime import datetime

from .config import backup_corrupt_files, get_data_file
from .exceptions import StorageError, ValidationError
from .factory import TaskFactory


class TaskStorage:
    """Loads and saves tasks, isolating the rest of the app from file I/O."""

    def __init__(self, path=None):
        self.path = os.fspath(path) if path is not None else get_data_file()
        #: Records that could not be rebuilt during the last :meth:`load`.
        self.skipped = []

    # ------------------------------------------------------------------
    def exists(self):
        return os.path.exists(self.path)

    def load(self):
        """Return the stored tasks.

        A missing file yields an empty list. A file that is present but not
        readable as JSON is quarantined (see ``TASK_SCHEDULER_BACKUP_CORRUPT``)
        and treated as empty, so a damaged file never blocks the app. Individual
        records that fail validation are collected in :attr:`skipped`.
        """
        self.skipped = []
        if not self.exists():
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            self._quarantine("unreadable JSON: {}".format(exc))
            return []
        except OSError as exc:
            raise StorageError("Could not read {}: {}".format(self.path, exc)) from exc

        if not isinstance(raw, list):
            self._quarantine("expected a list of tasks, found {}".format(type(raw).__name__))
            return []

        tasks = []
        for index, record in enumerate(raw):
            try:
                tasks.append(TaskFactory.from_dict(record))
            except (ValidationError, TypeError, KeyError) as exc:
                self.skipped.append("record {}: {}".format(index + 1, exc))
        return tasks

    def save(self, tasks):
        """Persist ``tasks`` atomically. Returns the number of tasks written."""
        payload = [task.to_dict() for task in tasks]
        directory = os.path.dirname(os.path.abspath(self.path))
        try:
            os.makedirs(directory, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=directory,
                prefix=".tasks-",
                suffix=".tmp",
                delete=False,
            )
            temp_path = handle.name
            try:
                with handle:
                    json.dump(payload, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, self.path)
            except BaseException:
                self._remove_quietly(temp_path)
                raise
        except OSError as exc:
            raise StorageError("Could not write {}: {}".format(self.path, exc)) from exc
        return len(payload)

    # ------------------------------------------------------------------
    def _quarantine(self, reason):
        """Move an unusable tasks file aside so the app can start clean."""
        note = "{} is not usable ({}).".format(self.path, reason)
        if not backup_corrupt_files():
            self.skipped.append(note + " Backups are disabled; it will be overwritten.")
            return
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup = "{}.corrupt.{}".format(self.path, stamp)
        try:
            os.replace(self.path, backup)
            self.skipped.append(note + " Moved to {}.".format(backup))
        except OSError as exc:
            self.skipped.append(note + " Backup failed: {}.".format(exc))

    @staticmethod
    def _remove_quietly(path):
        try:
            os.unlink(path)
        except OSError:
            pass
