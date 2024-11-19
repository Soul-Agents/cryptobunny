from pymongo import MongoClient
from typing import List, Dict
from datetime import datetime, timezone, timedelta
import os

from schemas import ReplyToAITweet, BaseTweet


MONGODB_URI = os.environ["MONGODB_URI"]


class TweetDB:
    def __init__(self):
        """Initialize MongoDB connection using environment variables"""

        if not MONGODB_URI:
            raise ValueError("MONGODB_URI not found in environment variables")

        print("Initializing database connection...")
        self.update_threshold = timedelta(minutes=60)
        # Connect to MongoDB
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client["tweets"]
        self.tweets = self.db["tweets"]
        self.written_ai_tweets = self.db["written_ai_tweets"]

        # Create indexes for both collections
        self.tweets.create_index("tweet_id", unique=True)

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

        Args:
            tweets (List[Dict]): List of tweet dictionaries

        Returns:
            Dict: Results of the operation
        """
        if not tweets:
            return {"added": 0, "duplicates": 0, "errors": 0}

        results = {"added": 0, "duplicates": 0, "errors": 0}

        for tweet in tweets:
            try:
                # Add timestamp if not present
                if "created_at" not in tweet:
                    tweet["created_at"] = datetime.now(timezone.utc)

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
            self.written_ai_tweets.update_one(
                {"tweet_id": tweet["tweet_id"]}, {"$set": tweet}, upsert=True
            )
            return "Success"
        except Exception as e:
            print(f"Error adding written tweet: {e}")
            return "Error"

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
        current_tweets = self.db.get_all_tweets(limit=10)
        print("\nCurrent tweets in database (latest 10):")
        for tweet in current_tweets:
            created_at = tweet.get("created_at", "No date")
            print(f"Tweet ID: {tweet['tweet_id']}, Created at: {created_at}")
            print(f"Text: {tweet['text']}\n")

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
        self.client.close()
