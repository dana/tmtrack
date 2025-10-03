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

    def _get_collection(self, collection_name: str):
        """Returns a collection object from the database by name."""
        # Ensure we have a database connection
        if self.db is None:
            self._get_db_connection()
        return self.db[collection_name]

    # --- New methods for the 'categories' collection ---
    def get_categories(self):
        """Retrieves the single categories document."""
        collection = self._get_collection('categories')
        try:
            return collection.find_one()
        except Exception as e:
            print(f"MongoDB find_one operation failed on 'categories' collection: {e}")
            raise e

    def update_categories(self, categories_doc: dict):
        """
        Replaces the single categories document.
        Uses upsert=True to create the document if it doesn't exist.
        """
        collection = self._get_collection('categories')
        try:
            # The filter {} matches any single document.
            # replace_one with upsert=True will replace the one doc or create it.
            result = collection.replace_one({}, categories_doc, upsert=True)
            return result
        except Exception as e:
            print(f"MongoDB replace_one operation failed on 'categories' collection: {e}")
            raise e

    def clear_categories_collection(self):
        """Clears all documents from the categories collection for testing."""
        collection = self._get_collection('categories')
        try:
            collection.delete_many({})
        except Exception as e:
            print(f"MongoDB clear_categories_collection operation failed: {e}")
            raise e
            
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

    def get_all_tasks(self, userids: list[str] | None = None):
        """
        Retrieves all tasks, optionally filtered by a list of userids.

        Args:
            userids: An optional list of userid strings to filter the results.
                     If None, all tasks are returned.

        Returns:
            A list of task documents.
        """
        collection = self._get_db_connection()
        query = {}
        if userids is not None:
            # Use the $in operator to find tasks where userid is in the provided list
            query = {"userid": {"$in": userids}}
        try:
            return list(collection.find(query))
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
