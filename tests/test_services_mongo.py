import pytest
from bson import ObjectId
from app.services.mongo_service import MongoService


def test_mongo_service_task_crud(app):
    """Test direct MongoService CRUD operations on tasks."""
    with app.app_context():
        service = MongoService()
        
        # Insert
        task_data = {
            "task_id": "service-test-1",
            "userid": "testuser",
            "date": "2023-06-01",
            "category": "Testing",
            "expected_hours": 2.0,
            "task_name": "Direct Service Test",
        }
        res = service.insert_task(task_data)
        assert isinstance(res, ObjectId)
        
        # Get by task_id
        retrieved = service.get_task("service-test-1")
        assert retrieved is not None
        assert retrieved["task_name"] == "Direct Service Test"
        
        # Get non-existent
        assert service.get_task("non-existent-id") is None
        
        # Update
        mod_count = service.update_task("service-test-1", {"task_name": "Renamed Test"})
        assert mod_count == 1
        assert service.get_task("service-test-1")["task_name"] == "Renamed Test"
        
        # Update non-existent
        assert service.update_task("non-existent-id", {"task_name": "X"}) == 0
        
        # Get all tasks (unfiltered)
        all_tasks = service.get_all_tasks()
        assert len(all_tasks) == 1
        
        # Get all tasks (filtered)
        assert len(service.get_all_tasks(userids=["testuser"])) == 1
        assert len(service.get_all_tasks(userids=["otheruser"])) == 0
        
        # Delete
        del_count = service.delete_task("service-test-1")
        assert del_count == 1
        assert service.get_task("service-test-1") is None
        
        # Delete non-existent
        assert service.delete_task("service-test-1") == 0


def test_mongo_service_categories(app):
    """Test direct MongoService categories operations."""
    with app.app_context():
        service = MongoService()
        
        # Initially None
        assert service.get_categories() is None
        
        # Update / Upsert
        cat_doc = {"categories": ["Alpha", "Beta", "Gamma"]}
        res = service.update_categories(cat_doc)
        assert res.acknowledged is True
        
        # Retrieve
        retrieved = service.get_categories()
        assert retrieved is not None
        assert retrieved["categories"] == ["Alpha", "Beta", "Gamma"]
        
        # Clear
        service.clear_categories_collection()
        assert service.get_categories() is None


def test_mongo_service_clear_collection(app):
    """Test clear_collection empties tasks."""
    with app.app_context():
        service = MongoService()
        service.insert_task({"task_id": "t1", "userid": "u1"})
        service.insert_task({"task_id": "t2", "userid": "u2"})
        assert len(service.get_all_tasks()) == 2
        
        service.clear_collection()
        assert len(service.get_all_tasks()) == 0
