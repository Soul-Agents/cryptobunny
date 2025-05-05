# import os
# import uuid
# import json
# from flask import Flask, request, jsonify, redirect, session, url_for
# from flask_cors import CORS
# import tweepy 
# from datetime import datetime, timezone
# from dotenv import load_dotenv
# from typing import Dict, Any, List, Optional
# from schemas import TwitterAuth, AgentConfig
# from db import TweetDB
# import main  # Import main module for agent execution
# import random

# # Load environment variables
# load_dotenv()

# # Initialize Flask application
# app = Flask(__name__)
# app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
# CORS(app, supports_credentials=True)  # Enable credential support for CORS

# # Twitter API configuration
# TWITTER_API_KEY = os.getenv("API_KEY")
# TWITTER_API_SECRET = os.getenv("API_SECRET_KEY")
# TWITTER_CALLBACK_URL = os.getenv("TWITTER_CALLBACK_URL", "http://localhost:8000/callback")
# print(TWITTER_CALLBACK_URL, "TWITTER CALLBACK URL")
# # Frontend URL for redirects after auth
# FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# def get_db():
#     return TweetDB()

# # ----- Frontend Routes -----

# @app.route('/', methods=['GET'])
# def index():
#     """
#     API home page
#     """
#     return jsonify({
#         "status": "success",
#         "message": "CryptoBunny API is running",
#         "version": "1.0.0",
#         "endpoints": {
#             "auth": "/auth/twitter",
#             "templates": "/agent-templates",
#             "configurations": "/agent-config/{client_id}",
#             "run_agent": "/run-agent/{client_id}/{agent_name}"
#         }
#     })

# @app.route('/login', methods=['GET'])
# def login():
#     """
#     Frontend login endpoint - redirects to Twitter auth
#     """
#     # Get the redirect URL from query param for frontend callback
#     redirect_url = request.args.get('redirect_url', FRONTEND_URL)
    
#     # Store the redirect URL in the session
#     session['redirect_url'] = redirect_url
    
#     # Generate a client ID if not provided
#     client_id = request.args.get('client_id')
#     if not client_id:
#         client_id = str(uuid.uuid4())
    
#     # Redirect to Twitter auth endpoint
#     return redirect(url_for('twitter_auth', client_id=client_id))

# @app.route('/auth/status', methods=['GET'])
# def auth_status():
#     """
#     Check authentication status for a client
#     """
#     client_id = request.args.get('client_id')
    
#     if not client_id:
#         return jsonify({
#             "status": "error",
#             "authenticated": False,
#             "message": "No client ID provided"
#         }), 400
    
#     db = get_db()
#     auth_data = db.get_twitter_auth(client_id)
    
#     if not auth_data:
#         return jsonify({
#             "status": "error",
#             "authenticated": False,
#             "message": "Not authenticated"
#         }), 401
    
#     safe_auth_data = {
#         "client_id": auth_data["client_id"],
#         "user_id": auth_data["user_id"],
#         "user_name": auth_data["user_name"],
#         "created_at": auth_data["created_at"],
#         "updated_at": auth_data["updated_at"]
#     }
    
#     # Convert ObjectId to string for JSON serialization
#     safe_auth_data_json = json.loads(json.dumps(safe_auth_data, default=str))
    
#     return jsonify({
#         "status": "success",
#         "authenticated": True,
#         "auth_data": safe_auth_data_json
#     })

# @app.route('/dashboard/<client_id>', methods=['GET'])
# def dashboard(client_id):
#     """
#     Get dashboard data for a client
#     """
#     try:
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
        
#         if not auth_data:
#             return jsonify({
#                 "status": "error",
#                 "message": "Not authenticated"
#             }), 401
        
#         # Get all agent configurations for the client
#         configs = db.get_all_agent_configs(client_id)
#         configs_json = json.loads(json.dumps(configs, default=str))
        
#         # Get all agent templates from the database
#         templates = {}
#         template_configs = db.agent_config.find({}, {"agent_name": 1, "user_personality": 1, "model_config": 1})
        
#         for config in template_configs:
#             agent_name = config.get("agent_name")
#             if agent_name and agent_name not in templates:
#                 templates[agent_name] = {
#                     "name": agent_name,
#                     "description": config.get("user_personality", "").split('\n')[0][:100] + "..." if config.get("user_personality") else "",
#                     "model": config.get("model_config", {}).get("type", "unknown")
#                 }
        
#         # Format user data for dashboard
#         user_data = {
#             "user_id": auth_data["user_id"],
#             "user_name": auth_data["user_name"],
#             "created_at": auth_data["created_at"],
#             "updated_at": auth_data["updated_at"]
#         }
#         user_data_json = json.loads(json.dumps(user_data, default=str))
        
#         return jsonify({
#             "status": "success",
#             "user": user_data_json,
#             "agent_count": len(configs),
#             "agents": configs_json,
#             "templates": templates
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get dashboard data: {str(e)}"
#         }), 500

# @app.route('/run-agent/<client_id>/<agent_name>', methods=['POST'])
# def run_agent(client_id, agent_name):
#     """
#     Run an agent with a specific prompt or action
#     """
#     try:
#         # Get the request data
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No data provided"
#             }), 400
        
