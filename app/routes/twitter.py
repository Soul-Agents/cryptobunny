import json
from flask import Blueprint, request, jsonify
import tweepy
from datetime import datetime, timezone

from app.utils.db import get_db
from app.config.config import Config
from app.utils.encryption import decrypt_dict_values,SENSITIVE_FIELDS
from app.utils.protect import require_auth

# Create Blueprint
twitter_bp = Blueprint('twitter', __name__, url_prefix='/twitter')

@twitter_bp.route('/auth/<client_id>', methods=['DELETE'])
@require_auth
def delete_twitter_auth(client_id):
    """
    Delete Twitter authentication information for a client
    """
    try:
        db = get_db()
        result = db.delete_twitter_auth(client_id)
        
        return jsonify({
            "status": "success",
            "message": result['message']
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to delete Twitter authentication: {str(e)}"
        }), 500


@twitter_bp.route('/validate-credentials', methods=['POST'])
def validate_twitter_credentials():
    """
    Validate Twitter API credentials without saving them
    Useful for testing if credentials are valid before saving
    """
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Validate required fields
        required_fields = [
            'api_key',
            'api_secret_key',
            'bearer_token',
            'access_token',
            'access_token_secret',
        ]
        
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Verify the credentials by making a test API call
        try:
            client = tweepy.Client(
                consumer_key=data['api_key'],
                consumer_secret=data['api_secret_key'],
                access_token=data['access_token'],
                access_token_secret=data['access_token_secret'],
                bearer_token=data['bearer_token']
            )
            
            # Get the user's information
            user = client.get_me(user_auth=True)
            
            if not user or not user.data:
                return jsonify({
                    'status': 'error',
                    'message': 'Could not verify Twitter credentials. Please check the provided keys and tokens.'
                }), 400
                
            user_id = user.data.id
            user_name = user.data.username
            
            return jsonify({
                'status': 'success',
                'message': 'Twitter credentials verified successfully',
                'data': {
                    'user_id': user_id,
                    'user_name': user_name
                }
            }), 200
            
        except Exception as twitter_error:
            return jsonify({
                'status': 'error',
                'message': f'Failed to verify Twitter credentials: {str(twitter_error)}'
            }), 400
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to validate Twitter credentials: {str(e)}'
        }), 500

@twitter_bp.route('/post-tweet/<client_id>', methods=['POST'])
def post_tweet(client_id):
    """
    Post a tweet on behalf of a user using their stored credentials
    """
    try:
        # Get request data
        data = request.json
   
        
        if not data or 'reply_content' not in data:
            return jsonify({
                "status": "error",
                "message": "Tweet text is required in the request body"
            }), 400
        
        tweet_text = data['reply_content']
        tweet_id = data['tweet_id']

        
        # Get the user's auth data from database
        db = get_db()
        auth_data = db.get_twitter_auth(client_id)
        if not auth_data:
            return jsonify({
                "status": "error",
                "message": "No authentication data found for this client ID"
            }), 404
        
        # Initialize Tweepy client with the stored credentials

        decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        client = tweepy.Client(
            consumer_key=decrypted_auth["api_key"],
            consumer_secret=decrypted_auth["api_secret_key"],
            access_token=decrypted_auth["access_token"],
            access_token_secret=decrypted_auth["access_token_secret"]
        )
        
       
        # Post the tweet
        try:

            if len(tweet_text) > 280:
                return jsonify({
                "status": "error",
                "message": f"Tweet exceeds 280 character limit (current: {len(tweet_text)})"
            }), 400

            if tweet_id:
                response = client.create_tweet(text=tweet_text,in_reply_to_tweet_id=tweet_id)
            else:
                response = client.create_tweet(text=tweet_text)
            
            new_tweet_id= response.data["id"]
            
            # Store the tweet in our database
            tweet_data = {
                "tweet_id": str(new_tweet_id),
                "user_id": auth_data["user_id"],
                "text": tweet_text,
                "created_at": datetime.now(timezone.utc),
                "saved_at": datetime.now(timezone.utc),
                "type": "ai_generated" 
            }
            
            db.add_written_ai_tweet(auth_data["user_id"], tweet_data)
            
            return jsonify({
                "status": "success",
                "message": "Tweet posted successfully",
                "tweet_id": new_tweet_id,
                "reply_content": tweet_text
            })
            
        except Exception as tweet_error:
            error_message = str(tweet_error)
            print(f"Error posting tweet: {error_message}")
            return jsonify({
                "status": "error",
                "message": f"Failed to post tweet: {error_message}"
            }), 500
    
    except Exception as e:
        error_message = str(e)
        print(f"Error in post_tweet: {error_message}")
        return jsonify({
            "status": "error",
            "message": f"Failed to post tweet: {error_message}"
        }), 500

