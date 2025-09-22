from pymongo import MongoClient
from flask import current_app
from pymongo.errors import ConnectionFailure, OperationFailure

class MongoService:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None

    def _get_db_connection(self):
        """
        Establishes a MongoDB connection if not already established.
        Uses configuration from Flask app context or default Config.
        """
        if self.client is None or self.collection is None:
            try:
                # Import Config here to avoid circular dependency if MongoService is imported early
                from ..config import Config

                # Use current_app.config if running within Flask app context
                # Otherwise, default to Config directly (useful for tests not in app context)
                # The 'app' fixture in tests/test_api.py sets app.config for testing
                mongo_uri = current_app.config.get('MONGO_URI', Config.MONGO_URI)
                db_name = current_app.config.get('MONGO_DB_NAME', Config.MONGO_DB_NAME)
                collection_name = current_app.config.get('MONGO_COLLECTION_NAME', Config.MONGO_COLLECTION_NAME)

                self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000) # 5-second timeout
                self.client.admin.command('ping') # Test connection
                self.db = self.client[db_name]
                self.collection = self.db[collection_name]
                print(f"Connected to MongoDB: {mongo_uri}, Database: {db_name}, Collection: {collection_name}")
            except ConnectionFailure as e:
                # Log the specific connection failure for better debugging
                print(f"ERROR: MongoDB connection failed: {e}")
                raise ConnectionFailure(f"Could not connect to MongoDB at {mongo_uri}. Is it running? {e}")
            except Exception as e:
                print(f"ERROR: An unexpected error occurred during MongoDB connection: {e}")
                raise e
        return self.collection

    def insert_task(self, task_data):
        """Inserts a new task document."""
        collection = self._get_db_connection()
        try:
            result = collection.insert_one(task_data)
            return result.inserted_id
        except OperationFailure as e:
            print(f"MongoDB insert operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during insert: {e}")
            raise e

    def update_task(self, task_id, update_data):
        """Updates an existing task document by task_id."""
        collection = self._get_db_connection()
        try:
            # $set operator updates only the specified fields
            result = collection.update_one(
                {"task_id": task_id},
                {"$set": update_data}
            )
            return result.modified_count
        except OperationFailure as e:
            print(f"MongoDB update operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during update: {e}")
            raise e

    def get_task(self, task_id):
        """Retrieves a single task by task_id."""
        collection = self._get_db_connection()
        try:
            return collection.find_one({"task_id": task_id})
        except OperationFailure as e:
            print(f"MongoDB find operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during get_task: {e}")
            raise e

    def get_all_tasks(self):
        """Retrieves all tasks."""
        collection = self._get_db_connection()
        try:
            return list(collection.find({}))
        except OperationFailure as e:
            print(f"MongoDB find operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during get_all_tasks: {e}")
            raise e

    def delete_task(self, task_id):
        """Deletes a single task by task_id."""
        collection = self._get_db_connection()
        try:
            result = collection.delete_one({"task_id": task_id})
            return result.deleted_count
        except OperationFailure as e:
            print(f"MongoDB delete operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during delete: {e}")
            raise e

    def clear_collection(self):
        """Clears all documents from the collection (use with caution, primarily for testing)."""
        # Ensure collection is correctly initialized, especially for non-app-context calls like setup/teardown
        if self.collection is None:
            self._get_db_connection() # Initialize if not already connected
        try:
            result = self.collection.delete_many({})
            print(f"Cleared {result.deleted_count} documents from {self.collection.name}")
            return result.deleted_count
        except OperationFailure as e:
            print(f"MongoDB clear_collection operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during clear_collection: {e}")
            raise e