#         # Validate required fields
#         action = data.get('action', 'default')
#         question = data.get('question')
        
#         if not question and action == 'custom':
#             return jsonify({
#                 "status": "error",
#                 "message": "Question is required for custom action"
#             }), 400
        
#         # Load the agent configuration
#         agent_config = main.load_agent_config(client_id, agent_name)
        
#         if not agent_config:
#             return jsonify({
#                 "status": "error",
#                 "message": f"Agent configuration not found for {client_id}/{agent_name}"
#             }), 404
        
#         # Use the session ID for memory persistence
#         session_id = f"{client_id}_{agent_name}"
        
#         # Select a random question from the agent's question bank if using default action
#         if action == 'default' or not question:
#             questions = agent_config.get("QUESTION", [])
#             if questions and isinstance(questions, list) and len(questions) > 0:
#                 question = random.choice(questions)
#             else:
#                 question = "What interesting topics should I engage with today?"
        
#         # Store original values to restore later
#         original_user_id = main.USER_ID
#         original_user_name = main.USER_NAME
        
#         try:
#             # Set global variables with our configuration
#             main.set_global_agent_variables(agent_config)
            
#             # Check if LLM is available
#             if not main.llm:
#                 return jsonify({
#                     "status": "error",
#                     "message": "Language model not available. Please check your API key configuration."
#                 }), 500
            
#             # Execute the agent
#             result = main.run_crypto_agent(question, session_id)
            
#             return jsonify({
#                 "status": "success",
#                 "message": "Agent executed successfully",
#                 "result": result,
#                 "question": question
#             })
        
#         finally:
#             # Restore original variables
#             main.USER_ID = original_user_id
#             main.USER_NAME = original_user_name
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to run agent: {str(e)}"
#         }), 500

# @app.route('/agent-history/<client_id>/<agent_name>', methods=['GET'])
# def get_agent_history(client_id, agent_name):
#     """
#     Get activity history for a specific agent
#     """
#     try:
#         db = get_db()
        
#         # Verify the agent exists
#         agent_config = db.get_agent_config(client_id, agent_name)
        
#         if not agent_config:
#             return jsonify({
#                 "status": "error",
#                 "message": f"No agent configuration found for {client_id}/{agent_name}"
#             }), 404
        
#         # Get the most recent tweets posted by this agent
#         user_id = agent_config["user_id"]
#         tweets = db.get_last_written_ai_tweets(user_id, limit=10)
        
#         # Get the most recent replies posted by this agent
#         replies = db.get_last_written_ai_tweet_replies(user_id, limit=10)
        
#         # Format the data for JSON response
#         tweets_json = json.loads(json.dumps(tweets, default=str))
#         replies_json = json.loads(json.dumps(replies, default=str))
        
#         return jsonify({
#             "status": "success",
#             "tweets": tweets_json,
#             "replies": replies_json
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get agent history: {str(e)}"
#         }), 500

# @app.route('/create-agent/<client_id>', methods=['POST'])
# def create_agent_frontend(client_id):
#     """
#     Create a new agent with provided configuration
#     """
#     try:
#         # Get request data
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No data provided"
#             }), 400
        
#         # Validate required fields
#         agent_name = data.get('name')
        
#         if not agent_name:
#             return jsonify({
#                 "status": "error",
#                 "message": "Agent name is required"
#             }), 400
        
#         # Get the Twitter auth data to associate with this agent
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
        
#         if not auth_data:
#             return jsonify({
#                 "status": "error",
#                 "message": f"No Twitter authentication found for client ID: {client_id}"
#             }), 400
        
#         # Create agent data with default values and any provided overrides
#         agent_data = {
#             "client_id": client_id,
#             "agent_name": agent_name,
#             "user_id": auth_data['user_id'],
#             "user_name": auth_data['user_name'],
#             "user_personality": data.get("user_personality", ""),
#             "style_rules": data.get("style_rules", ""),
#             "content_restrictions": data.get("content_restrictions", ""),
#             "strategy": data.get("strategy", ""),
#             "remember": data.get("remember", ""),
#             "mission": data.get("mission", ""),
#             "questions": data.get("questions", []),
#             "engagement_strategy": data.get("engagement_strategy", ""),
#             "ai_and_agents": data.get("ai_and_agents", []),
#             "web3_builders": data.get("web3_builders", []),
#             "defi_experts": data.get("defi_experts", []),
#             "thought_leaders": data.get("thought_leaders", []),
#             "traders_and_analysts": data.get("traders_and_analysts", []),
#             "knowledge_base": data.get("knowledge_base", ""),
#             "model_config": data.get("model_config", {
#                 "type": "gpt-4",
#                 "temperature": 0.7,
#                 "top_p": 0.9,
#                 "presence_penalty": 0.6,
#                 "frequency_penalty": 0.6,
#             }),
#             "created_at": datetime.now(timezone.utc),
#             "updated_at": datetime.now(timezone.utc),
#             "is_active": False
#         }
        
#         # Save the configuration
#         result = db.add_agent_config(agent_data)
        
#         # Convert datetime to string for JSON serialization
#         agent_data_json = json.loads(json.dumps(agent_data, default=str))
        
