from pymongo import MongoClient
from typing import List, Dict
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

from schemas import ReplyToAITweet, BaseTweet

# Load environment variables from .env file
load_dotenv()

# Was: MONGODB_URI = os.environ["MONGODB_URI"]
# Get MongoDB connection strings from environment
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_URI = os.getenv("MONGODB_URI")


class TweetDB:
    def __init__(self):
        """Initialize MongoDB connection using environment variables"""
        
        # Debug prints
        print("Environment variables:")
        print(f"MONGODB_URL: {MONGODB_URL}")
        print(f"MONGODB_URI: {MONGODB_URI}")
        
        # Use MONGODB_URI as it's the recommended public URL
        connection_string = MONGODB_URI
        
        if not connection_string:
            raise ValueError("MONGODB_URI not found in environment variables")
            
        print("Initializing database connection...")
        print(f"Attempting to connect with: {connection_string}")

        # Set update threshold
        self.update_threshold = timedelta(minutes=60)

        # Initialize MongoDB connection with stricter timeouts
        self.client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,  # 5 seconds
            connectTimeoutMS=5000,          # 5 seconds
            socketTimeoutMS=5000,           # 5 seconds
            retryWrites=False,              # Don't retry writes
            retryReads=False               # Don't retry reads
        )
        
        # Initialize database and collections
        self.db = self.client["tweets"]
        self.tweets = self.db["tweets"]
        self.written_ai_tweets = self.db["written_ai_tweets"]
        self.written_ai_tweets_replies = self.db["written_ai_tweets_replies"]
        self.ai_mention_tweets = self.db["ai_mention_tweets"]
        
        # Create indexes
        self.tweets.create_index("tweet_id", unique=True)
        self.ai_mention_tweets.create_index("tweet_id", unique=True)
        self.written_ai_tweets_replies.create_index("tweet_id", unique=True)

        # Test connection with timeout
        try:
            self.client.admin.command('ping', maxTimeMS=5000)
            print("Successfully connected to MongoDB")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise

    def add_written_ai_tweet_reply(self, original_tweet_id: str, reply: str) -> Dict:
        """Add replies to a written AI tweet"""
        try:
            self.written_ai_tweets_replies.update_one(
                {"tweet_id": original_tweet_id},
                {"$set": {"reply": reply}},
                upsert=True,
            )
            print(f"Added written AI tweet reply: {original_tweet_id}")
            return {"status": "Success"}
        except Exception as e:
            print(f"Error adding written AI tweet reply: {e}")
            return {"status": "Error", "message": str(e)}

    def add_replies_to_ai_tweet(
        self, original_tweet_id: str, replies: List[Dict]
    ) -> Dict:
        """
        Add replies array to an AI tweet document

        Args:
            original_tweet_id (str): The ID of the original AI tweet
            replies (List[Dict]): List of reply objects from Twitter API

        Returns:
            Dict: Results of the operation
        """
        try:
            formatted_replies = [
                {
                    "reply_id": str(reply["id"]),
                    "author_id": reply["author_id"],
                    "text": reply["text"],
                    "created_at": datetime.fromisoformat(reply["created_at"]),
                    "in_reply_to_user_id": reply["in_reply_to_user_id"],
                }
                for reply in replies
            ]

            # Add/update the replies array in the original tweet document
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
        """
        Add multiple tweets to the database, avoiding duplicates
        """
        if not tweets:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for tweet in tweets:
            try:
                # Add timestamp if not present
                if "created_at" not in tweet:
                    tweet["created_at"] = datetime.now(timezone.utc)

                # Add replied_to field
                tweet["replied_to"] = False

                # Attempt to insert the tweet
                self.tweets.update_one(
                    {"tweet_id": tweet["tweet_id"]}, {"$set": tweet}, upsert=True
                )
                results["added"] += 1

            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    results["duplicates"] += 1
                else:
                    results["errors"] += 1
                    print(f"Error adding tweet: {e}")

        return results

    def add_written_ai_tweet(self, tweet: Dict) -> Dict:
        """
        Add a single written AI tweet to the database
        """
        try:
            formatted_tweet = {
                "tweet_id": str(tweet["id"]),  # Convert id to tweet_id
                "text": tweet["text"],
                "saved_at": datetime.now(timezone.utc),  # Add timestamp
                "edit_history_tweet_ids": tweet["edit_history_tweet_ids"],
            }

            self.written_ai_tweets.update_one(
                {"tweet_id": formatted_tweet["tweet_id"]},
                {"$set": formatted_tweet},
                upsert=True,
            )
            return {"status": "Success"}
        except Exception as e:
            print(f"Error adding written tweet: {e}")
            return {"status": "Error", "message": str(e)}

    def get_all_tweets(self, limit: int = None, offset: int = 0) -> List[BaseTweet]:
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
        results = {"added": 0, "duplicates": 0, "errors": 0}

        if not tweets:
            return results

        for tweet in tweets:
            try:
                # Add timestamp if not present
                if "created_at" not in tweet:
                    tweet["created_at"] = datetime.now(timezone.utc)

                # Attempt to insert the tweet
                self.ai_mention_tweets.update_one(
                    {"tweet_id": tweet["tweet_id"]}, {"$set": tweet}, upsert=True
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
        Retrieve all tweets that mention AI with optional pagination

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
            print(f"Error marking tweet as replied: {str(e)}")
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
        """Check if a tweet reply was created by the AI"""
        try:
            # Check in written_ai_tweets_replies collection
            ai_tweet = self.written_ai_tweets_replies.find_one({"tweet_id": tweet_id})
            if ai_tweet:
                return True

        except Exception as e:
            print(f"Error checking if tweet is from AI: {e}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
