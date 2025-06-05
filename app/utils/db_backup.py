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
    
    def __init__(self):
        """Initialize database connection"""
        self.initialized = False
        self.connect()
    
    def connect(self):
        """Establish database connection"""
        if not self.initialized:
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
            self.rate_limits = self.db.rate_limits
            self.tweets = self.db.tweets

            # Create indexes for rate_limits collection
            self.rate_limits.create_index([("client_id", pymongo.ASCENDING)], unique=True)
            self.rate_limits.create_index([("cached_until", pymongo.ASCENDING)])
            
            # Create indexes for written_ai_tweet_replies collection to support approval workflow
            self.written_ai_tweet_replies.create_index([("client_id", pymongo.ASCENDING)])
            self.written_ai_tweet_replies.create_index([("status", pymongo.ASCENDING)])
            self.written_ai_tweet_replies.create_index([("created_at", pymongo.DESCENDING)])
            
            self.initialized = True
    
    def ensure_connected(self):
        """Ensure database connection is active"""
        if not self.initialized:
            self.connect()
        try:
            # Ping the database to check connection
            self.client.admin.command('ping')
        except:
            self.initialized = False
            self.connect()
    
    def close(self):
        """Close the database connection"""
        if self.initialized:
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
    
    def delete_agent_config(self, client_id: str) -> Dict[str, Any]:
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
        })
        
        return {
            "status": "success",
            "message": f"Agent configuration deleted for {client_id}",
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
        """Get the most recent AI-written tweet replies for a user"""
        return list(
            self.written_ai_tweet_replies
            .find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
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

    # --- Rate Limits Methods ---
    
    def get_rate_limits(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get rate limits for a client
        
        Args:
            client_id: Client ID to retrieve rate limits for
            
        Returns:
            Dictionary with rate limits or None if not found
        """
        return self.rate_limits.find_one({"client_id": client_id})
    
    def update_rate_limits(self, client_id: str, rate_limits: Dict[str, Any], cached_until: datetime) -> Dict[str, Any]:
        """
        Update rate limits for a client
        
        Args:
            client_id: Client ID to update rate limits for
            rate_limits: Dictionary containing rate limit data
            cached_until: Datetime when cache expires
            
        Returns:
            Dictionary with operation result
        """
        now = datetime.now(timezone.utc)
        
        update_data = {
            "client_id": client_id,
            "rate_limits": rate_limits,
            "last_checked": now,
            "cached_until": cached_until,
            "has_rate_limit_error": False,
            "updated_at": now
        }
        
        result = self.rate_limits.update_one(
            {"client_id": client_id},
            {"$set": update_data},
            upsert=True
        )
        
        return {
            "status": "success",
            "message": "Rate limits updated",
            "modified_count": result.modified_count if result.matched_count > 0 else 0,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None
        }
    
    def mark_rate_limit_error(self, client_id: str, reset_time: datetime) -> Dict[str, Any]:
        """
        Mark a client as rate limited
        
        Args:
            client_id: Client ID to mark as rate limited
            reset_time: When the rate limit will reset
            
        Returns:
            Dictionary with operation result
        """
        result = self.rate_limits.update_one(
            {"client_id": client_id},
            {
                "$set": {
                    "has_rate_limit_error": True,
                    "rate_limit_reset": reset_time,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        return {
            "status": "success",
            "message": "Rate limit error marked",
            "modified_count": result.modified_count
        }

    # --- Reply Approval Workflow Methods ---
    
    def add_reply_proposal(self, client_id: str, user_id: str, tweet_id: str, tweet_text: str, proposed_reply: str) -> Dict[str, Any]:
        """
        Add a reply proposal for manual approval
        
        Args:
            client_id: Client ID of the agent
            user_id: Twitter user ID 
            tweet_id: ID of the tweet to reply to
            tweet_text: Text content of the original tweet
            proposed_reply: The AI-generated reply text
            
        Returns:
            Dictionary with operation result
        """
        reply_data = {
            "client_id": client_id,
            "user_id": user_id,
            "tweet_id": tweet_id,  # This will be the original tweet ID until posted
            "original_tweet_id": tweet_id,  # Store the original tweet ID
            "original_tweet_text": tweet_text,
            "reply": {"reply": proposed_reply},
            "proposed_reply": proposed_reply,  # Store for easy access
            "status": "pending",  # pending, approved, rejected, posted
            "public_metrics": {},
            "conversation_id": None,
            "in_reply_to_user_id": None,
            "saved_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "approved_at": None,
            "posted_at": None,
            "posted_tweet_id": None  # Will store the actual reply tweet ID when posted
        }
        
        result = self.written_ai_tweet_replies.insert_one(reply_data)
        
        return {
            "status": "success",
            "message": "Reply proposal saved for approval",
            "id": str(result.inserted_id),
            "reply_data": reply_data
        }
    
    def get_pending_replies(self, client_id: str, status: str = "pending") -> List[Dict[str, Any]]:
        """
        Get pending replies for a client
        
        Args:
            client_id: Client ID to get pending replies for
            status: Status filter (pending, approved, rejected, posted)
            
        Returns:
            List of pending reply dictionaries
        """
        query = {"client_id": client_id}
        if status:
            query["status"] = status
            
        return list(
            self.written_ai_tweet_replies.find(query).sort("created_at", pymongo.DESCENDING)
        )
    
    def update_reply_status(self, reply_id: str, status: str) -> Dict[str, Any]:
        """
        Update the status of a pending reply
        
        Args:
            reply_id: ID of the pending reply
            status: New status (approved, rejected, posted)
            
        Returns:
            Dictionary with operation result
        """
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if status == "approved":
            update_data["approved_at"] = datetime.now(timezone.utc)
        elif status == "posted":
            update_data["posted_at"] = datetime.now(timezone.utc)
        
        result = self.written_ai_tweet_replies.update_one(
            {"_id": ObjectId(reply_id)},
            {"$set": update_data}
        )
        
        return {
            "status": "success" if result.modified_count > 0 else "error",
            "message": f"Reply status updated to {status}" if result.modified_count > 0 else "Reply not found",
            "modified_count": result.modified_count
        }
    
    def get_reply_by_id(self, reply_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific reply by ID
        
        Args:
            reply_id: ID of the reply
            
        Returns:
            Dictionary with reply data or None if not found
        """
        try:
            return self.written_ai_tweet_replies.find_one({"_id": ObjectId(reply_id)})
        except Exception as e:
            print(f"Error getting reply: {e}")
            return None
    def get_unreplied_tweets(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get unreplied tweets for a user
        """
        return list(self.tweets.find({"user_id": user_id, "in_reply_to_user_id": None}).limit(10))
    
    def mark_reply_as_posted(self, reply_id: str, posted_tweet_id: str) -> Dict[str, Any]:
        """
        Mark a reply as posted and store the actual tweet ID
        
        Args:
            reply_id: ID of the reply proposal
            posted_tweet_id: The actual tweet ID from Twitter after posting
            
        Returns:
            Dictionary with operation result
        """
        update_data = {
            "status": "posted",
            "posted_at": datetime.now(timezone.utc),
            "posted_tweet_id": posted_tweet_id,
            "tweet_id": posted_tweet_id,  # Update the main tweet_id field
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = self.written_ai_tweet_replies.update_one(
            {"_id": ObjectId(reply_id)},
            {"$set": update_data}
        )
        
        return {
            "status": "success" if result.modified_count > 0 else "error",
            "message": f"Reply marked as posted" if result.modified_count > 0 else "Reply not found",
            "modified_count": result.modified_count
        }

# Singleton instance
_db_instance = None



def get_db() -> TweetDB:
    """Get a database instance using singleton pattern"""
    global _db_instance
    if _db_instance is None or not _db_instance.initialized:
        _db_instance = TweetDB()
    return _db_instance

def close_db():
    """Close the database connection when application is shutting down"""
    global _db_instance
    if _db_instance is not None and _db_instance.initialized:
        _db_instance.close()
        _db_instance = None