#         return jsonify({
#             "status": "success",
#             "message": f"Agent '{agent_name}' created successfully",
#             "agent": agent_data_json
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to create agent: {str(e)}"
#         }), 500

# def create_agent_config_internal(data):
#     """
#     Internal function to create an agent configuration
#     """
#     try:
#         # Get client_id and agent_name
#         client_id = data['client_id']
#         agent_name = data['agent_name']
        
#         # Check if there's already a config in the database
#         db = get_db()
#         existing_config = db.get_agent_config(client_id, agent_name)
        
#         if existing_config:
#             # Update existing configuration with new values
#             for key in data:
#                 if key in existing_config and key not in ['client_id', 'agent_name', 'created_at']:
#                     existing_config[key] = data[key]
            
#             # Update the timestamp
#             existing_config['updated_at'] = datetime.now(timezone.utc)
            
#             # Save the updated configuration
#             result = db.add_agent_config(existing_config)
#             return existing_config
        
#         # Get the Twitter auth data to associate with this agent
#         auth_data = db.get_twitter_auth(client_id)
        
#         if not auth_data:
#             return {
#                 "status": "error",
#                 "message": f"No Twitter authentication found for client ID: {client_id}"
#             }
        
#         # Create a new config with default values
#         config_data = AgentConfig(
#             client_id=client_id,
#             agent_name=agent_name,
#             user_id=auth_data['user_id'],
#             user_name=auth_data['user_name'],
#             user_personality="",
#             style_rules="",
#             content_restrictions="",
#             strategy="",
#             remember="",
#             mission="",
#             questions=[],
#             engagement_strategy="",
#             ai_and_agents=[],
#             web3_builders=[],
#             defi_experts=[],
#             thought_leaders=[],
#             traders_and_analysts=[],
#             knowledge_base="",
#             model_config={
#                 "type": "gpt-4",
#                 "temperature": 0.7,
#                 "top_p": 0.9,
#                 "presence_penalty": 0.6,
#                 "frequency_penalty": 0.6,
#             },
#             created_at=datetime.now(timezone.utc),
#             updated_at=datetime.now(timezone.utc),
#             is_active=True
#         )
        
#         # Override with any custom data provided
#         for key in data:
#             if key in config_data and key not in ['client_id', 'agent_name', 'created_at']:
#                 if data[key] is not None:  # Only override if not None
#                     config_data[key] = data[key]
        
#         # Save the configuration
#         result = db.add_agent_config(config_data)
        
#         # Add relevant data to result
#         config_data["result"] = result
        
#         # Convert datetime to string for JSON serialization
#         config_data_json = json.loads(json.dumps(config_data, default=str))
        
#         return config_data_json
        
#     except Exception as e:
#         print(f"Error creating agent configuration: {str(e)}")
#         return {
#             "status": "error",
#             "message": f"Failed to create agent configuration: {str(e)}"
#         }

# # ----- Twitter Authentication -----

# @app.route('/auth/twitter', methods=['GET'])
# def twitter_auth():
#     """
#     Initiate Twitter OAuth flow
#     """
#     try:
#         # Generate a client ID if not provided
#         client_id = request.args.get('client_id')
#         if not client_id:
#             client_id = str(uuid.uuid4())
        
#         # Store the client ID in the session
#         session['client_id'] = client_id
        
#         # Initialize OAuth1UserHandler
#         oauth1_user_handler = tweepy.OAuth1UserHandler(
#             TWITTER_API_KEY,
#             TWITTER_API_SECRET,
#             callback=TWITTER_CALLBACK_URL
#         )
        
#         # Get the authorization URL
#         auth_url = oauth1_user_handler.get_authorization_url()
        
#         # Store the request token in the session
#         session['request_token'] = oauth1_user_handler.request_token
#         print(oauth1_user_handler.request_token, "REQUEST TOKEN")
#         # Redirect to Twitter authorization page
#         return redirect(auth_url)
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to initiate Twitter authentication: {str(e)}"
#         }), 500

# @app.route('/callback', methods=['GET'])
# def twitter_callback():
#     """
#     Handle Twitter OAuth callback
#     """
#     try:
#         # Verify the oauth_verifier is present
#         oauth_verifier = request.args.get('oauth_verifier')
#         print(oauth_verifier, "OAUTH VERIFIER")
#         oauth_token = request.args.get('oauth_token')
#         if not oauth_verifier:
#             return jsonify({
#                 "status": "error",
#                 "message": "OAuth verifier is missing"
#             }), 400
        
#         # Get the request token from the session
#         client_id = session.get('client_id')
#         redirect_url = session.get('redirect_url', FRONTEND_URL)
        
#         if  not client_id:
#             return jsonify({
#                 "status": "error",
#                 "message": "Request token or client ID is missing"
#             }), 400
        
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)  
#         API_KEY = auth_data["api_key"]
#         API_SECRET = auth_data["api_secret_key"]
#         print(API_KEY, API_SECRET, "API KEY AND SECRET")
#         # Initialize OAuth1UserHandler with the request token
#         oauth1_user_handler = tweepy.OAuth1UserHandler(
#             API_KEY,
#             API_SECRET,
#             callback=TWITTER_CALLBACK_URL
#         )
#         request_token = oauth1_user_handler.request_token["oauth_token"]

