from datetime import datetime
import pandas as pd
from pymongo import MongoClient
import json
from bson import json_util
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from db_utils import get_db

# Load environment variables
load_dotenv()

# MongoDB connection details
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "tweets"

def get_mongodb_client():
    """Create a MongoDB client with context manager"""
    try:
        mongodb_uri = os.getenv("MONGODB_URL")
        
        if not mongodb_uri or "railway.internal" in mongodb_uri:
            mongodb_uri = os.getenv("MONGODB_URI")
        
        if not mongodb_uri:
            raise ValueError("No valid MongoDB connection string found")
            
        client = MongoClient(mongodb_uri)
        client.admin.command('ping')
        print("[DB] Successfully connected to MongoDB!")
        return client
    except Exception as e:
        print(f"[DB] Failed to connect to MongoDB: {e}")
        raise

class MongoDBConnection:
    def __init__(self):
        self.client = None
        self.db = None

    def __enter__(self):
        self.client = get_mongodb_client()
        self.db = self.client[DB_NAME]
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
            print("[DB] MongoDB connection closed")

def cleanup_collections(db):
    """Hard delete everything that doesn't match the schema"""
    # Define exact schema fields
    tweet_fields = {
        "tweet_id", "text", "created_at", "author_id", "lang",
        "public_metrics", "conversation_id", "in_reply_to_user_id",
        "in_reply_to_tweet_id", "replied_to", "replied_at"
    }
    
    written_ai_tweet_fields = {
        "tweet_id", "edit_history_tweet_ids", "saved_at", "text",
        "public_metrics", "conversation_id", "in_reply_to_user_id",
        "replied_to", "replied_at"
    }
    
    written_ai_tweet_reply_fields = {
        "tweet_id", "reply", "public_metrics", "conversation_id",
        "in_reply_to_user_id", "saved_at"
    }
    
    ai_mention_tweet_fields = {
        "tweet_id", "text", "created_at", "replied_to", "replied_at"
    }
    
    try:
        # Clean up tweets collection
        result_tweets = db.tweets.delete_many({
            "$or": [
                {"tweet_id": {"$exists": False}},
                {"text": {"$exists": False}},
                {"created_at": {"$exists": False}},
                {"author_id": {"$exists": False}}
            ]
        })
        print(f"[DB] Cleaned up {result_tweets.deleted_count} non-compliant tweets")
        
        # Clean up written_ai_tweets collection
        result_ai_tweets = db.written_ai_tweets.delete_many({
            "$or": [
                {"tweet_id": {"$exists": False}},
                {"text": {"$exists": False}},
                {"saved_at": {"$exists": False}}
            ]
        })
        print(f"[DB] Cleaned up {result_ai_tweets.deleted_count} non-compliant AI tweets")
        
        # Clean up written_ai_tweets_replies collection
        result_replies = db.written_ai_tweets_replies.delete_many({
            "$or": [
                {"tweet_id": {"$exists": False}},
                {"reply": {"$exists": False}}
            ]
        })
        print(f"[DB] Cleaned up {result_replies.deleted_count} non-compliant AI tweet replies")
        
        # Clean up ai_mention_tweets collection
        result_mentions = db.ai_mention_tweets.delete_many({
            "$or": [
                {"tweet_id": {"$exists": False}},
                {"replied_to": {"$exists": False}}
            ]
        })
        print(f"[DB] Cleaned up {result_mentions.deleted_count} non-compliant mentions")
        
        print("[DB] Successfully cleaned up all collections!")
        
    except Exception as e:
        print(f"[DB] Error during cleanup: {e}")
        raise

def delete_existing_mentions(db):
    """Delete all existing mentions and related data for safety"""
    try:
        # Delete all mentions
        result_mentions = db.ai_mention_tweets.delete_many({})
        print(f"[DB] Deleted {result_mentions.deleted_count} mentions")
        
        # Delete all tweets that are mentions or replies
        result_tweets = db.tweets.delete_many({
            "$or": [
                {"in_reply_to_user_id": {"$exists": True}},
                {"in_reply_to_tweet_id": {"$exists": True}},
                {"replied_to": True}
            ]
        })
        print(f"[DB] Deleted {result_tweets.deleted_count} related tweets")
        
        # Delete all written AI tweet replies
        result_replies = db.written_ai_tweets_replies.delete_many({})
        print(f"[DB] Deleted {result_replies.deleted_count} AI tweet replies")
        
        print("[DB] Successfully cleared all mentions and related data!")
        
    except Exception as e:
        print(f"[DB] Error during mention deletion: {e}")
        raise

def print_collection_stats(db):
    """Print statistics about each collection"""
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
                
                fields = list(sample.keys())
                print(f"\nFields: {', '.join(fields)}")
                print("-" * 50)
        except Exception as e:
            print(f"Error analyzing {collection_name}: {e}")

def backup_database(db):
    """Create a backup of the database before cleanup"""
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(export_dir, f"backup_before_cleanup_{timestamp}.json")
        
        all_data = {}
        for collection in db.list_collection_names():
            all_data[collection] = json.loads(json_util.dumps(list(db[collection].find())))
        
        with open(filename, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"[DB] Backup created at: {filename}")
        return filename
    except Exception as e:
        print(f"[DB] Error creating backup: {e}")
        raise

def clean_mentions():
    try:
        with get_db() as db:
            # Drop the entire mentions collection
            
            # Or alternatively, remove just the empty mentions:
            result = db.ai_mention_tweets.delete_many({"text": {"$exists": False}})
            print(f"Removed {result.deleted_count} empty mentions")
            
    except Exception as e:
        print(f"Error cleaning mentions: {str(e)}")

if __name__ == "__main__":
    try:
        print("[ADMIN MODE] Starting database cleanup operation...")
        
        with MongoDBConnection() as db:
            # Create backup first
            backup_file = backup_database(db)
            print(f"Backup created successfully at: {backup_file}")
            
            # Print initial stats
            print("\nInitial database state:")
            print_collection_stats(db)
            
            # Commenting out the deletion of mentions for safety
            # print("\nDeleting existing mentions and related data...")
            # delete_existing_mentions(db)
            
            # Perform schema cleanup
            print("\nPerforming schema cleanup...")
            cleanup_collections(db)
            
            # Print final stats
            print("\nFinal database state:")
            print_collection_stats(db)
            
            print("\nOperation completed successfully!")
        
    except Exception as e:
        print(f"Operation failed: {e}")
