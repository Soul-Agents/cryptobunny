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

def cleanup_collections():
    """Clean up collections to match the schema exactly using bulk operations"""
    db = connect_to_mongodb()
    
    # Define allowed fields based on schemas
    base_fields = {"tweet_id", "text", "created_at", "author_id"}
    
    tweet_fields = base_fields | {
        "user", "user_id", "conversation_id", "in_reply_to_user_id", 
        "in_reply_to_tweet_id", "likes", "replies", "retweets", "quotes",
        "replied_to", "replied_at"
    }
    
    written_ai_tweet_fields = base_fields | {
        "saved_at", "edit_history_tweet_ids", "likes", "replies", 
        "retweets", "quotes", "prompt", "model", "temperature", 
        "max_tokens", "response_tweet_id"
    }
    
    reply_fields = {
        "reply_id", "text", "created_at", "author_id", "in_reply_to_tweet_id"
    }
    
    try:
        # Clean up tweets collection using bulk operations
        bulk_tweets = db.tweets.initialize_unordered_bulk_op()
        for doc in db.tweets.find():
            cleaned_doc = {k: v for k, v in doc.items() if k in tweet_fields}
            bulk_tweets.find({"_id": doc["_id"]}).replace_one(cleaned_doc)
        bulk_tweets.execute()
        
        # Clean up written_ai_tweets collection using bulk operations
        bulk_written_ai_tweets = db.written_ai_tweets.initialize_unordered_bulk_op()
        for doc in db.written_ai_tweets.find():
            cleaned_doc = {k: v for k, v in doc.items() if k in written_ai_tweet_fields}
            bulk_written_ai_tweets.find({"_id": doc["_id"]}).replace_one(cleaned_doc)
        bulk_written_ai_tweets.execute()
        
        # Clean up written_ai_tweets_replies collection using bulk operations
        bulk_replies = db.written_ai_tweets_replies.initialize_unordered_bulk_op()
        for doc in db.written_ai_tweets_replies.find():
            cleaned_doc = {k: v for k, v in doc.items() if k in reply_fields}
            bulk_replies.find({"_id": doc["_id"]}).replace_one(cleaned_doc)
        bulk_replies.execute()
        
        print("Successfully cleaned up collections to match schema!")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")

def backup_and_cleanup():
    """Backup data, cleanup, and export final state"""
    print("Starting database backup and cleanup...")
    
    try:
        # 1. First backup everything
        print("\nCreating backup...")
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = os.path.join(export_dir, f"backup_before_cleanup_{backup_timestamp}.json")
        
        data = get_all_collections_data()
        with open(backup_filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Backup created at: {backup_filename}")
        
        # 2. Perform cleanup
        print("\nPerforming cleanup...")
        cleanup_collections()
        
        # 3. Export final state
        print("\nExporting final state...")
        final_filename = os.path.join(export_dir, f"final_state_{backup_timestamp}.json")
        data = get_all_collections_data()
        with open(final_filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Final state exported to: {final_filename}")
        
        print("\nOperation completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nOperation failed: {e}")
        return False

if __name__ == "__main__":
    backup_and_cleanup()
