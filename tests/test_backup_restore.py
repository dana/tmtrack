import json
import os
import pytest
from pymongo import MongoClient
import backup
import restore


def test_backup_and_restore_cycle(mongodb_uri, tmp_path):
    """
    Seed database in collections 'categories' and 'daily_tasks',
    run backup to JSON file, clear collections,
    run restore from file, and verify full document fidelity.
    """
    db_name = "tmtrack_test_db"
    backup_file = str(tmp_path / "test_backup.json")

    client = MongoClient(mongodb_uri)
    db = client[db_name]
    cat_col = db["categories"]
    tasks_col = db["daily_tasks"]

    # Clear first
    cat_col.delete_many({})
    tasks_col.delete_many({})

    # Seed
    cat_col.insert_one({"categories": ["Dev", "Ops", "Review"]})
    tasks_col.insert_one({
        "task_id": "b-task-1",
        "userid": "dana",
        "date": "2023-07-01",
        "category": "Dev",
        "expected_hours": 3.5,
        "task_name": "Backup testing task",
    })

    # Run backup
    backup.backup_database(mongodb_uri, db_name, backup_file)
    assert os.path.exists(backup_file)

    with open(backup_file, 'r') as f:
        data = json.load(f)
    assert "categories" in data
    assert "daily_tasks" in data
    assert len(data["categories"]) >= 1
    assert any(t.get("task_id") == "b-task-1" for t in data["daily_tasks"])

    # Clear database
    cat_col.delete_many({})
    tasks_col.delete_many({})
    assert cat_col.count_documents({}) == 0
    assert tasks_col.count_documents({}) == 0

    # Run restore
    restore.restore_database(mongodb_uri, db_name, backup_file)

    # Verify restored data
    restored_cat = cat_col.find_one({})
    assert restored_cat is not None
    assert restored_cat["categories"] == ["Dev", "Ops", "Review"]

    restored_task = tasks_col.find_one({"task_id": "b-task-1"})
    assert restored_task is not None
    assert restored_task["task_name"] == "Backup testing task"
    assert restored_task["expected_hours"] == 3.5

    # Cleanup
    cat_col.delete_many({})
    tasks_col.delete_many({})
    client.close()


def test_restore_missing_file(mongodb_uri, capsys):
    """Restoring a non-existent file handles FileNotFoundError gracefully."""
    restore.restore_database(mongodb_uri, "tmtrack_test_db", "/non/existent/file.json")
    captured = capsys.readouterr()
    assert "ERROR: Backup file not found" in captured.out


def test_restore_corrupted_json(tmp_path, mongodb_uri, capsys):
    """Restoring a corrupted JSON file handles JSONDecodeError gracefully."""
    bad_file = tmp_path / "corrupted.json"
    bad_file.write_text("{not valid json...")
    restore.restore_database(mongodb_uri, "tmtrack_test_db", str(bad_file))
    captured = capsys.readouterr()
    assert "ERROR: Could not parse backup file" in captured.out
