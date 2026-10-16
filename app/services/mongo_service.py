import datetime
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

    def get_all_tasks(self, userids: list[str] | None = None, start_date: str | None = None, end_date: str | None = None, date: str | None = None, sort_desc: bool = True):
        """
        Retrieves tasks, optionally filtered by userids and/or date range.

        Args:
            userids: An optional list of userid strings to filter the results.
            start_date: Optional start date (inclusive, YYYY-MM-DD).
            end_date: Optional end date (inclusive, YYYY-MM-DD).
            date: Optional exact date (YYYY-MM-DD). Takes precedence over start_date/end_date.
            sort_desc: If True, sorts descending by date (newest first).

        Returns:
            A list of task documents.
        """
        collection = self._get_db_connection()
        query = {}
        if userids is not None:
            query["userid"] = {"$in": userids}
        if date is not None:
            query["date"] = date
        else:
            date_filter = {}
            if start_date is not None:
                date_filter["$gte"] = start_date
            if end_date is not None:
                date_filter["$lte"] = end_date
            if date_filter:
                query["date"] = date_filter

        sort_dir = -1 if sort_desc else 1
        try:
            return list(collection.find(query).sort("date", sort_dir))
        except OperationFailure as e:
            print(f"MongoDB find operation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during get_all_tasks: {e}")
            raise e

    def get_days_summary(self, userid: str, start_date: str | None = None, end_date: str | None = None):
        """
        Aggregates daily task counts, total hours, and incomplete flags for a given user.
        Also returns global incomplete dates across all history for this user.
        """
        collection = self._get_db_connection()
        try:
            match_stage = {"userid": userid}
            date_filter = {}
            if start_date is not None:
                date_filter["$gte"] = start_date
            if end_date is not None:
                date_filter["$lte"] = end_date
            if date_filter:
                match_stage["date"] = date_filter

            pipeline = [
                {"$match": match_stage},
                {"$group": {
                    "_id": "$date",
                    "task_count": {"$sum": 1},
                    "total_expected": {"$sum": {"$ifNull": ["$expected_hours", 0]}},
                    "total_actual": {"$sum": {"$ifNull": ["$actual_hours", 0]}},
                    "incomplete_count": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$or": [
                                        {"$eq": ["$actual_hours", None]},
                                        {"$eq": [{"$type": "$actual_hours"}, "missing"]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    }
                }},
                {"$sort": {"_id": -1}}
            ]

            days = []
            for doc in collection.aggregate(pipeline):
                incomplete_count = doc.get("incomplete_count", 0)
                days.append({
                    "date": doc["_id"],
                    "task_count": doc.get("task_count", 0),
                    "total_expected": round(float(doc.get("total_expected", 0.0)), 2),
                    "total_actual": round(float(doc.get("total_actual", 0.0)), 2),
                    "incomplete_count": incomplete_count,
                    "is_incomplete": bool(incomplete_count > 0)
                })

            # Global incomplete dates for this user across all history
            incomplete_pipeline = [
                {
                    "$match": {
                        "userid": userid,
                        "$or": [
                            {"actual_hours": None},
                            {"actual_hours": {"$exists": False}}
                        ]
                    }
                },
                {"$group": {"_id": "$date"}},
                {"$sort": {"_id": -1}}
            ]
            global_incomplete_dates = [doc["_id"] for doc in collection.aggregate(incomplete_pipeline)]

            return {
                "userid": userid,
                "days": days,
                "total_days": len(days),
                "total_incomplete_days": len(global_incomplete_dates),
                "incomplete_dates": global_incomplete_dates
            }
        except OperationFailure as e:
            print(f"MongoDB aggregation failed: {e}")
            raise e
        except Exception as e:
            print(f"An unexpected error occurred during get_days_summary: {e}")
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

    # --- Session methods for Google OAuth ---
    def create_session(self, session_id: str, userid: str, email: str, name: str = "", google_sub: str = "", state: str = None, nonce: str = None, expires_at = None):
        """Creates or replaces a session document in tmtrack_sessions."""
        collection = self._get_collection('tmtrack_sessions')
        doc = {
            "session_id": session_id,
            "userid": userid,
            "email": email,
            "name": name,
            "google_sub": google_sub,
            "state": state,
            "nonce": nonce,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "expires_at": expires_at
        }
        collection.replace_one({"session_id": session_id}, doc, upsert=True)
        return doc

    def get_session(self, session_id: str):
        """Retrieves a session document by session_id."""
        if not session_id:
            return None
        collection = self._get_collection('tmtrack_sessions')
        return collection.find_one({"session_id": session_id})

    def update_session(self, session_id: str, update_data: dict):
        """Updates fields on an existing session."""
        if not session_id:
            return None
        collection = self._get_collection('tmtrack_sessions')
        return collection.update_one({"session_id": session_id}, {"$set": update_data})

    def delete_session(self, session_id: str):
        """Deletes a session by session_id."""
        if not session_id:
            return None
        collection = self._get_collection('tmtrack_sessions')
        return collection.delete_one({"session_id": session_id})

    def clear_sessions_collection(self):
        """Clears all documents from tmtrack_sessions for testing."""
        collection = self._get_collection('tmtrack_sessions')
        return collection.delete_many({})
