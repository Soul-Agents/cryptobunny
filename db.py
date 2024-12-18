from pymongo import MongoClient
from typing import List, Dict
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

from schemas import (
    ReplyToAITweet,  
    Tweet, 
    WrittenAITweet, 
    WrittenAITweetReply,
    PublicMetrics
)

# Load environment variables from .env file
load_dotenv()

# Was: MONGODB_URI = os.environ["MONGODB_URI"]
# Get MongoDB connection strings from environment
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_URI = os.getenv("MONGODB_URI")


class TweetDB:
    def __init__(self):
        # Set update threshold to 1 minute for testing
        self.update_threshold = timedelta(minutes=1)
        
        # Try to get the public MongoDB URL first
        mongodb_uri = os.getenv("MONGODB_URL")  # Try MONGODB_URL first
        
        if not mongodb_uri or "railway.internal" in mongodb_uri:
            # Fallback to MONGODB_URI if URL contains internal references
            mongodb_uri = os.getenv("MONGODB_URI")
        
        print("Attempting database connection...")
        print(f"Using connection string: {mongodb_uri[:20]}...") # Only show start of URI for security
        
        if not mongodb_uri:
            raise ValueError("No valid MongoDB connection string found in environment variables")
        
        try:
            # Initialize MongoDB connection with different timeout settings
            self.client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                retryWrites=True,
                retryReads=True
            )
            
            # Test connection
            self.client.admin.command('ping')
            print("[DB] Successfully connected to MongoDB!")
            
            # Initialize collections with explicit database name
            self.db = self.client['tweets']  # Specify database name explicitly
            self.tweets = self.db.tweets
            self.written_ai_tweets = self.db.written_ai_tweets
            self.written_ai_tweets_replies = self.db.written_ai_tweets_replies
            self.ai_mention_tweets = self.db.ai_mention_tweets
            
            # Create index
            self.tweets.create_index("tweet_id", unique=True)
            self.ai_mention_tweets.create_index("tweet_id", unique=True)
            self.written_ai_tweets.create_index("tweet_id", unique=True)
            self.written_ai_tweets_replies.create_index("tweet_id", unique=True)
            
        except Exception as e:
            print(f"[DB] Failed to connect to MongoDB: {e}")
            print(f"[DB] Connection string used: {mongodb_uri[:20]}...")  # Show partial URI
            raise
    
    def get_last_written_ai_tweets(self, limit: int = 10) -> List[WrittenAITweet]:
        """Get the last N tweets written by AI"""
        try:
            return list(self.written_ai_tweets.find().sort("saved_at", -1).limit(limit))
        except Exception as e:
            print(f"Error fetching last written AI tweets: {e}")
            return []

    def get_last_written_ai_tweet_replies(self, limit: int = 21) -> List[WrittenAITweetReply]:
        """Get the last N replies written by AI"""
        try:
            return list(self.written_ai_tweets_replies.find().sort("saved_at", -1).limit(limit))
        except Exception as e:
            print(f"Error fetching last written AI tweet replies: {e}")
            return []

    
    def add_written_ai_tweet_reply(self, original_tweet_id: str, reply: str) -> Dict:
        """Add replies to a written AI tweet"""
        try:
            reply_data = WrittenAITweetReply(
                tweet_id=original_tweet_id,
                reply={"reply": reply},
                public_metrics={},
                conversation_id=None,
                in_reply_to_user_id=None,
                saved_at=datetime.now(timezone.utc)
            )
            
            self.written_ai_tweets_replies.update_one(
                {"tweet_id": original_tweet_id},
                {"$set": reply_data},
                upsert=True,
            )
            return {"status": "Success"}
        except Exception as e:
            print(f"[DB] Error adding written AI tweet reply: {e}")
            return {"status": "Error", "message": str(e)}

    def add_replies_to_ai_tweet(self, original_tweet_id: str, replies: List[Dict]) -> Dict:
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

    def add_tweets(self, tweets: List[Dict]) -> Dict:
        """Add multiple tweets to the database"""
        if not tweets:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for tweet_data in tweets:
            try:
                # Handle Twitter API v2 format
                tweet = Tweet(
                    tweet_id=str(tweet_data.get("id") or tweet_data.get("tweet_id")),
                    text=tweet_data.get("text", ""),
                    created_at=tweet_data.get("created_at", datetime.now(timezone.utc)),
                    author_id=str(tweet_data.get("author_id", "")),
                    public_metrics=PublicMetrics(
                        retweet_count=tweet_data.get("public_metrics", {}).get("retweet_count", 0),
                        reply_count=tweet_data.get("public_metrics", {}).get("reply_count", 0),
                        like_count=tweet_data.get("public_metrics", {}).get("like_count", 0),
                        quote_count=tweet_data.get("public_metrics", {}).get("quote_count", 0)
                    ),
                    conversation_id=tweet_data.get("conversation_id"),
                    in_reply_to_user_id=tweet_data.get("in_reply_to_user_id"),
                    in_reply_to_tweet_id=tweet_data.get("in_reply_to_tweet_id", tweet_data.get("referenced_tweet_id")),
                    replied_to=tweet_data.get("replied_to", False),
                    replied_at=tweet_data.get("replied_at")
                )

                if not tweet["tweet_id"] or not tweet["text"]:
                    print(f"Skipping invalid tweet: {tweet_data}")
                    results["errors"] += 1
                    continue

                self.tweets.update_one(
                    {"tweet_id": tweet["tweet_id"]}, 
                    {"$set": tweet}, 
                    upsert=True
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

    def add_written_ai_tweet(self, tweet: WrittenAITweet) -> Dict:
        """Add a single written AI tweet to the database"""
        try:
            self.written_ai_tweets.update_one(
                {"tweet_id": tweet["tweet_id"]},
                {"$set": tweet},
                upsert=True,
            )
            return {"status": "Success", "added": 1}
        except Exception as e:
            print(f"[DB] Error adding written tweet: {e}")
            return {"status": "Error", "message": str(e), "added": 0}

    def get_all_tweets(self, limit: int = None, offset: int = 0) -> List[Tweet]:
        """
        Retrieve all tweets with optional pagination

        Args:
            limit (int, optional): Maximum number of tweets to return
            offset (int): Number of tweets to skip

        Returns:
            List[Dict]: List of tweet documents
        """
        try:
            cursor = self.tweets.find({}).sort("created_at", -1).skip(offset)

            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            print(f"Error fetching tweets: {e}")
            return []

    def get_most_recent_tweet_id(self) -> str | None:
        """
        Get the ID of the most recent tweet in the database

        Returns:
            str | None: The most recent tweet ID or None if no tweets exist
        """
        try:
            most_recent = self.tweets.find_one(
                {}, sort=[("tweet_id", -1)]  # Sort by tweet_id in descending order
            )
            return most_recent["tweet_id"] if most_recent else None
        except Exception as e:
            print(f"Error fetching most recent tweet ID: {e}")
            return None

    def add_ai_tweet(self, tweet: Dict) -> Dict:
        """
        Add a single AI-generated tweet to the database

        Args:
            tweet (Dict): Tweet dictionary containing tweet_id, text, and other fields

        Returns:
            Dict: Results of the operation
        """
        results = {"added": 0, "duplicates": 0, "errors": 0}

        try:

            # Attempt to insert the AI tweet
            self.ai_tweets.update_one(
                {"tweet_id": tweet["tweet_id"]}, {"$set": tweet}, upsert=True
            )
            results["added"] += 1

        except Exception as e:
            if "duplicate key error" in str(e).lower():
                results["duplicates"] += 1
            else:
                results["errors"] += 1
                print(f"Error adding AI tweet: {e}")

        return results

    def get_all_ai_tweets(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """
        Retrieve all AI-generated tweets with optional pagination

        Args:
            limit (int, optional): Maximum number of tweets to return
            offset (int): Number of tweets to skip

        Returns:
            List[Dict]: List of AI tweet documents
        """
        try:
            cursor = self.ai_tweets.find({}).sort("created_at", -1).skip(offset)

            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            print(f"Error fetching AI tweets: {e}")
            return []

    def check_database_status(self) -> tuple[bool, list]:
        """
        Check database status and determine if update is needed

        Returns:
            tuple[bool, list]: (needs_update, current_tweets)
        """
        # Get latest 100 tweets from database
        # current_tweets = self.get_all_tweets(limit=100)
        current_tweets = self.get_unreplied_tweets()
        # print("\nCurrent tweets in database (latest 100):")
        for tweet in current_tweets:
            created_at = tweet.get("created_at", "No date")
            # print(f"Tweet ID: {tweet['tweet_id']}, Created at: {created_at}")
            # print(f"Text: {tweet['text']}\n")

        if not current_tweets:
            return True, []

        # Get the most recent tweet's timestamp
        most_recent_tweet = current_tweets[0]  # Since they're sorted by created_at
        most_recent_time = most_recent_tweet.get("created_at")

        # Ensure both times are timezone-aware
        current_time = datetime.now(timezone.utc)

        # Convert most_recent_time to UTC if it's naive
        if most_recent_time.tzinfo is None:
            most_recent_time = most_recent_time.replace(tzinfo=timezone.utc)

        time_since_update = current_time - most_recent_time

        needs_update = time_since_update > self.update_threshold

        print(f"Most recent tweet time: {most_recent_time}")
        print(f"Time since update: {time_since_update}")
        print(f"Needs update: {needs_update}")

        if not needs_update:
            print(
                "\nThe tweets database is up to date, we are not downloading all new tweets "
                "live due to Twitter API rate limits, however we are working on improving it, "
                "please try again in 1-60 minutes."
            )

        return needs_update, current_tweets

    def close(self):
        """Close MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            print("MongoDB connection closed")

    def add_ai_mention_tweets(self, tweets: List[Dict]) -> Dict:
        """
        Add tweets that mention AI to the database

        Args:
            tweets (List[Dict]): List of tweet dictionaries that mention AI

        Returns:
            Dict: Results of the operation with counts of added, duplicate, and error tweets
        """
        if not tweets:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for tweet in tweets:
            try:
                # Add timestamp if not present
                if "created_at" not in tweet:
                    tweet["created_at"] = datetime.now(timezone.utc)

                # Add replied_to field if not present
                if "replied_to" not in tweet:
                    tweet["replied_to"] = False

                # Ensure public_metrics exist with defaults
                tweet["public_metrics"] = PublicMetrics(
                    retweet_count=tweet.get("public_metrics", {}).get("retweet_count", 0),
                    reply_count=tweet.get("public_metrics", {}).get("reply_count", 0),
                    like_count=tweet.get("public_metrics", {}).get("like_count", 0),
                    quote_count=tweet.get("public_metrics", {}).get("quote_count", 0)
                )

                # Attempt to insert the tweet
                self.ai_mention_tweets.update_one(
                    {"tweet_id": tweet["tweet_id"]},
                    {"$set": tweet},
                    upsert=True
                )
                results["added"] += 1

            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    results["duplicates"] += 1
                else:
                    results["errors"] += 1
                    print(f"Error adding AI mention tweet: {e}")

        return results

    def get_ai_mention_tweets(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """
        Retrieve all tweets

        Args:
            limit (int, optional): Maximum number of tweets to return
            offset (int): Number of tweets to skip

        Returns:
            List[Dict]: List of tweets that mention AI
        """
        try:
            cursor = self.ai_mention_tweets.find({}).sort("created_at", -1).skip(offset)

            if limit:
                cursor = cursor.limit(limit)

            return list(cursor)

        except Exception as e:
            print(f"Error fetching AI mention tweets: {e}")
            return []

    def add_replied_tweet(self, tweet_id: str) -> bool:
        """Mark a tweet as replied to in the database"""
        try:
            result = self.tweets.update_one(
                {"tweet_id": tweet_id},
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

    def get_unreplied_tweets(self) -> list:
        """Get tweets that haven't been replied to yet"""
        try:
            unreplied_tweets = (
                self.tweets.find(
                    {"$or": [{"replied_to": {"$exists": False}}, {"replied_to": False}]}
                )
                .sort("created_at", -1)
                .limit(100)
            )

            return list(unreplied_tweets)
        except Exception as e:
            print(f"Error getting unreplied tweets: {str(e)}")
            return []

    def get_replied_tweets(self) -> list:
        """Get tweets that have been replied to"""
        try:
            replied_tweets = (
                self.tweets.find(
                    {"$or": [{"replied_to": {"$exists": True}}, {"replied_to": True}]}
                )
                .sort("created_at", -1)
                .limit(100)
            )

            return list(replied_tweets)
        except Exception as e:
            print(f"Error getting replied tweets: {str(e)}")
            return []

    def is_ai_tweet(self, tweet_id: str) -> bool:
        """Check if a tweet was generated by the AI"""
        try:
            # First check if it's a mention (mentions should be treated as non-AI tweets)
            mention = self.ai_mention_tweets.find_one({"tweet_id": tweet_id})
            if mention:
                print(f"[DB] Tweet {tweet_id} is a mention")
                return False

            # Then check if it's our tweet
            ai_tweet = self.written_ai_tweets.find_one({"tweet_id": tweet_id})
            if ai_tweet:
                print(f"[DB] Tweet {tweet_id} is an AI tweet")
                return True

            # Finally check if it's our reply
            ai_reply = self.written_ai_tweets_replies.find_one({"tweet_id": tweet_id})
            if ai_reply:
                print(f"[DB] Tweet {tweet_id} is an AI reply")
                return True

            print(f"[DB] Tweet {tweet_id} is not from AI")
            return False

        except Exception as e:
            print(f"[DB] Error checking if tweet is from AI: {str(e)}")
            return False

    def add_replied_mention(self, tweet_id: str) -> bool:
        """Mark a mention as replied to in the database"""
        try:
            result = self.ai_mention_tweets.update_one(
                {"tweet_id": tweet_id},
                {"$set": {"replied_to": True, "replied_at": datetime.now(timezone.utc)}},
                upsert=True
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[DB] Error marking mention as replied: {str(e)}")
            return False

    def is_mention_replied(self, tweet_id: str) -> bool:
        """Check if a mention has already been replied to"""
        try:
            mention = self.ai_mention_tweets.find_one({"tweet_id": tweet_id, "replied_to": True})
            return mention is not None
        except Exception as e:
            print(f"Error checking if mention is replied: {e}")
            return False

    def check_mentions_status(self) -> tuple[bool, list]:
        """
        Check mentions status and determine if update is needed

        Returns:
            tuple[bool, list]: (needs_update, current_mentions)
        """
        # Get latest 100 mentions from database
        current_mentions = self.ai_mention_tweets.find({}).sort("created_at", -1).limit(100)
        current_mentions_list = list(current_mentions)

        if not current_mentions_list:
            return True, []

        # Get the most recent mention's timestamp
        most_recent_mention = current_mentions_list[0]
        most_recent_time = most_recent_mention.get("created_at")

        # If no timestamp exists, we need to update
        if most_recent_time is None or most_recent_time.tzinfo is None:
            return True, current_mentions_list

        # Only compare times if we have a valid timestamp
        current_time = datetime.now(timezone.utc)
        time_since_update = current_time - most_recent_time
        needs_update = time_since_update > self.update_threshold

        print(f"Most recent mention time: {most_recent_time}")
        print(f"Time since mention update: {time_since_update}")
        print(f"Needs mention update: {needs_update}")

        return needs_update, current_mentions_list

    def get_most_recent_mention_id(self) -> str | None:
        """
        Get the ID of the most recent mention in the database

        Returns:
            str | None: The most recent mention ID or None if no mentions exist
        """
        try:
            most_recent = self.ai_mention_tweets.find_one(
                {}, sort=[("tweet_id", -1)]  # Sort by tweet_id in descending order
            )
            return most_recent["tweet_id"] if most_recent else None
        except Exception as e:
            print(f"Error fetching most recent mention ID: {e}")
            return None

    def add_mentions(self, mentions: List[Dict]) -> Dict:
        """Add multiple mentions to the database"""
        if not mentions:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for mention_data in mentions:
            try:
                # Ensure all required fields are present
                mention = {
                    "tweet_id": str(mention_data.get("id") or mention_data.get("tweet_id")),
                    "text": mention_data.get("text", ""),
                    "created_at": mention_data.get("created_at", datetime.now(timezone.utc)),
                    "replied_to": mention_data.get("replied_to", False),
                    "replied_at": mention_data.get("replied_at")
                }

                # Only store if we have the minimum required data
                if mention["tweet_id"] and mention["text"]:
                    self.ai_mention_tweets.update_one(
                        {"tweet_id": mention["tweet_id"]},
                        {"$set": mention},
                        upsert=True
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
