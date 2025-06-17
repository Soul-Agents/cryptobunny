from pymongo import MongoClient
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

from schemas import (
    ReplyToAITweet,
    Tweet,
    WrittenAITweet,
    WrittenAITweetReply,
    PublicMetrics,
    TwitterAuth,
    AgentConfig,
)

# Load environment variables from .env file
load_dotenv()

# Get MongoDB connection strings from environment
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_URI = os.getenv("MONGODB_URI")


class TweetDB:
    def __init__(self):
        # Change update threshold to 2 hours
        self.update_threshold = timedelta(hours=6)

        # Try to get the public MongoDB URL first
        mongodb_uri = os.getenv("MONGODB_URL")  # Try MONGODB_URL first

        if not mongodb_uri or "railway.internal" in mongodb_uri:
            # Fallback to MONGODB_URI if URL contains internal references
            mongodb_uri = os.getenv("MONGODB_URI")

        print("Attempting database connection...")
        print(
            f"Using connection string: {mongodb_uri[:20]}..."
        )  # Only show start of URI for security

        if not mongodb_uri:
            raise ValueError(
                "No valid MongoDB connection string found in environment variables"
            )

        try:
            # Initialize MongoDB connection with different timeout settings
            self.client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                retryWrites=True,
                retryReads=True,
            )

            # Test connection
            self.client.admin.command("ping")
            print("[DB] Successfully connected to MongoDB!")

            # Initialize collections with explicit database name
            self.db = self.client["tweets"]  # Specify database name explicitly
            self.users = self.db.users  # Add users collection
            self.tweets = self.db.tweets
            self.written_ai_tweets = self.db.written_ai_tweets
            self.written_ai_tweets_replies = self.db.written_ai_tweets_replies
            self.ai_mention_tweets = self.db.ai_mention_tweets
            self.reply_proposals = self.db.reply_proposals
            # Add new collections for Twitter auth and agent configuration
            self.twitter_auth = self.db.twitter_auth
            self.agent_config = self.db.agent_config
            self.rate_limits = self.db.rate_limits

            # Create index
            self.tweets.create_index("tweet_id", unique=True)
            self.ai_mention_tweets.create_index("tweet_id", unique=True)
            self.written_ai_tweets.create_index("tweet_id", unique=True)
            self.written_ai_tweets_replies.create_index("tweet_id", unique=True)

            # Create compound indexes with user_id
            self.tweets.create_index([("user_id", 1), ("tweet_id", 1)], unique=True)
            self.ai_mention_tweets.create_index(
                [("user_id", 1), ("tweet_id", 1)], unique=True
            )
            self.written_ai_tweets.create_index(
                [("user_id", 1), ("tweet_id", 1)], unique=True
            )
            self.written_ai_tweets_replies.create_index(
                [("user_id", 1), ("tweet_id", 1)], unique=True
            )
            
            # Add indexes for new collections
            self.twitter_auth.create_index("client_id", unique=True)
            self.twitter_auth.create_index("user_id", unique=True)
            self.agent_config.create_index([("client_id", 1), ("agent_name", 1)], unique=True)

        except Exception as e:
            print(f"[DB] Failed to connect to MongoDB: {e}")
            print(
                f"[DB] Connection string used: {mongodb_uri[:20]}..."
            )  # Show partial URI
            raise
        
    def get_api_limits(self, client_id: str) -> Dict:
        """Get the API limits for a client"""
        return self.rate_limits.find_one({"client_id": client_id})
    
    def add_reply_proposal(self, client_id: str, user_id: str, tweet_id: str, tweet_text: str, proposed_reply: str) -> Dict:
        """
        Add a reply proposal to the database
        """
        try:
            self.reply_proposals.insert_one({
                "client_id": client_id, 
                "user_id": user_id,
                "tweet_id": tweet_id,
                "tweet_text": tweet_text,
                "proposed_reply": proposed_reply,
                "status": "pending",
                "created_at": datetime.now(timezone.utc),   
            })
            return {"status": "Success"}
        except Exception as e:
            print(f"[DB] Error adding reply proposal: {e}")
            return {"status": "Error", "message": str(e)}

    def get_last_written_ai_tweets(
        self, user_id: str, limit: int = 21
    ) -> List[WrittenAITweet]:
        """Get the last N tweets written by AI"""
        try:
            return list(
                self.written_ai_tweets.find({"user_id": user_id})
                .sort("saved_at", -1)
                .limit(limit)
            )
        except Exception as e:
            print(f"Error fetching last written AI tweets: {e}")
            return []

    def get_last_written_ai_tweet_replies(
        self, user_id: str, limit: int = 21
    ) -> List[WrittenAITweetReply]:
        """Get the last N replies written by AI"""
        try:
            return list(
                self.written_ai_tweets_replies.find({"user_id": user_id})
                .sort("saved_at", -1)
                .limit(limit)
            )
        except Exception as e:
            print(f"Error fetching last written AI tweet replies: {e}")
            return []
        

    def check_if_tweet_replied_by_agent(self, user_id: str, tweet_id: str) -> bool:
        """Check if a tweet has been replied to by the agent"""
        return self.written_ai_tweets_replies.find_one({"user_id": user_id, "tweet_id": tweet_id}) is not None
    
    def add_written_ai_tweet_reply(
        self, user_id: str, original_tweet_id: str, reply: str
    ) -> Dict:
        """
        Add a reply to an AI tweet to the database and mark the original tweet as replied

        Args:
            user_id (str): The ID of the user making the reply
            original_tweet_id (str): The ID of the tweet being replied to
            reply (str): The content of the reply

        Returns:
            Dict: The result of the database operation
        """
        try:
            reply_data = WrittenAITweetReply(
                user_id=user_id,
                tweet_id=original_tweet_id,
                reply={"reply": reply},
                public_metrics={},
                conversation_id=None,
                in_reply_to_user_id=None,
                saved_at=datetime.now(timezone.utc),
            )

            # Add the reply
            self.written_ai_tweets_replies.update_one(
                {
                    "user_id": user_id,
                    "tweet_id": original_tweet_id,
                },
                {"$set": reply_data},
                upsert=True,
            )

            # Mark the original tweet as replied in both collections
            current_time = datetime.now(timezone.utc)

            # Update in tweets collection
            self.tweets.update_one(
                {"user_id": user_id, "tweet_id": original_tweet_id},
                {
                    "$set": {
                        "replied_to": True,
                        "replied_at": current_time,
                    }
                },
            )

            # Update in mentions collection
            self.ai_mention_tweets.update_one(
                {"user_id": user_id, "tweet_id": original_tweet_id},
                {
                    "$set": {
                        "replied_to": True,
                        "replied_at": current_time,
                    }
                },
            )

            return {"status": "Success"}
        except Exception as e:
            print(f"[DB] Error adding written AI tweet reply: {e}")
            return {"status": "Error", "message": str(e)}

    def add_replies_to_ai_tweet(
        self, original_tweet_id: str, replies: List[Dict]
    ) -> Dict:
        """Add replies array to an AI tweet document"""
        try:
            # Replies are already formatted by Twitter API, just need to convert to our schema
            formatted_replies = [ReplyToAITweet(**reply) for reply in replies]

            self.written_ai_tweets.update_one(
                {"tweet_id": original_tweet_id},
                {"$set": {"replies": formatted_replies}},
                upsert=True,
            )
            return {"status": "Success", "replies_added": len(formatted_replies)}

        except Exception as e:
            print(f"Error adding replies: {e}")
            return {"status": "Error", "message": str(e)}

    def get_replies_to_tweet(self, tweet_id: str) -> List[Dict]:
        """
        Get all replies for a specific AI tweet

        Args:
            tweet_id (str): The ID of the original AI tweet

        Returns:
            List[Dict]: List of replies to the tweet
        """
        try:
            replies = self.replies_to_ai_tweets.find({"tweet_id": tweet_id}).sort(
                "created_at", -1
            )
            return list(replies)
        except Exception as e:
            print(f"Error fetching replies: {e}")
            return []

    def add_tweets(self, user_id: str, tweets: List[Dict]) -> Dict:
        """Add multiple tweets to the database for a specific user"""
        if not tweets:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for tweet_data in tweets:
            try:
                tweet = Tweet(
                    user_id=user_id,  # Add user_id
                    tweet_id=str(tweet_data.get("id") or tweet_data.get("tweet_id")),
                    text=tweet_data.get("text", ""),
                    created_at=tweet_data.get("created_at", datetime.now(timezone.utc)),
                    author_id=str(tweet_data.get("author_id", "")),
                    public_metrics=PublicMetrics(
                        retweet_count=tweet_data.get("public_metrics", {}).get(
                            "retweet_count", 0
                        ),
                        reply_count=tweet_data.get("public_metrics", {}).get(
                            "reply_count", 0
                        ),
                        like_count=tweet_data.get("public_metrics", {}).get(
                            "like_count", 0
                        ),
                        quote_count=tweet_data.get("public_metrics", {}).get(
                            "quote_count", 0
                        ),
                    ),
                    conversation_id=tweet_data.get("conversation_id"),
                    in_reply_to_user_id=tweet_data.get("in_reply_to_user_id"),
                    in_reply_to_tweet_id=tweet_data.get(
                        "in_reply_to_tweet_id", tweet_data.get("referenced_tweet_id")
                    ),
                    replied_to=tweet_data.get("replied_to", False),
                    replied_at=tweet_data.get("replied_at"),
                )

                if not tweet["tweet_id"] or not tweet["text"]:
                    print(f"Skipping invalid tweet: {tweet_data}")
                    results["errors"] += 1
                    continue

                self.tweets.update_one(
                    {"user_id": user_id, "tweet_id": tweet["tweet_id"]},
                    {"$set": tweet},
                    upsert=True,
                )
                results["added"] += 1

            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    results["duplicates"] += 1
                else:
                    results["errors"] += 1
                    print(f"Error adding tweet: {e}")
                    print(f"Problematic tweet data: {tweet_data}")

        return results

    def add_written_ai_tweet(self, user_id: str, tweet: WrittenAITweet) -> Dict:
        """Add a single written AI tweet to the database"""
        print(f"Adding written AI tweet by user {user_id}")
        try:
            tweet["user_id"] = user_id  # Ensure user_id is set
            self.written_ai_tweets.update_one(
                {"user_id": user_id, "tweet_id": tweet["tweet_id"]},
                {"$set": tweet},
                upsert=True,
            )
            return {"status": "Success", "added": 1}
        except Exception as e:
            print(f"[DB] Error adding written tweet: {e}")
            return {"status": "Error", "message": str(e)}

    def get_all_tweets(
        self, user_id: str, limit: int = None, offset: int = 0
    ) -> List[Tweet]:
        """
        Retrieve all tweets for a specific user with optional pagination

        Args:
            user_id (str): The user ID to fetch tweets for
            limit (int, optional): Maximum number of tweets to return
            offset (int): Number of tweets to skip

        Returns:
            List[Dict]: List of tweet documents
        """
        try:
            cursor = (
                self.tweets.find({"user_id": user_id})
                .sort("created_at", -1)
                .skip(offset)
            )

            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            print(f"Error fetching tweets: {e}")
            return []

    def get_most_recent_tweet_id(self, user_id: str) -> str | None:
        """
        Get the ID of the most recent tweet for a specific user

        Args:
            user_id (str): The user ID to get the most recent tweet for

        Returns:
            str | None: The most recent tweet ID or None if no tweets exist
        """
        try:
            most_recent = self.tweets.find_one(
                {"user_id": user_id}, sort=[("created_at", -1)]
            )
            print(f"Most recent tweet: {most_recent}")
            return most_recent["tweet_id"] if most_recent else None
        except Exception as e:
            print(f"Error fetching most recent tweet ID: {e}")
            return None

    def add_ai_tweet(self, user_id: str, tweet: Dict) -> Dict:
        """
        Add a single AI-generated tweet to the database

        Args:
            user_id (str): The user ID who owns this tweet
            tweet (Dict): Tweet dictionary containing tweet_id, text, and other fields

        Returns:
            Dict: Results of the operation
        """
        results = {"added": 0, "duplicates": 0, "errors": 0}

        try:
            # Add user_id to tweet data
            tweet["user_id"] = user_id

            # Attempt to insert the AI tweet
            self.ai_tweets.update_one(
                {"user_id": user_id, "tweet_id": tweet["tweet_id"]},
                {"$set": tweet},
                upsert=True,
            )
            results["added"] += 1

        except Exception as e:
            if "duplicate key error" in str(e).lower():
                results["duplicates"] += 1
            else:
                results["errors"] += 1
                print(f"Error adding AI tweet: {e}")

        return results

    def get_all_ai_tweets(
        self, user_id: str, limit: int = None, offset: int = 0
    ) -> List[Dict]:
        """
        Retrieve all AI-generated tweets for a specific user with optional pagination

        Args:
            user_id (str): The user ID to fetch tweets for
            limit (int, optional): Maximum number of tweets to return
            offset (int): Number of tweets to skip

        Returns:
            List[Dict]: List of AI tweet documents
        """
        try:
            cursor = (
                self.ai_tweets.find({"user_id": user_id})
                .sort("created_at", -1)
                .skip(offset)
            )

            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            print(f"Error fetching AI tweets: {e}")
            return []

    def check_database_status(self, user_id: str) -> tuple[bool, list]:
        """
        Check database status for a specific user. Returns needs_update=True only when
        the most recent tweet is more than the update threshold.

        Args:
            user_id (str): The user ID to check status for

        Returns:
            tuple[bool, list]: (needs_update, current_tweets)
        """
        current_tweets = self.get_unreplied_tweets(user_id)

        if not current_tweets:
            return True, []

        most_recent_tweet = current_tweets[0]  # Since they're sorted by created_at
        most_recent_time = most_recent_tweet.get("created_at")

        # Ensure both times are timezone-aware
        current_time = datetime.now(timezone.utc)

        # Convert most_recent_time to UTC if it's naive
        if most_recent_time.tzinfo is None:
            most_recent_time = most_recent_time.replace(tzinfo=timezone.utc)

        time_since_update = current_time - most_recent_time
        needs_update = time_since_update > self.update_threshold

        print(f"Needs update: {needs_update}")

        if not needs_update:
            print(
                "\nThe tweets database is up to date. Due to Twitter API rate limits, "
                "we only update tweets that are more than 2 hours old. Please try again later."
            )

        return needs_update, current_tweets

    def close(self):
        """Close MongoDB connection if it's open and hasn't been closed yet"""
        if hasattr(self, "client") and self.client and not hasattr(self, "_closed"):
            self.client.close()
            # Remove or comment out this print statement since the context manager will handle it
            # print("MongoDB connection closed")
            self._closed = True

    def add_ai_mention_tweets(self, user_id: str, tweets: List[Dict]) -> Dict:
        """
        Add tweets that mention AI to the database

        Args:
            user_id (str): The user ID who owns these mentions
            tweets (List[Dict]): List of tweet dictionaries that mention AI

        Returns:
            Dict: Results of the operation with counts of added, duplicate, and error tweets
        """
        if not tweets:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for tweet in tweets:
            try:
                # Add user_id and required fields
                tweet["user_id"] = user_id
                tweet["created_at"] = tweet.get(
                    "created_at", datetime.now(timezone.utc)
                )
                tweet["replied_to"] = tweet.get("replied_to", False)

                # Ensure public_metrics exist with defaults
                tweet["public_metrics"] = PublicMetrics(
                    retweet_count=tweet.get("public_metrics", {}).get(
                        "retweet_count", 0
                    ),
                    reply_count=tweet.get("public_metrics", {}).get("reply_count", 0),
                    like_count=tweet.get("public_metrics", {}).get("like_count", 0),
                    quote_count=tweet.get("public_metrics", {}).get("quote_count", 0),
                )

                # Attempt to insert the tweet
                self.ai_mention_tweets.update_one(
                    {"user_id": user_id, "tweet_id": tweet["tweet_id"]},
                    {"$set": tweet},
                    upsert=True,
                )
                results["added"] += 1

            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    results["duplicates"] += 1
                else:
                    results["errors"] += 1
                    print(f"Error adding AI mention tweet: {e}")

        return results

    def get_ai_mention_tweets(
        self, user_id: str, limit: int = None, offset: int = 0
    ) -> List[Dict]:
        """
        Retrieve all mentions for a specific user

        Args:
            user_id (str): The user ID to fetch mentions for
            limit (int, optional): Maximum number of tweets to return
            offset (int): Number of tweets to skip

        Returns:
            List[Dict]: List of tweets that mention AI
        """
        try:
            cursor = (
                self.ai_mention_tweets.find({"user_id": user_id})
                .sort("created_at", -1)
                .skip(offset)
            )

            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            print(f"Error fetching AI mention tweets: {e}")
            return []

    def add_replied_tweet(self, user_id: str, tweet_id: str) -> bool:
        """Mark a tweet as replied to in the database for a specific user"""
        try:
            result = self.tweets.update_one(
                {"user_id": user_id, "tweet_id": tweet_id},
                {
                    "$set": {
                        "replied_to": True,
                        "replied_at": datetime.now(timezone.utc),
                    }
                },
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[DB] Error marking tweet as replied: {str(e)}")
            return False

    def get_unreplied_tweets(self, user_id: str) -> list:
        """Get tweets that haven't been replied to yet for a specific user"""
        try:
            unreplied_tweets = (
                self.tweets.find(
                    {
                        "user_id": user_id,
                        "$or": [
                            {"replied_to": {"$exists": False}},
                            {"replied_to": False},
                        ],
                    }
                )
                .sort("created_at", -1)
                .limit(20)
            )
            return list(unreplied_tweets)
        except Exception as e:
            print(f"Error getting unreplied tweets: {str(e)}")
            return []

    def get_replied_tweets(self, user_id: str) -> list:
        """Get tweets that have been replied to for a specific user"""
        try:
            replied_tweets = (
                self.tweets.find(
                    {
                        "user_id": user_id,
                        "$or": [
                            {"replied_to": {"$exists": True}},
                            {"replied_to": True},
                        ],
                    }
                )
                .sort("created_at", -1)
                .limit(100)
            )

            return list(replied_tweets)
        except Exception as e:
            print(f"Error getting replied tweets: {str(e)}")
            return []

    def is_ai_tweet(self, user_id: str, tweet_id: str) -> bool:
        """Check if a tweet was generated by the AI for a specific user"""
        try:
            # Check if it's a mention
            mention = self.ai_mention_tweets.find_one(
                {"user_id": user_id, "tweet_id": tweet_id}
            )
            if mention:
                return False

            # Check if it's our tweet
            ai_tweet = self.written_ai_tweets.find_one(
                {"user_id": user_id, "tweet_id": tweet_id}
            )
            if ai_tweet:
                return True

            # Check if it's our reply
            ai_reply = self.written_ai_tweets_replies.find_one(
                {"user_id": user_id, "tweet_id": tweet_id}
            )

            return bool(ai_reply)

        except Exception as e:
            print(f"[DB] Error checking if tweet is from AI: {str(e)}")
            return False

    def add_replied_mention(self, tweet_id: str, user_id: str) -> bool:
        """
        Mark a mention as replied to for a specific user

        Args:
            tweet_id (str): The ID of the tweet that was replied to
            user_id (str): The user ID who made the reply

        Returns:
            bool: True if the update was successful, False otherwise
        """
        try:
            result = self.ai_mention_tweets.update_one(
                {"user_id": user_id, "tweet_id": tweet_id},
                {
                    "$set": {
                        "replied_to": True,
                        "replied_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[DB] Error marking mention as replied: {str(e)}")
            return False

    def is_mention_replied(self, tweet_id: str, user_id: str) -> bool:
        """
        Check if a mention has already been replied to by a specific user

        Args:
            tweet_id (str): The ID of the tweet to check
            user_id (str): The user ID who might have replied

        Returns:
            bool: True if the mention has been replied to, False otherwise
        """
        try:
            mention = self.ai_mention_tweets.find_one(
                {"user_id": user_id, "tweet_id": tweet_id, "replied_to": True}
            )
            return mention is not None
        except Exception as e:
            print(f"Error checking if mention is replied: {e}")
            return False

    def check_mentions_status(self, user_id: str) -> tuple[bool, list]:
        """Check mentions status for a specific user"""
        current_mentions = (
            self.ai_mention_tweets.find({"user_id": user_id})
            .sort("created_at", -1)
            .limit(100)
        )
        current_mentions_list = list(current_mentions)

        if not current_mentions_list:
            return True, []

        most_recent_mention = current_mentions_list[0]
        most_recent_time = most_recent_mention.get("created_at")

        if most_recent_time is None or most_recent_time.tzinfo is None:
            return True, current_mentions_list

        time_since_update = datetime.now(timezone.utc) - most_recent_time
        needs_update = time_since_update > self.update_threshold

        return needs_update, current_mentions_list

    def get_most_recent_mention_id(self, user_id: str) -> str | None:
        """Get the most recent mention ID for a specific user"""
        try:
            most_recent = self.ai_mention_tweets.find_one(
                {
                    "tweet_id": {
                        "$exists": True,
                        "$regex": "^[0-9]+$",
                    }  # Only numeric IDs
                },
                sort=[("created_at", -1)],
            )
            return str(most_recent["tweet_id"]) if most_recent else None
        except Exception as e:
            print(f"Error fetching most recent mention ID: {e}")
            return None

    def add_mentions(self, mentions: List[Dict], user_id: str) -> Dict:
        """
        Add multiple mentions to the database for a specific user

        Args:
            mentions (List[Dict]): List of mentions to add
            user_id (str): The user ID who owns these mentions

        Returns:
            Dict: Results of the operation with counts
        """
        if not mentions:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for mention_data in mentions:
            try:
                # Ensure all required fields are present
                mention = {
                    "user_id": user_id,  # Add user_id to each mention
                    "tweet_id": str(
                        mention_data.get("id") or mention_data.get("tweet_id")
                    ),
                    "text": mention_data.get("text", ""),
                    "created_at": mention_data.get(
                        "created_at", datetime.now(timezone.utc)
                    ),
                    "replied_to": mention_data.get("replied_to", False),
                    "replied_at": mention_data.get("replied_at"),
                }

                # Only store if we have the minimum required data
                if mention["tweet_id"] and mention["text"]:
                    self.ai_mention_tweets.update_one(
                        {
                            "user_id": user_id,
                            "tweet_id": mention["tweet_id"],
                        },  # Add user_id to query
                        {"$set": mention},
                        upsert=True,
                    )
                    results["added"] += 1
                else:
                    print(f"Skipping invalid mention data: {mention_data}")
                    results["errors"] += 1

            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    results["duplicates"] += 1
                else:
                    results["errors"] += 1
                    print(f"Error adding mention: {e}")
                    print(f"Problematic mention data: {mention_data}")

        return results

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def is_tweet_replied(self, user_id: str, tweet_id: str) -> bool:
        """
        Check if we should not reply to a tweet.
        Returns True if we should NOT reply.
        """
        try:
            tweet = self.tweets.find_one({"tweet_id": tweet_id})
            if not tweet:
                return True
                
            # Don't reply if:
            # 1. It's our tweet
            # 2. We've already replied to it
            # 3. It's part of a conversation we're in
            if (tweet.get("author_id") == user_id or  # our tweet
                tweet.get("replied_to") is True or    # already replied
                self.tweets.find_one({                # in conversation
                    "conversation_id": tweet.get("conversation_id"),
                    "author_id": user_id
                })):
                return True
                
            return False

        except Exception as e:
            print(f"Error in is_tweet_replied: {e}")
            return True  # Fail safe

    # ===== Twitter Authentication Methods =====
    
    def add_twitter_auth(self, auth_data: TwitterAuth) -> Dict:
        """
        Add or update Twitter authentication information for a client
        
        Args:
            auth_data (TwitterAuth): The authentication data
            
        Returns:
            Dict: Result of the operation
        """
        try:
            # Ensure the auth data has timestamps
            if "created_at" not in auth_data:
                auth_data["created_at"] = datetime.now(timezone.utc)
            auth_data["updated_at"] = datetime.now(timezone.utc)
            
            # Insert or update the authentication data
            result = self.twitter_auth.update_one(
                {"client_id": auth_data["client_id"]},
                {"$set": auth_data},
                upsert=True
            )
            
            return {
                "status": "success",
                "message": "Twitter authentication saved successfully",
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            }
        except Exception as e:
            print(f"[DB] Error adding Twitter authentication: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_twitter_auth(self, client_id: str) -> Optional[TwitterAuth]:
        """
        Get Twitter authentication information for a client
        
        Args:
            client_id (str): The client ID
            
        Returns:
            Optional[TwitterAuth]: The authentication data if found, None otherwise
        """
        try:
            auth_data = self.twitter_auth.find_one({"client_id": client_id})
            return auth_data
        except Exception as e:
            print(f"[DB] Error getting Twitter authentication: {e}")
            return None
    
    def delete_twitter_auth(self, client_id: str) -> Dict:
        """
        Delete Twitter authentication information for a client
        
        Args:
            client_id (str): The client ID
            
        Returns:
            Dict: Result of the operation
        """
        try:
            result = self.twitter_auth.delete_one({"client_id": client_id})
            
            if result.deleted_count > 0:
                return {
                    "status": "success",
                    "message": "Twitter authentication deleted successfully"
                }
            else:
                return {
                    "status": "warning",
                    "message": "No Twitter authentication found for this client"
                }
        except Exception as e:
            print(f"[DB] Error deleting Twitter authentication: {e}")
            return {"status": "error", "message": str(e)}
    
    # ===== Agent Configuration Methods =====
    
    def add_agent_config(self, config_data: AgentConfig) -> Dict:
        """
        Add or update agent configuration for a client
        
        Args:
            config_data (AgentConfig): The agent configuration data
            
        Returns:
            Dict: Result of the operation
        """
        try:
            # Ensure the config data has timestamps
            if "created_at" not in config_data:
                config_data["created_at"] = datetime.now(timezone.utc)
            config_data["updated_at"] = datetime.now(timezone.utc)
            
            # Insert or update the configuration data
            result = self.agent_config.update_one(
                {
                    "client_id": config_data["client_id"],
                    "agent_name": config_data["agent_name"]
                },
                {"$set": config_data},
                upsert=True
            )
            
            return {
                "status": "success",
                "message": "Agent configuration saved successfully",
                "modified_count": result.modified_count,
                "upserted_id": result.upserted_id
            }
        except Exception as e:
            print(f"[DB] Error adding agent configuration: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_agent_config(self, client_id: str) -> Optional[AgentConfig]:
        """
        Get agent configuration for a client
        
        Args:
            client_id (str): The client ID
            
        Returns:
            Optional[AgentConfig]: The configuration data if found, None otherwise
        """
        try:
            config_data = self.agent_config.find_one({
                "client_id": client_id,
            })
            return config_data
        except Exception as e:
            print(f"[DB] Error getting agent configuration: {e}")
            return None
    
    def get_all_agent_configs(self, client_id: str) -> List[AgentConfig]:
        """
        Get all agent configurations for a client
        
        Args:
            client_id (str): The client ID
            
        Returns:
            List[AgentConfig]: List of all agent configurations for the client
        """
        try:
            config_data = list(self.agent_config.find({"client_id": client_id}))
            return config_data
        except Exception as e:
            print(f"[DB] Error getting all agent configurations: {e}")
            return []
    
    def delete_agent_config(self, client_id: str, agent_name: str) -> Dict:
        """
        Delete agent configuration for a client
        
        Args:
            client_id (str): The client ID
            agent_name (str): The agent name
            
        Returns:
            Dict: Result of the operation
        """
        try:
            result = self.agent_config.delete_one({
                "client_id": client_id,
                "agent_name": agent_name
            })
            
            if result.deleted_count > 0:
                return {
                    "status": "success",
                    "message": "Agent configuration deleted successfully"
                }
            else:
                return {
                    "status": "warning",
                    "message": "No agent configuration found for this client and agent"
                }
        except Exception as e:
            print(f"[DB] Error deleting agent configuration: {e}")
            return {"status": "error", "message": str(e)}
