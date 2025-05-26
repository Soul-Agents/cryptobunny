import os
import uuid
import json
from flask import Blueprint, request, jsonify, redirect, session, url_for
import tweepy
from datetime import datetime, timezone
from pymongo import MongoClient
from app.utils.db import get_db
from app.models.twitter import TwitterAuth
from app.models.agent import AgentConfig
from app.config.config import Config
from app.utils.encryption import encrypt_dict_values, decrypt_dict_values
from app.utils.protect import require_auth
from app.utils.bearer import generate_bearer_token
# from jwt import jwt
# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Twitter API configuration from config
TWITTER_CALLBACK_URL = Config.TWITTER_CALLBACK_URL
FRONTEND_URL = Config.FRONTEND_URL

# Define which fields should be encrypted
SENSITIVE_FIELDS = [
    'api_key',
    'api_secret_key',
    'access_token',
    'access_token_secret',
    'bearer_token',
    'temp_request_token',
    'temp_request_secret'
]




@auth_bp.route('/save-twitter-keys', methods=['POST'])
@require_auth
def save_twitter_keys():
    """
    Save Twitter API key and API secret key from the frontend with encryption
    """
    try:
        # Extract data from request
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Extract required fields
        apiKey = data.get('apiKey')
        apiSecretKey = data.get('apiSecretKey')
        clientId = data.get('clientId', str(uuid.uuid4()))
        
        # Validate required fields
        if not apiKey or not apiSecretKey:
            return jsonify({
                "status": "error",
                "message": "API key and API secret key are required"
            }), 400
        
        # Create or update auth record in the database
        db = get_db()
        
        # Check if this client_id already exists
        existing_auth = db.twitter_auth.find_one({"client_id": clientId})
        
        # Check if there are agent configurations for this client
        agent_configs = list(db.agent_config.find({"client_id": clientId}))
        has_agent_config = len(agent_configs) > 0
        bearer_token = generate_bearer_token(apiKey, apiSecretKey)
        # Prepare auth data with encryption
        auth_data = {
            "client_id": clientId,
            "api_key": apiKey,
            "api_secret_key": apiSecretKey,
            "bearer_token": bearer_token,
            "has_agent_config": has_agent_config,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Encrypt sensitive data
        auth_data = encrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        
        if existing_auth:
            # Update existing record
            result = db.twitter_auth.update_one(
                {"client_id": clientId},
                {"$set": auth_data}
            )
            message = "Twitter API keys updated successfully"
        else:
            # Create new record
            auth_data["created_at"] = datetime.now(timezone.utc)
            result = db.twitter_auth.insert_one(auth_data)
            message = "Twitter API keys saved successfully"
        
        # Update agent configuration
        db.agent_config.update_one(
            {"client_id": clientId},
            {"$set": {
                "has_twitter_keys": True,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return jsonify({
            "status": "success",
            "message": message,
            "client_id": clientId,
            "has_agent_config": has_agent_config
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to save Twitter API keys: {str(e)}"
        }), 500

@auth_bp.route('/api-keys/<client_id>', methods=['DELETE'])
def delete_twitter_credentials(client_id):
    """
    Delete Twitter API keys from the database
    """
    try:
        db = get_db()
        auth = db.twitter_auth.find_one({"client_id": client_id})
        if not auth:
            return jsonify({
                "success": False,
                "message": "Twitter API keys not found"
            }), 404
        db.twitter_auth.update_one(
            {"client_id": client_id},
            {"$set": {
                "api_key": None,
                "api_secret_key": None,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return jsonify({
            "success": True,
            "message": "Twitter API keys deleted successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to delete Twitter API keys: {str(e)}"
        }), 500



# @auth_bp.route('/credentials/<client_id>', methods=['GET'])
# def twitter_credentials(client_id):
#     """
#     Get Twitter API credentials with decryption
    
#     Accepts client_id either as:
#     - a path parameter (/credentials/123123)
#     - a query parameter (/credentials?client_id=123123)
#     - a query parameter with camelCase (/credentials?clientId=123123)
#     """
#     # If client_id was not provided as a path parameter, try to get it from query parameters
#     if not client_id:
#         client_id = request.args.get('client_id')
#         # Also check for camelCase clientId
#         if not client_id:
#             client_id = request.args.get('clientId')
    
#     try:
#         if not client_id:
#             return jsonify({
#                 "status": "error",
#                 "message": "No client ID provided"
#             }), 400
        
#         # Store the client ID in the session
#         session['client_id'] = client_id
        
#         # Get Twitter API credentials from database
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
        
#         # Check if auth_data is valid and contains API keys
#         if not auth_data or not isinstance(auth_data, dict):
#             return jsonify({
#                 "status": "error",
#                 "message": "No Twitter authentication data found for this client ID. Please initialize with API keys first."
#             }), 400
        
#         # Decrypt the sensitive data
#         decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        
#         # Get API keys from decrypted auth data
#         api_key = decrypted_auth.get("api_key")
#         api_secret = decrypted_auth.get("api_secret_key")
        
#         if not api_key or not api_secret:
#             return jsonify({
#                 "status": "error",
#                 "message": "Twitter API keys are missing from authentication data"
#             }), 400
        
#         return jsonify({
#             "status": "success",
#             "api_key": api_key,
#             "api_secret": api_secret    
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to retrieve Twitter credentials: {str(e)}"
#         }), 500

@auth_bp.route('/connect-twitter-account', methods=['POST'])
def connect_twitter_account():
    """
    Start the Twitter OAuth flow with a simplified user experience
    """
    try:
        print(request.json, "REQUEST JSON")
        # Get client ID from request data
        client_id = request.json.get('client_id')
        print(client_id, "CLIENT ID")
        
        # Only generate a new client ID if one is not provided
        if not client_id:
            client_id = str(uuid.uuid4())
            print(f"No client ID provided, generated new ID: {client_id}")
        else:
            print(f"Using provided client ID: {client_id}")
        
        # Get the redirect URL from query param for frontend callback
        redirect_url = request.args.get('redirect_url', FRONTEND_URL)
        
        # Store the redirect URL and client ID in the session
        session['redirect_url'] = redirect_url
        session['client_id'] = client_id
        
        # Log session data for debugging
        print(f"Session data stored: client_id={client_id}, redirect_url={redirect_url}")
        print(f"Session object: {session}")
        
        db = get_db()
        auth_data = db.get_twitter_auth(client_id)
        print(auth_data, "AUTH DATA")
        
        # Check if auth_data is valid
        if not auth_data or not isinstance(auth_data, dict):
            return jsonify({
                "status": "error",
                "message": "No Twitter authentication data found for this client ID. Please initialize with API keys first."
            }), 400
        
        # Safely get API keys
        decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        api_key = decrypted_auth.get("api_key")
        api_secret = decrypted_auth.get("api_secret_key")
        
        if not api_key or not api_secret:
            return jsonify({
                "status": "error",
                "message": "Twitter API keys are missing from authentication data"
            }), 400
        
        # Log the API key being used (first few chars only for security)
        print(f"Using API key: {api_key[:4]}...")
        print(TWITTER_CALLBACK_URL, "TWITTER CALLBACK URL")
        # Initialize OAuth1UserHandler with application credentials
        oauth1_user_handler = tweepy.OAuth1UserHandler(
            api_key,
            api_secret,
            callback=TWITTER_CALLBACK_URL
        )
        
        # Get the authorization URL
        auth_url = oauth1_user_handler.get_authorization_url()
        
        # Store the request token and secret
        request_token = oauth1_user_handler.request_token['oauth_token']
        request_secret = oauth1_user_handler.request_token['oauth_token_secret']

        # Store request tokens in the database instead of the session
        db.twitter_auth.update_one(
            {"client_id": client_id},
            {"$set": {
                "temp_request_token": request_token,
                "temp_request_secret": request_secret,
                "temp_redirect_url": redirect_url,
                "temp_updated_at": datetime.now(timezone.utc),
                "oauth_token": request_token
            }}
        )
        twitter_auth = db.get_twitter_auth(client_id)
        print(twitter_auth, "TWITTER AUTH")
        print(f"Storing in database: token={request_token}, secret={request_secret}")
        
        # Return the auth URL for the frontend to redirect the user to Twitter
        return jsonify({
            "status": "success",
            "message": "Twitter authentication flow started",
            "auth_url": auth_url,
            "client_id": client_id,
            "redirect_url": redirect_url,
            "instructions": {
                "step1": "Redirect user to the auth_url (window.location.href or window.open)",
                "step2": "Twitter will handle the authentication and redirect to our backend",
                "step3": "Our backend will process the callback and redirect to your redirect_url",
                "step4": "Check authentication status using /twitter-callback-status?client_id=YOUR_CLIENT_ID"
            }
        })
    
    except Exception as e:
        error_message = str(e)
        print(f"Error in connect_twitter_account: {error_message}")
        return jsonify({
            "status": "error",
            "message": f"Failed to start Twitter authentication: {error_message}"
        }), 500

@auth_bp.route('/callback', methods=['GET'])
def twitter_callback():
    """
    Handle Twitter OAuth callback with encrypted storage
    """
    try:
        oauth_verifier = request.args.get('oauth_verifier')
        oauth_token = request.args.get('oauth_token')
        if not oauth_verifier:
            return jsonify({
                "status": "error",
                "message": "OAuth verifier is missing"
            }), 400
        
        client_id = session.get('client_id')
        redirect_url = session.get('redirect_url', FRONTEND_URL)
        
        db = get_db()
        auth_record = db.twitter_auth.find_one({"oauth_token": oauth_token})
        
        if auth_record:
            client_id = auth_record.get("client_id")
            # Decrypt the tokens for authentication
            decrypted_record = decrypt_dict_values(auth_record, SENSITIVE_FIELDS)
            request_token = decrypted_record.get("temp_request_token")
            request_secret = decrypted_record.get("temp_request_secret")
            redirect_url = decrypted_record.get("temp_redirect_url", FRONTEND_URL)
        else:
            request_token = session.get('request_token')
            request_secret = session.get('request_secret')
        
        if not client_id or not request_token:
            return jsonify({
                "status": "error",
                "message": "Request token or client ID is missing. Authentication flow may have expired."
            }), 400
        
        # Get and decrypt auth data
        auth_data = db.get_twitter_auth(client_id)
        decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        API_KEY = decrypted_auth["api_key"]
        API_SECRET = decrypted_auth["api_secret_key"]
        
        new_oauth1_user_handler = tweepy.OAuth1UserHandler(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            callback=TWITTER_CALLBACK_URL
        )
        new_oauth1_user_handler.request_token = {
            "oauth_token": request_token,
            "oauth_token_secret": request_secret
        }
        
        # Get the access token
        access_token, access_token_secret = new_oauth1_user_handler.get_access_token(oauth_verifier)
        
        # Initialize Tweepy client
        client = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Get the authenticated user
        user = client.get_me(user_auth=True)
        
        

        # Create the auth data object
        auth_data = {
            "client_id": client_id,
            "user_id": user.data.id,
            "username": user.data.username,
            "api_key": API_KEY,
            "api_secret_key": API_SECRET,
            "bearer_token": "",
            "access_token": access_token,
            "access_token_secret": access_token_secret,
            "updated_at": datetime.now(timezone.utc),
            # "temp_request_token": None,
            # "temp_request_secret": None,
            # "temp_redirect_url": None,
            # "temp_updated_at": None
        }
        
        # Encrypt sensitive data before saving
        encrypted_auth_data = encrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        encrypted_auth_data["created_at"] = datetime.now(timezone.utc)
        
        # Save to database
        result = db.add_twitter_auth(TwitterAuth(**encrypted_auth_data))

        agent_config = db.agent_config.update_one(
            {"client_id": client_id},
            {"$set": {
                "agent_name": user.data.username,
                "updated_at": datetime.now(timezone.utc),
                "is_twitter_authorized": True
            }}
        )
        frontend_redirect = f"{redirect_url}/app/payment?client_id={client_id}&auth=success&username={user.data.username}"
        return redirect(frontend_redirect)
    
    except Exception as e:
        error_message = str(e)
        print(f"Error in Twitter callback: {error_message}")
        error_redirect = f"{FRONTEND_URL}?auth=error&message={error_message}"
        return redirect(error_redirect)

@auth_bp.route('/users', methods=['GET'])
@require_auth
def users():
    """
    Get all users with sensitive data removed
    """
    db = get_db()   
    users = db.twitter_auth.find()
    users_list = list(users)
    
    # Filter out sensitive data
    safe_users = []
    for user in users_list:
        safe_user = {
            "client_id": user.get("client_id"),
            "username": user.get("username"),
            "user_id": user.get("user_id"),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at"),
            "has_agent_config": user.get("has_agent_config", False)
        }
        safe_users.append(safe_user)
    
    users_list_json = json.loads(json.dumps(safe_users, default=str))
    return jsonify({
        "status": "success",
        "message": "Users retrieved successfully",
        "users": users_list_json
    }), 200
    
@auth_bp.route('/status/<client_id>', methods=['GET'])
@require_auth
def auth_status(client_id=None):
    """
    Check authentication status for a client
    
    Accepts client_id either as:
    - a path parameter (/status/123123)
    - a query parameter (/status?client_id=123123)
    - a query parameter with camelCase (/status?clientId=123123)
    """
    # If client_id was not provided as a path parameter, try to get it from query parameters
    if not client_id:
        client_id = request.args.get('client_id')
        # Also check for camelCase clientId
        if not client_id:
            client_id = request.args.get('clientId')
    
    if not client_id:
        return jsonify({
            "status": "error",
            "authenticated": False,
            "message": "No client ID provided"
        }), 400
    
    db = get_db()
    auth_data = db.get_twitter_auth(client_id)
    print(auth_data, "AUTH DATA")
    if not auth_data:
        return jsonify({
            "status": "error",
            "authenticated": False,
            "message": "Not authenticated"
        }), 401
    
    safe_auth_data = {
        "client_id": auth_data["client_id"],
        # "user_id": auth_data["user_id"],
        # "user_name": auth_data["user_name"],
        "created_at": auth_data["created_at"],
        "updated_at": auth_data["updated_at"]
    }
    
    # Convert ObjectId to string for JSON serialization
    safe_auth_data_json = json.loads(json.dumps(safe_auth_data, default=str))
    
    return jsonify({
        "status": "success",
        "authenticated": True,
        "auth_data": safe_auth_data_json
    })