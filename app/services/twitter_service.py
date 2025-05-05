import tweepy
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import time
import html
import re
import logging
import uuid

from app.utils.db import get_db
from app.utils.config import Config
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

class TwitterService:
    """Service for handling Twitter API interactions"""
    
    def __init__(self):
        self.config = Config()
    
    @staticmethod
    def _get_client(client_id: str) -> Tuple[bool, Any]:
        """
        Get a Twitter API client for a user
        
        Args:
            client_id: Client ID to get API for
            
        Returns:
            Tuple of (success, api_client)
        """
        try:
            db = get_db()
            auth_data = db.get_twitter_auth(client_id)
            
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Client not authenticated"
                }
            
            # Get Twitter API credentials
            config = Config()
            consumer_key = config.get("TWITTER_API_KEY")
            consumer_secret = config.get("TWITTER_API_SECRET")
            
            if not consumer_key or not consumer_secret:
                return False, {
                    "status": "error",
                    "message": "Twitter API credentials not configured"
                }
            
            # Create OAuth1 handler
            auth = tweepy.OAuth1UserHandler(
                consumer_key,
                consumer_secret
            )
            
            # Set access token
            auth.set_access_token(
                auth_data.get("oauth_token"),
                auth_data.get("oauth_token_secret")
            )
            
            # Create API client
            api = tweepy.API(auth)
            
            # Verify credentials
            api.verify_credentials()
            
            return True, api
        
        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Twitter API error: {str(e)}"
            }
        
        except Exception as e:
            logger.error(f"Error creating Twitter client: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to create Twitter client: {str(e)}"
            }
    
    def post_tweet(self, client_id: str, content: str, media_ids: Optional[List[str]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Post a tweet for a client
        
        Args:
            client_id: Client ID to post tweet for
            content: Tweet content
            media_ids: Optional list of media IDs to attach
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Validate input
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Client ID is required"
                }
            
            if not content:
                return False, {
                    "status": "error",
                    "message": "Tweet content is required"
                }
            
            # Check if content is within Twitter's character limit
            if len(content) > 280:
                return False, {
                    "status": "error",
                    "message": "Tweet content exceeds 280 characters"
                }
            
            # Check authentication
            success, auth_status = auth_service.get_twitter_auth_status(client_id)
            
            if not success:
                return False, {
                    "status": "error",
                    "message": "Failed to check authentication status"
                }
            
            if not auth_status.get("is_authenticated", False):
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            if auth_status.get("is_expired", True):
                # Try to refresh token
                success, refresh_result = auth_service.refresh_twitter_token(client_id)
                
                if not success:
                    return False, {
                        "status": "error",
                        "message": "Authentication expired and refresh failed"
                    }
            
            # In a real implementation, you would:
            # 1. Get the access token for the client
            # 2. Use Twitter API to post the tweet
            
            # For this demo, we'll simulate a successful tweet
            tweet_id = f"tweet_{uuid.uuid4().hex}"
            
            # Store tweet in database
            db = get_db()
            tweet_data = {
                "client_id": client_id,
                "tweet_id": tweet_id,
                "content": content,
                "media_ids": media_ids or [],
                "created_at": datetime.now().isoformat()
            }
            
            db.store_tweet(tweet_id, tweet_data)
            
            return True, {
                "status": "success",
                "tweet_id": tweet_id,
                "message": "Tweet posted successfully"
            }
        
        except Exception as e:
            logger.error(f"Error posting tweet: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to post tweet: {str(e)}"
            }
    
    def get_user_timeline(self, client_id: str, count: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Get the user's timeline
        
        Args:
            client_id: Client ID to get timeline for
            count: Number of tweets to retrieve
            
        Returns:
            Tuple of (success, timeline_data)
        """
        try:
            # Get Twitter API client
            success, client = self._get_client(client_id)
            
            if not success:
                return False, client
            
            # Get timeline
            timeline = client.user_timeline(count=count)
            
            # Format tweets
            tweets = []
            for tweet in timeline:
                tweets.append({
                    "id": tweet.id_str,
                    "text": tweet.text,
                    "created_at": str(tweet.created_at),
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count
                })
            
            return True, {
                "status": "success",
                "tweets": tweets
            }
        
        except Exception as e:
            logger.error(f"Error getting user timeline: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get user timeline: {str(e)}"
            }
    
    def get_home_timeline(self, client_id: str, count: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Get the user's home timeline
        
        Args:
            client_id: Client ID to get timeline for
            count: Number of tweets to retrieve
            
        Returns:
            Tuple of (success, timeline_data)
        """
        try:
            # Get Twitter API client
            success, client = self._get_client(client_id)
            
            if not success:
                return False, client
            
            # Get timeline
            timeline = client.home_timeline(count=count)
            
            # Format tweets
            tweets = []
            for tweet in timeline:
                tweets.append({
                    "id": tweet.id_str,
                    "text": tweet.text,
                    "created_at": str(tweet.created_at),
                    "user": {
                        "id": tweet.user.id_str,
                        "name": tweet.user.name,
                        "screen_name": tweet.user.screen_name
                    },
                    "retweet_count": tweet.retweet_count,
                    "favorite_count": tweet.favorite_count
                })
            
            return True, {
                "status": "success",
                "tweets": tweets
            }
        
        except Exception as e:
            logger.error(f"Error getting home timeline: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get home timeline: {str(e)}"
            }
    
    def like_tweet(self, client_id: str, tweet_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Like a tweet
        
        Args:
            client_id: Client ID to like for
            tweet_id: Tweet ID to like
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Get Twitter API client
            success, client = self._get_client(client_id)
            
            if not success:
                return False, client
            
            # Like tweet
            client.create_favorite(id=tweet_id)
            
            return True, {
                "status": "success",
                "message": "Tweet liked successfully"
            }
        
        except Exception as e:
            logger.error(f"Error liking tweet: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to like tweet: {str(e)}"
            }
    
    def retweet(self, client_id: str, tweet_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Retweet a tweet
        
        Args:
            client_id: Client ID to retweet for
            tweet_id: Tweet ID to retweet
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Get Twitter API client
            success, client = self._get_client(client_id)
            
            if not success:
                return False, client
            
            # Retweet
            client.retweet(id=tweet_id)
            
            return True, {
                "status": "success",
                "message": "Tweet retweeted successfully"
            }
        
        except Exception as e:
            logger.error(f"Error retweeting: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to retweet: {str(e)}"
            }
    
    def upload_media(self, client_id: str, media_data: bytes, media_type: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Upload media to Twitter
        
        Args:
            client_id: Client ID to upload media for
            media_data: Binary media data
            media_type: MIME type of media
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Validate input
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Client ID is required"
                }
            
            if not media_data:
                return False, {
                    "status": "error",
                    "message": "Media data is required"
                }
            
            if not media_type:
                return False, {
                    "status": "error",
                    "message": "Media type is required"
                }
            
            # Check authentication
            success, auth_status = auth_service.get_twitter_auth_status(client_id)
            
            if not success:
                return False, {
                    "status": "error",
                    "message": "Failed to check authentication status"
                }
            
            if not auth_status.get("is_authenticated", False):
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            if auth_status.get("is_expired", True):
                # Try to refresh token
                success, refresh_result = auth_service.refresh_twitter_token(client_id)
                
                if not success:
                    return False, {
                        "status": "error",
                        "message": "Authentication expired and refresh failed"
                    }
            
            # In a real implementation, you would:
            # 1. Get the access token for the client
            # 2. Use Twitter API to upload the media
            
            # For this demo, we'll simulate a successful upload
            media_id = f"media_{uuid.uuid4().hex}"
            
            # Store media info in database
            db = get_db()
            media_data = {
                "client_id": client_id,
                "media_id": media_id,
                "media_type": media_type,
                "created_at": datetime.now().isoformat()
            }
            
            db.store_media(media_id, media_data)
            
            return True, {
                "status": "success",
                "media_id": media_id,
                "message": "Media uploaded successfully"
            }
        
        except Exception as e:
            logger.error(f"Error uploading media: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to upload media: {str(e)}"
            }
    
    def get_tweet(self, tweet_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get tweet details
        
        Args:
            tweet_id: ID of the tweet to retrieve
            
        Returns:
            Tuple of (success, tweet_data)
        """
        try:
            # Validate input
            if not tweet_id:
                return False, {
                    "status": "error",
                    "message": "Tweet ID is required"
                }
            
            # Get tweet from database
            db = get_db()
            tweet_data = db.get_tweet(tweet_id)
            
            if not tweet_data:
                return False, {
                    "status": "error",
                    "message": "Tweet not found"
                }
            
            # Return tweet data
            return True, {
                "status": "success",
                "tweet_id": tweet_data.get("tweet_id"),
                "content": tweet_data.get("content"),
                "created_at": tweet_data.get("created_at"),
                "client_id": tweet_data.get("client_id"),
                "twitter_username": tweet_data.get("twitter_username"),
                "url": f"https://twitter.com/{tweet_data.get('twitter_username')}/status/{tweet_id}"
            }
        
        except Exception as e:
            logger.error(f"Error getting tweet: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get tweet: {str(e)}"
            }
    
    def list_client_tweets(self, client_id: str, limit: int = 10, offset: int = 0) -> Tuple[bool, Dict[str, Any]]:
        """
        List tweets for a client
        
        Args:
            client_id: Client ID to list tweets for
            limit: Maximum number of tweets to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (success, tweets_data)
        """
        try:
            # Validate input
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Client ID is required"
                }
            
            # Get tweets from database
            db = get_db()
            tweets = db.list_client_tweets(client_id, limit, offset)
            
            # Format tweets
            formatted_tweets = []
            for tweet in tweets:
                formatted_tweets.append({
                    "tweet_id": tweet.get("tweet_id"),
                    "content": tweet.get("content"),
                    "created_at": tweet.get("created_at"),
                    "twitter_username": tweet.get("twitter_username"),
                    "url": f"https://twitter.com/{tweet.get('twitter_username')}/status/{tweet.get('tweet_id')}"
                })
            
            # Return tweets
            return True, {
                "status": "success",
                "client_id": client_id,
                "tweets": formatted_tweets,
                "count": len(formatted_tweets),
                "limit": limit,
                "offset": offset
            }
        
        except Exception as e:
            logger.error(f"Error listing tweets: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to list tweets: {str(e)}"
            }
    
    def delete_tweet(self, client_id: str, tweet_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete a tweet
        
        Args:
            client_id: Client ID that owns the tweet
            tweet_id: ID of the tweet to delete
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Validate input
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Client ID is required"
                }
            
            if not tweet_id:
                return False, {
                    "status": "error",
                    "message": "Tweet ID is required"
                }
            
            # Get tweet from database
            db = get_db()
            tweet_data = db.get_tweet(tweet_id)
            
            if not tweet_data:
                return False, {
                    "status": "error",
                    "message": "Tweet not found"
                }
            
            # Check if client owns the tweet
            if tweet_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Client does not own this tweet"
                }
            
            # In a real application, we would use the Twitter API to delete the tweet
            # For demonstration purposes, we'll simulate a successful deletion
            
            # Delete tweet from database
            db.delete_tweet(tweet_id)
            
            # Return success
            return True, {
                "status": "success",
                "message": "Tweet deleted successfully"
            }
        
        except Exception as e:
            logger.error(f"Error deleting tweet: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to delete tweet: {str(e)}"
            }
    
    def get_tweet_metrics(self, client_id: str, tweet_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get metrics for a tweet
        
        Args:
            client_id: Client ID to get metrics for
            tweet_id: ID of tweet to get metrics for
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Validate input
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Client ID is required"
                }
            
            if not tweet_id:
                return False, {
                    "status": "error",
                    "message": "Tweet ID is required"
                }
            
            # Check authentication
            success, auth_status = auth_service.get_twitter_auth_status(client_id)
            
            if not success:
                return False, {
                    "status": "error",
                    "message": "Failed to check authentication status"
                }
            
            if not auth_status.get("is_authenticated", False):
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            # Get tweet from database
            db = get_db()
            tweet_data = db.get_tweet(tweet_id)
            
            if not tweet_data or tweet_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Tweet not found or not owned by client"
                }
            
            # In a real implementation, you would:
            # 1. Get the access token for the client
            # 2. Use Twitter API to get metrics for the tweet
            
            # For this demo, we'll simulate metrics
            metrics = {
                "impressions": 1000 + int(time.time()) % 1000,  # Random number based on time
                "likes": 50 + int(time.time()) % 50,
                "retweets": 10 + int(time.time()) % 20,
                "replies": 5 + int(time.time()) % 10
            }
            
            return True, {
                "status": "success",
                "tweet_id": tweet_id,
                "metrics": metrics
            }
        
        except Exception as e:
            logger.error(f"Error getting tweet metrics: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get tweet metrics: {str(e)}"
            }
    
    def get_client_tweets(self, client_id: str, limit: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Get recent tweets for a client
        
        Args:
            client_id: Client ID to get tweets for
            limit: Maximum number of tweets to return
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Validate input
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Client ID is required"
                }
            
            # Check authentication
            success, auth_status = auth_service.get_twitter_auth_status(client_id)
            
            if not success:
                return False, {
                    "status": "error",
                    "message": "Failed to check authentication status"
                }
            
            if not auth_status.get("is_authenticated", False):
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            # In a real implementation, you would:
            # 1. Get the access token for the client
            # 2. Use Twitter API to get recent tweets
            
            # For this demo, we'll get tweets from our database
            db = get_db()
            tweets = db.get_client_tweets(client_id, limit)
            
            if not tweets:
                return True, {
                    "status": "success",
                    "tweets": []
                }
            
            # Format tweets
            formatted_tweets = []
            for tweet in tweets:
                formatted_tweets.append({
                    "tweet_id": tweet.get("tweet_id"),
                    "content": tweet.get("content"),
                    "created_at": tweet.get("created_at")
                })
            
            return True, {
                "status": "success",
                "tweets": formatted_tweets
            }
        
        except Exception as e:
            logger.error(f"Error getting client tweets: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get client tweets: {str(e)}"
            }


# Create a singleton instance
twitter_service = TwitterService() 