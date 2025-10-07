
import argparse
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# The collections that are essential for the REST API server.
COLLECTIONS_TO_BACKUP = ['categories', 'daily_tasks']

def backup_database(mongo_url, db_name, output_file):
    """
    Connects to the MongoDB database and dumps the specified collections to a file.
    """
    print(f"Starting backup for database '{db_name}' from '{mongo_url}'...")
    
    try:
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        # Test the connection
        client.admin.command('ping')
        db = client[db_name]
        
        backup_data = {}
        
        for collection_name in COLLECTIONS_TO_BACKUP:
            print(f"  - Backing up collection '{collection_name}'...")
            try:
                collection = db[collection_name]
                documents = list(collection.find({}))
                
                # Convert ObjectId to string for JSON serialization
                for doc in documents:
                    if '_id' in doc:
                        doc['_id'] = str(doc['_id'])
                        
                backup_data[collection_name] = documents
                print(f"    > Found {len(documents)} documents.")
                
            except OperationFailure as e:
                print(f"    > ERROR: Could not access collection '{collection_name}'. Skipping. Reason: {e}")
            except Exception as e:
                print(f"    > ERROR: An unexpected error occurred with collection '{collection_name}'. Skipping. Reason: {e}")

        # Write the backup data to the output file
        try:
            with open(output_file, 'w') as f:
                json.dump(backup_data, f, indent=4, default=str)
            print(f"\nSuccessfully wrote backup to '{output_file}'")
            
        except IOError as e:
            print(f"\nERROR: Could not write to output file '{output_file}'. Reason: {e}")

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
        description="Backup tool for the tmtrack MongoDB database.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "mongo_url",
        help="The connection URL for the MongoDB instance (e.g., 'mongodb://localhost:27017/')."
    )
    parser.add_argument(
        "db_name",
        help="The name of the database to back up (e.g., 'tmtrack_db')."
    )
    parser.add_argument(
        "output_file",
        nargs='?',
        default="tmtrack_backup.json",
        help="The optional path to the output backup file (default: tmtrack_backup.json)."
    )
    
    args = parser.parse_args()
    
    backup_database(args.mongo_url, args.db_name, args.output_file)

if __name__ == "__main__":
    main()
