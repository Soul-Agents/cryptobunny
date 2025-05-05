import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pymongo
from pymongo import MongoClient
from bson import ObjectId

from app.models.twitter import TwitterAuth
from app.models.agent import AgentConfig

class JSONEncoder(json.JSONEncoder):
    """JSON encoder that can handle MongoDB ObjectId and datetime objects"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

class TweetDB:
    """Database access class for CryptoBunny application"""
    
    # Class variable for singleton instance
    _instance = None
    
    def __init__(self):
        """Initialize database connection"""
        # Skip initialization if this is a singleton reuse
        if hasattr(self, 'initialized') and self.initialized:
            return
            
        mongo_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017/cryptobunny")
        self.client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            retryWrites=True,
            retryReads=True,
        )
        self.db = self.client["tweets"]
        
        # Collections
        self.twitter_auth = self.db.twitter_auth
        self.agent_config = self.db.agent_config
        self.written_ai_tweets = self.db.written_ai_tweets
        self.written_ai_tweet_replies = self.db.written_ai_tweet_replies

        
        # Mark as initialized
        self.initialized = True
    
    def close(self):
        """Close the database connection"""
        self.client.close()
        self.initialized = False
    
    # --- Twitter Authentication Methods ---
    
    def add_twitter_auth(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add or update Twitter authentication data
        
        Args:
            auth_data: Dictionary containing authentication data
            
        Returns:
            Dictionary with operation result
        """
        # Convert TwitterAuth object to dictionary if necessary
        if isinstance(auth_data, TwitterAuth):
            auth_data = auth_data.to_dict()
        
        # Check if a record already exists for this client
        existing = self.twitter_auth.find_one({"client_id": auth_data["client_id"]})
        
        if existing:
            # Update existing record
            auth_data["updated_at"] = datetime.now(timezone.utc)
            if "created_at" not in auth_data:
                auth_data["created_at"] = existing.get("created_at", datetime.now(timezone.utc))
            
            result = self.twitter_auth.update_one(
                {"client_id": auth_data["client_id"]},
                {"$set": auth_data}
            )
            
            return {
                "status": "success",
                "message": "Twitter authentication updated",
                "modified_count": result.modified_count
            }
        else:
            # Insert new record
            if "created_at" not in auth_data:
                auth_data["created_at"] = datetime.now(timezone.utc)
            if "updated_at" not in auth_data:
                auth_data["updated_at"] = datetime.now(timezone.utc)
            
            result = self.twitter_auth.insert_one(auth_data)
            
            return {
                "status": "success",
                "message": "Twitter authentication added",
                "id": str(result.inserted_id)
            }
    
    def get_twitter_auth(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Twitter authentication data for a client
        
        Args:
            client_id: Client ID to retrieve auth data for
            
        Returns:
            Dictionary with auth data or None if not found
        """
        return self.twitter_auth.find_one({"client_id": client_id})
    
    def delete_twitter_auth(self, client_id: str) -> Dict[str, Any]:
        """
        Delete Twitter authentication data for a client
        
        Args:
            client_id: Client ID to delete auth data for
            
        Returns:
            Dictionary with operation result
        """
        result = self.twitter_auth.delete_one({"client_id": client_id})
        
        return {
            "status": "success",
            "message": f"Twitter authentication deleted for client ID: {client_id}",
            "deleted_count": result.deleted_count
        }
    
    # --- Agent Configuration Methods ---
    
    def add_agent_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add or update agent configuration
        
        Args:
            config_data: Dictionary containing agent configuration
            
        Returns:
            Dictionary with operation result
        """
        # Convert AgentConfig object to dictionary if necessary
        if isinstance(config_data, AgentConfig):
            config_data = config_data.to_dict()
        
        # Create a query to find an existing configuration
        query = {
            "client_id": config_data["client_id"],
        }
        
        # Check if a record already exists for this agent
        existing = self.agent_config.find_one(query)
        
        if existing:
            # Update existing record
            config_data["updated_at"] = datetime.now(timezone.utc)
            if "created_at" not in config_data:
                config_data["created_at"] = existing.get("created_at", datetime.now(timezone.utc))
            
            result = self.agent_config.update_one(
                query,
                {"$set": config_data}
            )
            
            return {
                "status": "success",
                "message": "Agent configuration updated",
                "modified_count": result.modified_count
            }
        else:
            # Insert new record
            if "created_at" not in config_data:
                config_data["created_at"] = datetime.now(timezone.utc)
            if "updated_at" not in config_data:
                config_data["updated_at"] = datetime.now(timezone.utc)
            
            result = self.agent_config.insert_one(config_data)
            
            return {
                "status": "success",
                "message": "Agent configuration added",
                "id": str(result.inserted_id)
            }
    
    def get_agent_config(self, client_id: str, ) -> Optional[Dict[str, Any]]:
        """
        Get agent configuration for a client 
        
        Args:
            client_id: Client ID of the agent owner
            
        Returns:
            Dictionary with agent configuration or None if not found
        """
        return self.agent_config.find_one({
            "client_id": client_id,
        })
    
  
    
    def get_agent_config(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a client's single agent configuration (one user = one agent)
        
        Args:
            client_id: Client ID to retrieve configuration for
            
        Returns:
            Dictionary with agent configuration or None if not found
        """
        return self.agent_config.find_one({"client_id": client_id})
    
    def delete_agent_config(self, client_id: str, agent_name: str) -> Dict[str, Any]:
        """
        Delete agent configuration for a client and agent name
        
        Args:
            client_id: Client ID of the agent owner
            agent_name: Name of the agent
            
        Returns:
            Dictionary with operation result
        """
        result = self.agent_config.delete_one({
            "client_id": client_id,
            "agent_name": agent_name
        })
        
        return {
            "status": "success",
            "message": f"Agent configuration deleted for {agent_name}",
            "deleted_count": result.deleted_count
        }
    
    # --- Tweet Methods ---
    
    def add_written_ai_tweet(self, user_id: str, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a tweet written by an AI agent
        
        Args:
            user_id: Twitter user ID the tweet was posted as
            tweet_data: Dictionary containing tweet data
            
        Returns:
            Dictionary with operation result
        """
        tweet_data["saved_at"] = datetime.now(timezone.utc)
        result = self.written_ai_tweets.insert_one(tweet_data)
        
        return {
            "status": "success",
            "message": "Tweet saved",
            "id": str(result.inserted_id)
        }
    
    def get_last_written_ai_tweets(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent tweets written by an AI agent for a user
        
        Args:
            user_id: Twitter user ID to get tweets for
            limit: Maximum number of tweets to return
            
        Returns:
            List of tweet dictionaries
        """
        return list(
            self.written_ai_tweets.find(
                {"user_id": user_id}
            ).sort("created_at", pymongo.DESCENDING).limit(limit)
        )
    
    def add_written_ai_tweet_reply(self, user_id: str, reply_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a reply written by an AI agent
        
        Args:
            user_id: Twitter user ID the reply was posted as
            reply_data: Dictionary containing reply data
            
        Returns:
            Dictionary with operation result
        """
        reply_data["saved_at"] = datetime.now(timezone.utc)
        result = self.written_ai_tweet_replies.insert_one(reply_data)
        
        return {
            "status": "success",
            "message": "Reply saved",
            "id": str(result.inserted_id)
        }
    
    def get_last_written_ai_tweet_replies(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent replies written by an AI agent for a user
        
        Args:
            user_id: Twitter user ID to get replies for
            limit: Maximum number of replies to return
            
        Returns:
            List of reply dictionaries
        """
        return list(
            self.written_ai_tweet_replies.find(
                {"user_id": user_id}
            ).sort("created_at", pymongo.DESCENDING).limit(limit)
        )
    def get_all_active_paid_agents(self) -> List[Dict[str, Any]]:
        """
        Get all active and paid agent configurations
        
        Returns:
            List of dictionaries containing agent configurations
        """
        result = self.agent_config.find({
            "is_active": True,
            "is_paid": True
        })
        
        return list(result)
# Singleton instance
_db_instance = None



def get_db() -> TweetDB:
    """Get a database instance using singleton pattern"""
    print("Getting db instance")
    global _db_instance
    if _db_instance is None:
        print("Creating new db instance")
        _db_instance = TweetDB()
    return _db_instance

# Add a function to explicitly close the connection when needed
def close_db():
    """Close the database connection when application is shutting down"""
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None 