@twitter_bp.route('/users', methods=['GET'])
def get_all_users():
    """
    Get all Twitter users who have connected their accounts
    """
    try:
        db = get_db()
        agents = list(db.get_all_active_paid_agents())
        # Find all users with minimal information for security
        users = list(db.twitter_auth.find({}, {
            "client_id": 1,
            "user_id": 1,
            "user_name": 1,
            "created_at": 1,
            "updated_at": 1,
            "username": 1,
            "_id": 0  # Exclude MongoDB _id
        }))
        
        # Convert dates to string for JSON serialization
        users_json = json.loads(json.dumps(users, default=str))
        agents_json = json.loads(json.dumps(agents, default=str))
        return jsonify({
            "status": "success",
            "count": len(users_json),
            "users": users_json,
            "agents": agents_json
        })
    
    except Exception as e:
        error_message = str(e)
        print(f"Error getting all users: {error_message}")
        return jsonify({
            "status": "error",
            "message": f"Failed to get users: {error_message}"
        }), 500

@twitter_bp.route('/check-connection/<client_id>', methods=['GET'])
@require_auth
def check_twitter_connection(client_id):
    """
    Check if Twitter connection is working properly for a client
    """
    try:
        print(f"Checking Twitter connection for client_id: {client_id}")
        
        db = get_db()
        auth_data = db.get_twitter_auth(client_id)
        
        if not auth_data or not isinstance(auth_data, dict):
            return jsonify({
                "status": "error",
                "message": "No Twitter authentication found",
                "error_type": "not_found",
                "recommendation": "Please authenticate with Twitter first"
            }), 404
        
        # Check if required credentials exist
        required_fields = ["api_key", "api_secret_key", "access_token", "access_token_secret"]
        missing_fields = [field for field in required_fields if not auth_data.get(field)]
        
        if missing_fields:
            return jsonify({
                "status": "error",
                "message": f"Twitter authentication data is incomplete. Missing: {', '.join(missing_fields)}",
                "error_type": "incomplete_data",
                "recommendation": "Please reconnect your Twitter account"
            }), 400
        
        try:
            # Decrypt sensitive fields
            decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
            
            # Create client with the stored credentials
            client = tweepy.Client(
                consumer_key=decrypted_auth["api_key"],
                consumer_secret=decrypted_auth["api_secret_key"],
                access_token=decrypted_auth["access_token"],
                access_token_secret=decrypted_auth["access_token_secret"]
            )
            
            # Test: Get user info and verify permissions
            user = client.get_me()
            if not user or not user.data:
                return jsonify({
                    "status": "error",
                    "message": "Could not retrieve user information",
                    "error_type": "api_error",
                    "recommendation": "Please check your Twitter credentials"
                }), 400
            
            return jsonify({
                "status": "success",
                "message": "Twitter connection is working properly",
                "data": {
                    "user_id": user.data.id,
                    "user_name": user.data.username,
                    "verified": True
                }
            })
            
        except tweepy.TweepyException as tweet_error:
            error_str = str(tweet_error)
            print(f"Twitter API Error: {error_str}")
            
            # Determine specific error type
            error_type = "unknown"
            recommendation = "Please try reconnecting your Twitter account"
            
            if "401" in error_str:
                error_type = "unauthorized"
                recommendation = "Your Twitter credentials have expired or been revoked. Check your API keys and tokens."
            elif "403" in error_str:
                error_type = "forbidden"
                recommendation = "Your Twitter app doesn't have permission to perform this action. Check your app permissions."
            elif "404" in error_str:
                error_type = "not_found"
                recommendation = "Twitter user account not found. The account may have been deleted or suspended."
            elif "429" in error_str:
                error_type = "rate_limit"
                recommendation = "Twitter rate limit exceeded. Please try again later."
            
            return jsonify({
                "status": "error",
                "message": f"Twitter API error: {error_str}",
                "error_type": error_type,
                "recommendation": recommendation,
                "reconnect_url": f"/connect-twitter-account?client_id={client_id}"
            }), 401
    
    except Exception as e:
        print(f"Internal Error in check_twitter_connection: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Failed to check Twitter connection: {str(e)}",
            "error_type": "server_error",
            "recommendation": "Please try again later or contact support"
        }), 500 