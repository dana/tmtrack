import argparse
import json
import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId

# The collections that are essential for the REST API server.
COLLECTIONS_TO_RESTORE = ['categories', 'daily_tasks']

def restore_database(mongo_url, db_name, input_file):
    """
    Connects to the MongoDB database and restores data from a backup file.
    This is a destructive operation: it clears the collections before loading.
    """
    print(f"Starting restore for database '{db_name}' at '{mongo_url}' from file '{input_file}'...")
    
    # Read the backup data first to ensure the file is valid before touching the database
    try:
        with open(input_file, 'r') as f:
            backup_data = json.load(f)
        print("Successfully read backup file.")
    except FileNotFoundError:
        print(f"ERROR: Backup file not found at '{input_file}'. Aborting.")
        return
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse backup file. It may be corrupted. Reason: {e}. Aborting.")
        return
    except IOError as e:
        print(f"ERROR: Could not read backup file '{input_file}'. Reason: {e}. Aborting.")
        return

    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        # Test the connection
        client.admin.command('ping')
        db = client[db_name]
        
        for collection_name in COLLECTIONS_TO_RESTORE:
            if collection_name not in backup_data:
                print(f"  - WARNING: Collection '{collection_name}' not found in backup file. Skipping.")
                continue

            print(f"  - Processing collection '{collection_name}'...")
            
            try:
                collection = db[collection_name]
                
                # Destructively clear the collection
                print(f"    > Clearing all documents from '{collection_name}'...")
                delete_result = collection.delete_many({})
                print(f"    > {delete_result.deleted_count} documents cleared.")
                
                # Insert the documents from the backup
                documents_to_insert = backup_data[collection_name]
                
                if not documents_to_insert:
                    print("    > No documents to insert for this collection.")
                    continue
                    
                # Convert string '_id' back to ObjectId and date strings to datetime objects
                for doc in documents_to_insert:
                    if '_id' in doc:
                        doc['_id'] = ObjectId(doc['_id'])
                    
                    # Specifically for daily_tasks, convert known date fields
                    if collection_name == 'daily_tasks':
                        for field in ['created_at', 'updated_at']:
                            if field in doc and isinstance(doc[field], str):
                                try:
                                    # Handle different ISO format variations
                                    if '.' in doc[field]:
                                        # Format with microseconds
                                        doc[field] = datetime.datetime.strptime(doc[field], '%Y-%m-%d %H:%M:%S.%f')
                                    else:
                                        # Format without microseconds
                                        doc[field] = datetime.datetime.strptime(doc[field], '%Y-%m-%d %H:%M:%S')
                                except (ValueError, TypeError):
                                    print(f"    > WARNING: Could not parse date string for field '{field}'. Leaving as string.")

                print(f"    > Inserting {len(documents_to_insert)} documents...")
                collection.insert_many(documents_to_insert)
                print("    > Insertion successful.")

            except OperationFailure as e:
                print(f"    > ERROR: An operation failed on collection '{collection_name}'. Skipping. Reason: {e}")
            except Exception as e:
                print(f"    > ERROR: An unexpected error occurred with collection '{collection_name}'. Skipping. Reason: {e}")

        print("\nDatabase restore process completed.")

    except ConnectionFailure as e:
        print(f"ERROR: Could not connect to MongoDB at '{mongo_url}'. Please check the URL and ensure the server is running. Reason: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if 'client' in locals() and client:
            client.close()
            print("Connection to MongoDB closed.")

def main():
    parser = argparse.ArgumentParser(
        description="Restore tool for the tmtrack MongoDB database.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "mongo_url",
        help="The connection URL for the MongoDB instance to restore into (e.g., 'mongodb://localhost:27017/')."
    )
    parser.add_argument(
        "db_name",
        help="The name of the database to restore into (e.g., 'tmtrack_db')."
    )
    parser.add_argument(
        "input_file",
        nargs='?',
        default="tmtrack_backup.json",
        help="The optional path to the input backup file (default: tmtrack_backup.json)."
    )
    
    args = parser.parse_args()
    
    # Add a confirmation step because this is a destructive operation
    confirm = input(f"This will destructively restore to database '{args.db_name}'.\n"
                    f"All data in the '{', '.join(COLLECTIONS_TO_RESTORE)}' collections will be DELETED.\n"
                    "Are you sure you want to continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        restore_database(args.mongo_url, args.db_name, args.input_file)
    else:
        print("Restore operation cancelled by user.")

if __name__ == "__main__":
    main()