#         oauth1_user_handler.request_token = oauth_token

#         access_token, access_token_secret = oauth1_user_handler.get_access_token(oauth_verifier)
#         print("TOKENs", access_token, access_token_secret)
        
#         # Initialize Tweepy client with the access token
#         client = tweepy.Client(
#             consumer_key=API_KEY,
#             consumer_secret=API_SECRET,
#             access_token=access_token,
#             access_token_secret=access_token_secret
#         )
        
#         # Get the authenticated user
#         user = client.get_me(user_auth=True)
#         print(f"User: {user}")
#         # Create the auth data object
#         auth_data = {
#             "client_id": client_id,
#             "user_id": user.data.id,
#             "user_name": user.data.username,
#             "api_key": API_KEY,
#             "api_secret_key": API_SECRET,
#             "bearer_token": "",  # Not obtained through OAuth 1.0a
#             "access_token": access_token,
#             "access_token_secret": access_token_secret,
#             "updated_at": datetime.now(timezone.utc)
#         }
        
#         # Get database instance
        
#         # Check if this Twitter user_id already exists in our database
#         existing_auth = db.twitter_auth.find_one({"user_id": user.data.id})
        
#         if existing_auth:
#             # If this user already exists, update their client_id to the new one
#             # and update their access tokens
#             print(f"User {user.data.username} already exists, updating their credentials")
            
#             # Update auth_data with the existing record's creation date
#             auth_data["created_at"] = existing_auth.get("created_at", datetime.now(timezone.utc))
            
#             # Update the record
#             result = db.twitter_auth.update_one(
#                 {"user_id": user.data.id},
#                 {"$set": auth_data}
#             )
#         else:
#             # This is a new user, create a new record
#             print(f"Creating new auth record for user {user.data.username}")
#             auth_data["created_at"] = datetime.now(timezone.utc)
#             result = db.add_twitter_auth(TwitterAuth(**auth_data))
        
#         # Redirect to the frontend with client_id as a parameter
#         frontend_redirect = f"{redirect_url}?client_id={client_id}&auth=success&username={user.data.username}"
#         return redirect(frontend_redirect)
    
#     except Exception as e:
#         error_message = str(e)
#         print(f"Error in Twitter callback: {error_message}")
#         error_redirect = f"{FRONTEND_URL}?auth=error&message={error_message}"
#         return redirect(error_redirect)

# # ----- Agent Configuration -----

# @app.route('/agent-config', methods=['POST'])
# def create_agent_config():
#     """
#     Create or update an agent configuration
#     """
#     try:
#         # Get request data
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No data provided"
#             }), 400
        
