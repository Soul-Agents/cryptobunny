from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import json
from bson import json_util
from typing import List, Dict, Any
import os

# MongoDB connection details
MONGODB_URL = os.getenv("MONGODB_URL")  # Try MONGODB_URL first
MONGODB_URI = os.getenv("MONGODB_URI")  # Fallback to MONGODB_URI
DB_NAME = "tweets"  # Changed from "twitter_bot"

def connect_to_mongodb():
    """Create a MongoDB client and return database connection"""
    try:
        # Try to get the public MongoDB URL first
        mongodb_uri = MONGODB_URL
        
        if not mongodb_uri or "railway.internal" in mongodb_uri:
            # Fallback to MONGODB_URI if URL contains internal references
            mongodb_uri = MONGODB_URI
        
        if not mongodb_uri:
            raise ValueError("No valid MongoDB connection string found")
            
        client = MongoClient(mongodb_uri)
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        return client[DB_NAME]
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise

def get_all_collections_data() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch all data from all collections"""
    db = connect_to_mongodb()
    collections = db.list_collection_names()
    
    print(f"\nFound {len(collections)} collections: {', '.join(collections)}")
    
    all_data = {}
    for collection_name in collections:
        try:
            collection_data = list(db[collection_name].find())
            # Convert ObjectId to string for JSON serialization
            collection_data = json.loads(json_util.dumps(collection_data))
            all_data[collection_name] = collection_data
            print(f"Retrieved {len(collection_data)} documents from {collection_name}")
        except Exception as e:
            print(f"Error retrieving data from {collection_name}: {e}")
    
    return all_data

def export_to_csv():
    """Export all collections to separate CSV files"""
    data = get_all_collections_data()
    export_dir = "exports"
    
    # Create exports directory if it doesn't exist
    os.makedirs(export_dir, exist_ok=True)
    
    for collection_name, collection_data in data.items():
        if collection_data:  # Only create CSV if there's data
            try:
                df = pd.DataFrame(collection_data)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = os.path.join(export_dir, f"export_{collection_name}_{timestamp}.csv")
                df.to_csv(filename, index=False)
                print(f"Exported {len(collection_data)} records from {collection_name} to {filename}")
            except Exception as e:
                print(f"Error exporting {collection_name} to CSV: {e}")

def export_to_json():
    """Export all collections to a single JSON file"""
    data = get_all_collections_data()
    export_dir = "exports"
    
    # Create exports directory if it doesn't exist
    os.makedirs(export_dir, exist_ok=True)
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(export_dir, f"export_all_{timestamp}.json")
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Exported all collections to {filename}")
    except Exception as e:
        print(f"Error exporting to JSON: {e}")

def print_collection_stats():
    """Print statistics about each collection"""
    db = connect_to_mongodb()
    collections = db.list_collection_names()
    
    print("\nDatabase Statistics:")
    print("-" * 50)
    
    for collection_name in collections:
        try:
            count = db[collection_name].count_documents({})
            print(f"\n{collection_name}: {count} documents")
            
            if count > 0:
                sample = db[collection_name].find_one()
                print("\nSample document structure:")
                formatted_sample = json.dumps(json.loads(json_util.dumps(sample)), indent=2)
                print(formatted_sample)
                
                # Print field names for easier reference
                fields = list(sample.keys())
                print(f"\nFields: {', '.join(fields)}")
                print("-" * 50)
        except Exception as e:
            print(f"Error analyzing {collection_name}: {e}")

if __name__ == "__main__":
    print("Starting database export...")
    
    try:
        # Print collection statistics
        print_collection_stats()
        
        # Export to both CSV and JSON
        export_to_csv()
        export_to_json()
        
        print("\nExport completed successfully!")
    except Exception as e:
        print(f"\nExport failed: {e}")
