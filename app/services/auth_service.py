import logging
import json
import uuid
from typing import Dict, Any, Tuple, Optional
import time
from datetime import datetime, timedelta
import urllib.parse
import secrets
import hashlib
import base64
import tweepy
import requests

from app.utils.db import get_db
from app.utils.config import Config

logger = logging.getLogger(__name__)

class AuthService:
    """Service for handling authentication"""
    
    def __init__(self):
        self.config = Config()
        self.twitter_api_key = self.config.get("TWITTER_API_KEY", "")
        self.twitter_api_secret = self.config.get("TWITTER_API_SECRET", "")
        self.callback_url = self.config.get("TWITTER_CALLBACK_URL", "http://localhost:3000/callback")
        self.auth_sessions = {}  # Store temporary auth session data
    
    def create_twitter_auth_url(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Create Twitter OAuth URL for a client
        
        Args:
            client_id: Client ID to create auth URL for
            
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
            
            # Check Twitter API credentials
            if not self.twitter_api_key or not self.twitter_api_secret:
                return False, {
                    "status": "error",
                    "message": "Twitter API credentials not configured"
                }
            
            # Get auth data
            db = get_db()
            auth_data = db.get_twitter_auth(client_id)
            
            # Initialize OAuth1UserHandler with application credentials
            oauth1_user_handler = tweepy.OAuth1UserHandler(
                self.twitter_api_key,
                self.twitter_api_secret,
                callback=self.callback_url
            )
            
            # Generate state for security
            state = f"{client_id}:{uuid.uuid4().hex}"
            
            # Store state in session
            session_id = uuid.uuid4().hex
            session_data = {
                "client_id": client_id,
                "state": state,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(minutes=10),
                "used": False
            }
            
            self.auth_sessions[session_id] = session_data
            
            # Get the authorization URL
            try:
                auth_url = oauth1_user_handler.get_authorization_url(state=state)
                
                # Store the request token in the session data
                session_data["request_token"] = oauth1_user_handler.request_token
                
                return True, {
                    "status": "success",
                    "auth_url": auth_url,
                    "session_id": session_id
                }
            except tweepy.TweepyException as e:
                logger.error(f"Tweepy error creating auth URL: {str(e)}")
                return False, {
                    "status": "error",
                    "message": f"Twitter API error: {str(e)}"
                }
        
        except Exception as e:
            logger.error(f"Error creating Twitter auth URL: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to create Twitter auth URL: {str(e)}"
            }
    
    def handle_twitter_callback(self, oauth_token: str, oauth_verifier: str, 
                              state: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Handle Twitter OAuth callback
        
        Args:
            oauth_token: OAuth token from Twitter
            oauth_verifier: OAuth verifier from Twitter
            state: Optional state parameter from Twitter
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Validate input
            if not oauth_token or not oauth_verifier:
                return False, {
                    "status": "error",
                    "message": "OAuth token and verifier are required"
                }
            
            # Parse client ID from state if available
            client_id = None
            session_id = None
            
            if state:
                # Try to extract client ID from state
                state_parts = state.split(":")
                if len(state_parts) >= 2:
                    client_id = state_parts[0]
                    # Could have more parts in later implementation
            
            # If we couldn't extract from state, try to find session by oauth_token
            if not client_id:
                for sid, session in self.auth_sessions.items():
                    if session.get("request_token", {}).get("oauth_token") == oauth_token:
                        client_id = session.get("client_id")
                        session_id = sid
                        break
            
            # If we still don't have a client ID, error
            if not client_id:
                return False, {
                    "status": "error",
                    "message": "Could not identify client from callback parameters"
                }
            
            # Initialize OAuth handler
            oauth1_user_handler = tweepy.OAuth1UserHandler(
                self.twitter_api_key,
                self.twitter_api_secret,
                callback=self.callback_url
            )
            
            # Set the request token
            if session_id and "request_token" in self.auth_sessions[session_id]:
                oauth1_user_handler.request_token = self.auth_sessions[session_id]["request_token"]
            else:
                # If we don't have the request token in our session, create it from the oauth_token
                oauth1_user_handler.request_token = {"oauth_token": oauth_token, "oauth_token_secret": ""}
            
            # Get the access token
            try:
                access_token = oauth1_user_handler.get_access_token(oauth_verifier)
                
                # access_token is a tuple (oauth_token, oauth_token_secret)
                oauth_token = access_token[0]
                oauth_token_secret = access_token[1]
                
                # Create auth object with the tokens
                auth = tweepy.OAuth1UserHandler(
                    self.twitter_api_key,
                    self.twitter_api_secret
                )
                auth.set_access_token(oauth_token, oauth_token_secret)
                
                # Create API client to get user info
                api = tweepy.API(auth)
                user = api.verify_credentials()
                
                # Store tokens in database
                db = get_db()
                auth_data = {
                    "client_id": client_id,
                    "oauth_token": oauth_token,
                    "oauth_token_secret": oauth_token_secret,
                    "user_id": user.id_str,
                    "username": user.screen_name,
                    "user_name": user.name,
                    "profile_image_url": user.profile_image_url_https,
                    "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),  # OAuth1 tokens don't expire, but we'll set a refresh schedule
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                db.store_twitter_auth(client_id, auth_data)
                
                # If we have a session, mark it as used
                if session_id in self.auth_sessions:
                    self.auth_sessions[session_id]["used"] = True
                
                return True, {
                    "status": "success",
                    "client_id": client_id,
                    "user_id": user.id_str,
                    "username": user.screen_name,
                    "message": "Authentication successful"
                }
            
            except tweepy.TweepyException as e:
                logger.error(f"Tweepy error in callback: {str(e)}")
                return False, {
                    "status": "error",
                    "message": f"Twitter API error: {str(e)}"
                }
        
        except Exception as e:
            logger.error(f"Error handling Twitter callback: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to handle Twitter callback: {str(e)}"
            }
    
    def get_twitter_client(self, client_id: str) -> Tuple[bool, Any]:
        """
        Get authenticated Twitter API client for a client
        
        Args:
            client_id: Client ID to get Twitter client for
            
        Returns:
            Tuple of (success, api_client)
        """
        try:
            # Get auth data
            db = get_db()
            auth_data = db.get_twitter_auth(client_id)
            
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            # Check if we have OAuth tokens
            if "oauth_token" not in auth_data or "oauth_token_secret" not in auth_data:
                return False, {
                    "status": "error",
                    "message": "Missing OAuth tokens"
                }
            
            # Create OAuth1 handler
            auth = tweepy.OAuth1UserHandler(
                self.twitter_api_key,
                self.twitter_api_secret
            )
            
            # Set access token
            auth.set_access_token(
                auth_data["oauth_token"],
                auth_data["oauth_token_secret"]
            )
            
            # Create API client
            api = tweepy.API(auth)
            
            # Verify credentials
            api.verify_credentials()
            
            return True, api
        
        except tweepy.TweepyException as e:
            logger.error(f"Tweepy error getting client: {str(e)}")
            
            # Check if this is an authentication error
            if "401" in str(e):
                # Authentication issue, try to refresh or prompt re-auth
                return False, {
                    "status": "error",
                    "error_type": "auth_expired",
                    "message": "Twitter authentication has expired or been revoked"
                }
            
            return False, {
                "status": "error",
                "message": f"Twitter API error: {str(e)}"
            }
        
        except Exception as e:
            logger.error(f"Error getting Twitter client: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get Twitter client: {str(e)}"
            }
    
    def refresh_twitter_token(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Refresh Twitter access token for a client
        Note: OAuth 1.0a tokens don't expire, but this method
        can be used to verify and update token data if needed
        
        Args:
            client_id: Client ID to refresh token for
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            # Get current auth data
            db = get_db()
            auth_data = db.get_twitter_auth(client_id)
            
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            # Verify the existing tokens
            success, result = self.get_twitter_client(client_id)
            
            if not success:
                # If we get an auth error, the tokens are invalid
                if isinstance(result, dict) and result.get("error_type") == "auth_expired":
                    # Tokens are invalid/revoked, prompt for re-auth
                    # Delete the invalid tokens
                    db.delete_twitter_auth(client_id)
                    
                    # Return specific error
                    return False, {
                        "status": "error",
                        "error_type": "reauth_required",
                        "message": "Authentication expired or revoked, re-authentication required"
                    }
                
                # Some other error
                return False, result
            
            # Tokens are still valid, update the expires_at field
            auth_data["expires_at"] = (datetime.now() + timedelta(days=30)).isoformat()
            auth_data["updated_at"] = datetime.now().isoformat()
            
            db.store_twitter_auth(client_id, auth_data)
            
            return True, {
                "status": "success",
                "message": "Token verified successfully"
            }
        
        except Exception as e:
            logger.error(f"Error refreshing Twitter token: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to refresh Twitter token: {str(e)}"
            }
    
    def revoke_twitter_auth(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Revoke Twitter authentication for a client
        
        Args:
            client_id: Client ID to revoke auth for
            
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
            
            # Get current auth data
            db = get_db()
            auth_data = db.get_twitter_auth(client_id)
            
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Client not authenticated with Twitter"
                }
            
            # For OAuth 1.0a, we can't revoke tokens from the client side
            # We simply delete them from our database
            
            # If we had OAuth 2.0, we'd make a revocation request here
            
            # Remove auth data from database
            db.delete_twitter_auth(client_id)
            
            return True, {
                "status": "success",
                "message": "Authentication revoked successfully"
            }
        
        except Exception as e:
            logger.error(f"Error revoking Twitter auth: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to revoke Twitter auth: {str(e)}"
            }
    
    def get_twitter_auth_status(self, client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get Twitter authentication status for a client
        
        Args:
            client_id: Client ID to get auth status for
            
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
            
            # Get auth data
            db = get_db()
            auth_data = db.get_twitter_auth(client_id)
            
            if not auth_data:
                return True, {
                    "status": "success",
                    "is_authenticated": False
                }
            
            # Check if we need to verify tokens
            # OAuth 1.0a tokens don't expire, but we'll periodically verify them
            expires_at = None
            try:
                if "expires_at" in auth_data:
                    expires_at = datetime.fromisoformat(auth_data["expires_at"])
            except (ValueError, TypeError):
                pass
            
            is_expired = False
            if expires_at and datetime.now() > expires_at:
                is_expired = True
                
                # Try to verify the tokens
                success, _ = self.get_twitter_client(client_id)
                if success:
                    # Tokens are still good, update expiration
                    is_expired = False
                    auth_data["expires_at"] = (datetime.now() + timedelta(days=30)).isoformat()
                    auth_data["updated_at"] = datetime.now().isoformat()
                    db.store_twitter_auth(client_id, auth_data)
            
            # Format response
            username = auth_data.get("username", "")
            user_id = auth_data.get("user_id", "")
            user_name = auth_data.get("user_name", "")
            profile_image_url = auth_data.get("profile_image_url", "")
            
            return True, {
                "status": "success",
                "is_authenticated": True,
                "is_expired": is_expired,
                "username": username,
                "user_id": user_id,
                "user_name": user_name,
                "profile_image_url": profile_image_url,
                "authenticated_at": auth_data.get("created_at")
            }
        
        except Exception as e:
            logger.error(f"Error getting Twitter auth status: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get Twitter auth status: {str(e)}"
            }


# Create a singleton instance
auth_service = AuthService() 