#         # Validate required fields
#         required_fields = ['client_id', 'agent_name']
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({
#                     "status": "error",
#                     "message": f"Missing required field: {field}"
#                 }), 400
        
#         # Create agent configuration
#         result = create_agent_config_internal(data)
        
#         if 'status' in result and result['status'] == 'error':
#             return jsonify(result), 400
        
#         return jsonify({
#             "status": "success",
#             "message": "Agent configuration created successfully",
#             "configuration": result
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to create agent configuration: {str(e)}"
#         }), 500

# @app.route('/agent-config/<client_id>', methods=['GET'])
# def get_all_agent_configs(client_id):
#     """
#     Get all agent configurations for a client
#     """
#     try:
#         db = get_db()
#         configs = db.get_all_agent_configs(client_id)
        
#         # Convert ObjectId to string for JSON serialization
#         configs_json = json.loads(json.dumps(configs, default=str))
        
#         return jsonify({
#             "status": "success",
#             "configurations": configs_json
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get agent configurations: {str(e)}"
#         }), 500

# @app.route('/agent-config/<client_id>/<agent_name>', methods=['GET'])
# def get_agent_config(client_id, agent_name):
#     """
#     Get a specific agent configuration
#     """
#     try:
#         db = get_db()
#         config = db.get_agent_config(client_id, agent_name)
        
#         if not config:
#             return jsonify({
#                 "status": "error",
#                 "message": f"No configuration found for client ID: {client_id} and agent name: {agent_name}"
#             }), 404
        
#         # Convert ObjectId to string for JSON serialization
#         config_json = json.loads(json.dumps(config, default=str))
        
#         return jsonify({
#             "status": "success",
#             "configuration": config_json
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get agent configuration: {str(e)}"
#         }), 500

# @app.route('/agent-config/<client_id>/<agent_name>', methods=['PUT'])
# def update_agent_config(client_id, agent_name):
#     """
#     Update a specific agent configuration
#     """
#     try:
#         # Get request data
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No data provided"
#             }), 400
        
#         # Get the existing configuration
#         db = get_db()
#         existing_config = db.get_agent_config(client_id, agent_name)
        
#         if not existing_config:
#             return jsonify({
#                 "status": "error",
#                 "message": f"No configuration found for client ID: {client_id} and agent name: {agent_name}"
#             }), 404
        
#         # Update the configuration with the new data
#         for key in data:
#             if key in existing_config and key not in ['client_id', 'agent_name', 'created_at']:
#                 existing_config[key] = data[key]
        
#         # Update the updated_at timestamp
#         existing_config['updated_at'] = datetime.now(timezone.utc)
        
#         # Save the updated configuration
#         result = db.add_agent_config(existing_config)
        
#         return jsonify({
#             "status": "success",
#             "message": "Agent configuration updated successfully",
#             "result": result
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to update agent configuration: {str(e)}"
#         }), 500

# @app.route('/agent-config/<client_id>/<agent_name>', methods=['DELETE'])
# def delete_agent_config(client_id, agent_name):
#     """
#     Delete a specific agent configuration
#     """
#     try:
#         db = get_db()
#         result = db.delete_agent_config(client_id, agent_name)
        
#         return jsonify({
#             "status": "success",
#             "message": result['message']
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to delete agent configuration: {str(e)}"
#         }), 500

# @app.route('/agent-templates', methods=['GET'])
# def get_agent_templates():
#     """
#     Get all available agent templates
#     """
#     try:
#         # Get agent templates from database
#         db = get_db()
#         templates = {}
        
#         # Find distinct agent names
#         agent_configs = db.agent_config.find({}, {"agent_name": 1, "user_personality": 1, "model_config": 1})
        
#         for config in agent_configs:
#             agent_name = config.get("agent_name")
#             if agent_name and agent_name not in templates:
#                 templates[agent_name] = {
#                     "name": agent_name,
#                     "description": config.get("user_personality", "").split('\n')[0] if config.get("user_personality") else "",
#                     "model": config.get("model_config", {}).get("type", "unknown")
#                 }
        
#         return jsonify({
#             "status": "success",
#             "templates": templates
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get agent templates: {str(e)}"
#         }), 500

# # ----- Twitter Authentication Management -----

# @app.route('/twitter-auth/<client_id>', methods=['GET'])
# def get_twitter_auth(client_id):
#     """
#     Get Twitter authentication information for a client
#     """
#     try:
#         print(f"Retrieving Twitter auth for client_id: {client_id}")
        
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
        
#         if not auth_data or not isinstance(auth_data, dict):
#             print(f"No Twitter authentication found for client_id: {client_id}")
#             return jsonify({
#                 "status": "error",
#                 "message": f"No Twitter authentication found for client ID: {client_id}",
#                 "error_type": "not_found",
#                 "recommendation": "Please authenticate with Twitter first"
#             }), 404
        
#         # Print auth data for debugging (redacting sensitive info)
#         debug_auth = {
#             "client_id": auth_data.get("client_id", ""),
#             "user_id": auth_data.get("user_id", ""),
#             "user_name": auth_data.get("user_name", ""),
#             "api_key_exists": bool(auth_data.get("api_key")),
#             "api_secret_exists": bool(auth_data.get("api_secret_key")),
#             "access_token_exists": bool(auth_data.get("access_token")),
#             "access_token_secret_exists": bool(auth_data.get("access_token_secret"))
#         }
#         print("Debug Auth Data:", debug_auth)
        
#         # Check if required credentials exist
#         required_fields = ["api_key", "api_secret_key", "access_token", "access_token_secret", "user_name"]
#         missing_fields = [field for field in required_fields if not auth_data.get(field)]
        
#         if missing_fields:
#             return jsonify({
#                 "status": "error",
#                 "message": f"Twitter authentication data is incomplete. Missing: {', '.join(missing_fields)}",
#                 "error_type": "incomplete_data",
#                 "recommendation": "Please reconnect your Twitter account"
#             }), 400
        
#         try:
#             # Create client with the stored credentials
#             client = tweepy.Client(
#                 consumer_key=auth_data.get("api_key"), 
#                 consumer_secret=auth_data.get("api_secret_key"), 
#                 access_token=auth_data.get("access_token"), 
#                 access_token_secret=auth_data.get("access_token_secret")
#             )
            
#             # Try a basic API call (get user info)
#             user = client.get_me() 

#             test = client.create_tweet(text="Hello, world!")
#             print(f"Test: {test}")
#             print(f"Successfully retrieved user data for @{auth_data.get('user_name')}")
            
#             # Remove sensitive information before returning
#             safe_auth_data = {
#                 "client_id": auth_data.get("client_id"),
#                 "user_id": auth_data.get("user_id"),
#                 "user_name": auth_data.get("user_name"),
#                 "created_at": auth_data.get("created_at", datetime.now(timezone.utc)),
#                 "updated_at": auth_data.get("updated_at", datetime.now(timezone.utc)),
#                 "user": user.data._json if hasattr(user, 'data') and hasattr(user.data, '_json') else None
#             }
            
#             # Convert ObjectId to string for JSON serialization
#             safe_auth_data_json = json.loads(json.dumps(safe_auth_data, default=str))
            
#             return jsonify({
#                 "status": "success",
#                 "auth_data": safe_auth_data_json
#             })
        
#         except tweepy.TweepyException as tweet_error:
#             error_str = str(tweet_error)
#             print(f"Twitter API Error: {error_str}")
            
#             # Determine specific error type
#             error_type = "unknown"
#             recommendation = "Please try reconnecting your Twitter account"
            
#             if "401" in error_str:
#                 error_type = "unauthorized"
#                 recommendation = "Your Twitter credentials have expired or been revoked. Please reconnect your Twitter account."
#             elif "403" in error_str:
#                 error_type = "forbidden"
#                 recommendation = "Your Twitter app doesn't have permission to perform this action. Check your app permissions."
#             elif "404" in error_str:
#                 error_type = "not_found"
#                 recommendation = "Twitter user account not found. The account may have been deleted or suspended."
#             elif "429" in error_str:
#                 error_type = "rate_limit"
#                 recommendation = "Twitter rate limit exceeded. Please try again later."
            
#             # Return a more informative error
#             return jsonify({
#                 "status": "error",
#                 "message": f"Twitter API error: {error_str}",
#                 "auth_exists": True,
#                 "user_name": auth_data.get("user_name"),
#                 "error_type": error_type,
#                 "recommendation": recommendation,
#                 "reconnect_url": f"/connect-twitter-account?client_id={client_id}"
#             }), 401
    
#     except Exception as e:
#         print(f"Internal Error in get_twitter_auth: {str(e)}")
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get Twitter authentication: {str(e)}",
#             "error_type": "server_error",
#             "recommendation": "Please try again later or contact support"
#         }), 500

# @app.route('/twitter-auth/<client_id>', methods=['DELETE'])
# def delete_twitter_auth(client_id):
#     """
#     Delete Twitter authentication information for a client
#     """
#     try:
#         db = get_db()
#         result = db.delete_twitter_auth(client_id)
        
#         return jsonify({
#             "status": "success",
#             "message": result['message']
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to delete Twitter authentication: {str(e)}"
#         }), 500

# @app.route('/twitter-auth', methods=['POST'])
# def save_twitter_auth():
#     """
#     Save Twitter API keys for both app and user authentication
#     """
#     try:
#         data = request.get_json()
        
#         # Validate required fields
#         required_fields = [
#             'client_id',
#             'user_id',
#             'user_name',
#             'api_key',
#             'api_secret_key',
#             'bearer_token',
#             'access_token',
#             'access_token_secret'
#         ]
        
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({
#                     'status': 'error',
#                     'message': f'Missing required field: {field}'
#                 }), 400

#         # Create TwitterAuth object
#         auth_data = {
#             'client_id': data['client_id'],
#             'user_id': data['user_id'],
#             'user_name': data['user_name'],
#             'api_key': data['api_key'],
#             'api_secret_key': data['api_secret_key'],
#             'bearer_token': data['bearer_token'],
#             'access_token': data['access_token'],
#             'access_token_secret': data['access_token_secret'],
#             'created_at': datetime.now(timezone.utc),
#             'updated_at': datetime.now(timezone.utc)
#         }

#         # Save to database
#         db = get_db()
#         result = db.add_twitter_auth(auth_data)
#         db.close()

#         return jsonify({
#             'status': 'success',
#             'message': 'Twitter API keys saved successfully',
#             'data': {
#                 'client_id': data['client_id'],
#                 'user_name': data['user_name']
#             }
#         }), 200

#     except Exception as e:
#         return jsonify({
#             'status': 'error',
#             'message': f'Failed to save Twitter API keys: {str(e)}'
#         }), 500

# @app.route('/test-agent/<client_id>/<agent_name>', methods=['POST'])
# def test_agent_config(client_id, agent_name):
#     """
#     Test an agent configuration by generating a simple LLM response
#     """
#     try:
#         # Get the request data
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No data provided"
#             }), 400
        
#         # Get the test question from request data
#         test_question = data.get('question')
        
#         if not test_question:
#             return jsonify({
#                 "status": "error",
#                 "message": "Test question is required"
#             }), 400
        
  
#         # Load the agent configuration
#         agent_config = main.load_agent_config(client_id, agent_name)

#         if not agent_config:
#             return jsonify({
#                 "status": "error",
#                 "message": f"Agent configuration not found for {client_id}/{agent_name}"
#             }), 404
        
#         # Get model configuration
#         model_config = agent_config.get("MODEL_CONFIG", {})
#         model_type = model_config.get("model", "gpt-4")
      
#         llm = main.initialize_llm(model_config={"type": "deepseek"})
        
#         # Create a simple prompt that includes the agent's personality and configuration
#         personality = agent_config.get("USER_PERSONALITY", "")
#         style_rules = agent_config.get("STYLE_RULES", "")
#         content_restrictions = agent_config.get("CONTENT_RESTRICTIONS", "")
        
#         prompt = f"""You are a Twitter bot with the following personality and rules:

# Personality:
# {personality}

# Style Rules:
# {style_rules}

# Content Restrictions:
# {content_restrictions}

# Please respond to this question in character, as if you were this Twitter bot:
# {test_question}

# Remember to:
# 1. Stay in character
# 2. Follow the style rules
# 3. Respect content restrictions
# 4. Keep the response concise and Twitter-like
# """

#         print(prompt, "PROMPT")
#         # Generate response using selected LLM
#         response = llm.invoke(prompt)
#         print(response, "RESPONSE")
#         print(response.content, "RESPONSE CONTENT")
#         return jsonify({
#             "status": "success",
#             "message": "Test response generated successfully",
#             "result": response.content,
#             "question": test_question,
#             "agent_config": {
#                 "name": agent_name,
#                 "personality": personality,
#                 "style_rules": style_rules,
#                 "content_restrictions": content_restrictions,
#                 "model": model_type,
#                 "model_config": model_config
#             }
#         })
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to generate test response: {str(e)}"
#         }), 500

# @app.route('/connect-twitter-account', methods=['POST'])
# def connect_twitter_account():
#     """
#     Start the Twitter OAuth flow with a simplified user experience
#     """
#     try:
#         print(request.json, "REQUEST JSON")
#         # Get client ID from request data
#         client_id = request.json.get('client_id')
#         print(client_id, "CLIENT ID")
        
#         # Only generate a new client ID if one is not provided
#         if not client_id:
#             client_id = str(uuid.uuid4())
#             print(f"No client ID provided, generated new ID: {client_id}")
#         else:
#             print(f"Using provided client ID: {client_id}")
        
#         # Get the redirect URL from query param for frontend callback
#         redirect_url = request.args.get('redirect_url', FRONTEND_URL)
        
#         # Store the redirect URL and client ID in the session
#         session['redirect_url'] = redirect_url
#         session['client_id'] = client_id
        
#         # Log session data for debugging
#         print(f"Session data stored: client_id={client_id}, redirect_url={redirect_url}")
#         print(f"Session object: {session}")
        
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
#         print(auth_data, "AUTH DATA")
        
#         # Check if auth_data is valid
#         if not auth_data or not isinstance(auth_data, dict):
#             return jsonify({
#                 "status": "error",
#                 "message": "No Twitter authentication data found for this client ID. Please initialize with API keys first."
#             }), 400
        
#         # Safely get API keys
#         api_key = auth_data.get("api_key")
#         api_secret = auth_data.get("api_secret_key")
        
#         if not api_key or not api_secret:
#             return jsonify({
#                 "status": "error",
#                 "message": "Twitter API keys are missing from authentication data"
#             }), 400
        
#         # Log the API key being used (first few chars only for security)
#         print(f"Using API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
        
#         # Initialize OAuth1UserHandler with application credentials
#         oauth1_user_handler = tweepy.OAuth1UserHandler(
#             api_key,
#             api_secret,
#             callback=TWITTER_CALLBACK_URL  # Add client_id to callback URL
#         )
        
#         # Get the authorization URL
#         auth_url = oauth1_user_handler.get_authorization_url()
        
#         # Store the request token in the session
#         session['request_token'] = oauth1_user_handler.request_token
#         print(session['request_token']['oauth_token'], "REQUEST TOKEN")
#         # Return the auth URL for the frontend to redirect the user to Twitter
#         return jsonify({
#             "status": "success",
#             "message": "Twitter authentication flow started",
#             "auth_url": auth_url,
#             "client_id": client_id,
#             "redirect_url": redirect_url,
#             "instructions": {
#                 "step1": "Redirect user to the auth_url (window.location.href or window.open)",
#                 "step2": "Twitter will handle the authentication and redirect to our backend",
#                 "step3": "Our backend will process the callback and redirect to your redirect_url",
#                 "step4": "Check authentication status using /twitter-callback-status?client_id=YOUR_CLIENT_ID"
#             }
#         })
    
#     except Exception as e:
#         error_message = str(e)
#         print(f"Error in connect_twitter_account: {error_message}")
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to start Twitter authentication: {error_message}"
#         }), 500

# @app.route('/validate-twitter-credentials', methods=['POST'])
# def validate_twitter_credentials():
#     """
#     Validate Twitter API credentials without saving them
#     Useful for testing if credentials are valid before saving
#     """
#     try:
#         # Get request data
#         data = request.json
        
#         if not data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No data provided"
#             }), 400
        
#         # Validate required fields
#         required_fields = [
#             'api_key',
#             'api_secret_key',
#             'bearer_token',
#             'access_token',
#             'access_token_secret',
#         ]
        
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({
#                     'status': 'error',
#                     'message': f'Missing required field: {field}'
#                 }), 400
        
#         # Verify the credentials by making a test API call
#         try:
#             client = tweepy.Client(
#                 consumer_key=data['api_key'],
#                 consumer_secret=data['api_secret_key'],
#                 access_token=data['access_token'],
#                 access_token_secret=data['access_token_secret'],
#                 bearer_token=data['bearer_token']
#             )
            
#             # Get the user's information
#             user = client.get_me(user_auth=True)
            
#             if not user or not user.data:
#                 return jsonify({
#                     'status': 'error',
#                     'message': 'Could not verify Twitter credentials. Please check the provided keys and tokens.'
#                 }), 400
                
#             user_id = user.data.id
#             user_name = user.data.username
            
#             return jsonify({
#                 'status': 'success',
#                 'message': 'Twitter credentials verified successfully',
#                 'data': {
#                     'user_id': user_id,
#                     'user_name': user_name
#                 }
#             }), 200
            
#         except Exception as twitter_error:
#             return jsonify({
#                 'status': 'error',
#                 'message': f'Failed to verify Twitter credentials: {str(twitter_error)}'
#             }), 400
    
#     except Exception as e:
#         return jsonify({
#             'status': 'error',
#             'message': f'Failed to validate Twitter credentials: {str(e)}'
#         }), 500

# @app.route('/twitter-callback-status', methods=['GET'])
# def twitter_callback_status():
#     """
#     Check the status of a Twitter OAuth callback
#     This endpoint can be used by the frontend to check if the user has completed the OAuth flow
#     """
#     try:
#         client_id = request.args.get('client_id')
        
#         if not client_id:
#             return jsonify({
#                 "status": "error",
#                 "message": "No client ID provided"
#             }), 400
        
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
        
#         if not auth_data or not isinstance(auth_data, dict):
#             return jsonify({
#                 "status": "pending",
#                 "message": "Authentication not completed yet"
#             }), 200
        
#         # Check if required user data is available
#         if not auth_data.get("user_id") or not auth_data.get("user_name"):
#             return jsonify({
#                 "status": "pending",
#                 "message": "Authentication data incomplete"
#             }), 200
        
#         # Return minimal user data
#         user_data = {
#             "user_id": auth_data.get("user_id"),
#             "user_name": auth_data.get("user_name"),
#             "created_at": auth_data.get("created_at", datetime.now(timezone.utc))
#         }
        
#         # Convert dates to string for JSON serialization
#         user_data_json = json.loads(json.dumps(user_data, default=str))
        
#         return jsonify({
#             "status": "completed",
#             "message": "Authentication completed successfully",
#             "user_data": user_data_json
#         }), 200
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to check Twitter callback status: {str(e)}"
#         }), 500

# @app.route('/oauth-example', methods=['GET'])
# def oauth_example():
#     """
#     Serve the OAuth example HTML page
#     """
#     try:
#         with open('oauth_example.html', 'r') as f:
#             html_content = f.read()
        
#         return html_content, 200, {'Content-Type': 'text/html'}
    
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to load OAuth example: {str(e)}"
#         }), 500

# @app.route('/post-tweet/<client_id>', methods=['POST'])
# def post_tweet(client_id):
#     """
#     Post a tweet on behalf of a user using their stored credentials
#     """
#     try:
#         # Get request data
#         data = request.json
        
#         if not data or 'text' not in data:
#             return jsonify({
#                 "status": "error",
#                 "message": "Tweet text is required in the request body"
#             }), 400
        
#         tweet_text = data['text']
        
#         # Get the user's auth data from database
#         db = get_db()
#         auth_data = db.get_twitter_auth(client_id)
        
#         if not auth_data:
#             return jsonify({
#                 "status": "error",
#                 "message": "No authentication data found for this client ID"
#             }), 404
        
#         # Initialize Tweepy client with the stored credentials
#         client = tweepy.Client(
#             consumer_key=auth_data["api_key"],
#             consumer_secret=auth_data["api_secret_key"],
#             access_token=auth_data["access_token"],
#             access_token_secret=auth_data["access_token_secret"]
#         )
        
#         # Post the tweet
#         try:
#             response = client.create_tweet(text=tweet_text)
#             tweet_id = response.data["id"]
            
#             # Store the tweet in our database
#             tweet_data = {
#                 "tweet_id": str(tweet_id),
#                 "user_id": auth_data["user_id"],
#                 "text": tweet_text,
#                 "created_at": datetime.now(timezone.utc),
#                 "saved_at": datetime.now(timezone.utc),
#                 "type": "ai_generated" 
#             }
            
#             db.add_written_ai_tweet(auth_data["user_id"], tweet_data)
            
#             return jsonify({
#                 "status": "success",
#                 "message": "Tweet posted successfully",
#                 "tweet_id": tweet_id,
#                 "tweet_url": f"https://twitter.com/{auth_data['user_name']}/status/{tweet_id}"
#             })
            
#         except Exception as tweet_error:
#             error_message = str(tweet_error)
#             print(f"Error posting tweet: {error_message}")
#             return jsonify({
#                 "status": "error",
#                 "message": f"Failed to post tweet: {error_message}"
#             }), 500
    
#     except Exception as e:
#         error_message = str(e)
#         print(f"Error in post_tweet: {error_message}")
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to post tweet: {error_message}"
#         }), 500

# @app.route('/users', methods=['GET'])
# def get_all_users():
#     """
#     Get all Twitter users who have connected their accounts
#     """
#     try:
#         db = get_db()
        
#         # Find all users with minimal information for security
#         users = list(db.twitter_auth.find({}, {
#             "client_id": 1,
#             "user_id": 1,
#             "user_name": 1,
#             "created_at": 1,
#             "updated_at": 1,
#             "_id": 0  # Exclude MongoDB _id
#         }))
        
#         # Convert dates to string for JSON serialization
#         users_json = json.loads(json.dumps(users, default=str))
        
#         return jsonify({
#             "status": "success",
#             "count": len(users_json),
#             "users": users_json
#         })
    
#     except Exception as e:
#         error_message = str(e)
#         print(f"Error getting all users: {error_message}")
#         return jsonify({
#             "status": "error",
#             "message": f"Failed to get users: {error_message}"
#         }), 500

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=int(8000)) 