import json

import pytest

from task_scheduler import Priority, StorageError, TaskFactory, TaskStorage
from task_scheduler.config import get_data_file, get_upcoming_days


def sample_tasks():
    return [
        TaskFactory.create("Ship release", "cut v1.0", Priority.URGENT, due_date="2026-03-04"),
        TaskFactory.create("Read book", "chapter 4", Priority.PERSONAL),
        TaskFactory.create("Water plants", "", Priority.ROUTINE, frequency="weekly"),
    ]


def test_missing_file_loads_empty(storage):
    assert storage.exists() is False
    assert storage.load() == []
    assert storage.skipped == []


def test_round_trip(storage):
    tasks = sample_tasks()
    assert storage.save(tasks) == 3
    restored = storage.load()
    assert [t.to_dict() for t in restored] == [t.to_dict() for t in tasks]
    assert [type(t).__name__ for t in restored] == [type(t).__name__ for t in tasks]


def test_round_trip_preserves_timestamps_exactly(storage):
    """Timestamps are stored to the second, so they must be created that way."""
    tasks = sample_tasks()
    storage.save(tasks)
    for original, restored in zip(tasks, storage.load()):
        assert restored.created_at == original.created_at
        assert restored.created_at.microsecond == 0
        assert restored.due_date == original.due_date


def test_save_writes_readable_json(storage, data_file):
    storage.save(sample_tasks())
    payload = json.loads(data_file.read_text(encoding="utf-8"))
    assert isinstance(payload, list) and len(payload) == 3
    assert payload[0]["title"] == "Ship release"


def test_save_creates_missing_directories(tmp_path):
    target = tmp_path / "nested" / "deeper" / "tasks.json"
    TaskStorage(str(target)).save(sample_tasks())
    assert target.exists()


def test_save_leaves_no_temporary_files(storage, data_file, tmp_path):
    storage.save(sample_tasks())
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != data_file.name]
    assert leftovers == []


def test_corrupt_file_is_quarantined(storage, data_file, tmp_path, clean_env):
    data_file.write_text("{not json at all", encoding="utf-8")
    assert storage.load() == []
    assert any("not usable" in note for note in storage.skipped)
    backups = list(tmp_path.glob("tasks.json.corrupt.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not json at all"
    assert not data_file.exists()


def test_backup_can_be_disabled(storage, data_file, tmp_path, clean_env):
    clean_env.setenv("TASK_SCHEDULER_BACKUP_CORRUPT", "0")
    data_file.write_text("nope", encoding="utf-8")
    assert storage.load() == []
    assert list(tmp_path.glob("tasks.json.corrupt.*")) == []
    assert data_file.exists()


def test_non_list_payload_is_quarantined(storage, data_file, clean_env):
    data_file.write_text('{"title": "single object"}', encoding="utf-8")
    assert storage.load() == []
    assert any("expected a list" in note for note in storage.skipped)


def test_bad_records_are_skipped_not_fatal(storage, data_file):
    good = sample_tasks()[0].to_dict()
    data_file.write_text(json.dumps([good, {"title": ""}, "junk"]), encoding="utf-8")
    tasks = storage.load()
    assert len(tasks) == 1
    assert tasks[0].title == "Ship release"
    assert len(storage.skipped) == 2


def test_unreadable_path_raises_storage_error(tmp_path):
    directory = tmp_path / "a_directory"
    directory.mkdir()
    with pytest.raises(StorageError):
        TaskStorage(str(directory)).save(sample_tasks())


def test_storage_defaults_to_configured_path(clean_env):
    clean_env.setenv("TASK_SCHEDULER_DATA_FILE", "custom-tasks.json")
    assert get_data_file() == "custom-tasks.json"
    assert TaskStorage().path == "custom-tasks.json"


def test_upcoming_days_config(clean_env):
    assert get_upcoming_days() == 3
    clean_env.setenv("TASK_SCHEDULER_UPCOMING_DAYS", "10")
    assert get_upcoming_days() == 10
    clean_env.setenv("TASK_SCHEDULER_UPCOMING_DAYS", "not-a-number")
    assert get_upcoming_days() == 3
    clean_env.setenv("TASK_SCHEDULER_UPCOMING_DAYS", "-5")
    assert get_upcoming_days() == 3
