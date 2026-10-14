from unittest.mock import MagicMock, patch
import pytest
from pymongo.errors import ConnectionFailure, OperationFailure
from app.services.mongo_service import MongoService


def test_mongo_service_connection_failure(app):
    """Simulate failure in MongoClient connection."""
    with app.app_context():
        with patch("app.services.mongo_service.MongoClient", side_effect=ConnectionFailure("Cannot connect")):
            service = MongoService()
            with pytest.raises(ConnectionFailure):
                service._get_db_connection()


def test_mongo_service_insert_operation_failure(app):
    """Simulate OperationFailure during insert."""
    with app.app_context():
        service = MongoService()
        with patch.object(service, "_get_db_connection") as mock_conn:
            mock_col = MagicMock()
            mock_col.insert_one.side_effect = OperationFailure("Write error")
            mock_conn.return_value = mock_col
            with pytest.raises(OperationFailure):
                service.insert_task({"task_id": "1"})


def test_mongo_service_update_operation_failure(app):
    """Simulate OperationFailure during update."""
    with app.app_context():
        service = MongoService()
        with patch.object(service, "_get_db_connection") as mock_conn:
            mock_col = MagicMock()
            mock_col.update_one.side_effect = OperationFailure("Update error")
            mock_conn.return_value = mock_col
            with pytest.raises(OperationFailure):
                service.update_task("1", {"name": "foo"})


def test_mongo_service_delete_operation_failure(app):
    """Simulate OperationFailure during delete."""
    with app.app_context():
        service = MongoService()
        with patch.object(service, "_get_db_connection") as mock_conn:
            mock_col = MagicMock()
            mock_col.delete_one.side_effect = OperationFailure("Delete error")
            mock_conn.return_value = mock_col
            with pytest.raises(OperationFailure):
                service.delete_task("1")


def test_mongo_service_get_task_exception(app):
    """Simulate Exception during get_task."""
    with app.app_context():
        service = MongoService()
        with patch.object(service, "_get_db_connection") as mock_conn:
            mock_col = MagicMock()
            mock_col.find_one.side_effect = Exception("Find error")
            mock_conn.return_value = mock_col
            with pytest.raises(Exception):
                service.get_task("1")


def test_mongo_service_categories_exception(app):
    """Simulate Exception during categories operations."""
    with app.app_context():
        service = MongoService()
        with patch.object(service, "_get_collection") as mock_col_fn:
            mock_col = MagicMock()
            mock_col.find_one.side_effect = Exception("Cat find error")
            mock_col.replace_one.side_effect = Exception("Cat replace error")
            mock_col.delete_many.side_effect = Exception("Cat delete error")
            mock_col_fn.return_value = mock_col
            
            with pytest.raises(Exception):
                service.get_categories()
            with pytest.raises(Exception):
                service.update_categories({"categories": []})
            with pytest.raises(Exception):
                service.clear_categories_collection()
