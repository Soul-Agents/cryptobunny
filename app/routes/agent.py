import json
import random
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from functools import wraps
from app.utils.encryption import decrypt_dict_values, SENSITIVE_FIELDS
from app.utils.db import get_db
from app.models.agent import AgentConfig
from app.utils.bearer import generate_bearer_token
import main  # Import main module for agent execution
import jwt
import requests
from app.utils.protect import require_auth
# Create Blueprint
agent_bp = Blueprint('agent', __name__, url_prefix='/agent')


# Default configuration for new agents
DEFAULT_AGENT_CONFIG = {
    'user_personality': '',
    'style_rules': '',
    'content_restrictions': '',
    'strategy': '',
    'remember': '',
    'mission': '',
    'questions': [],
    'engagement_strategy': '',
    'ai_and_agents': [],
    'web3_builders': [],
    'defi_experts': [],
    'knowledge_base': '',
    'model_config': {
        'type': 'gpt-4',
        'temperature': 0.7,
        'top_p': 0.9,
        'presence_penalty': 0.6,
        'frequency_penalty': 0.6,
    },
    'is_active': False,
    'approval_mode': 'automatic'  # 'automatic' | 'manual'
}

def get_api_limit(bearer_token): 

    if not bearer_token:
        return {
            "project_usage": 0,
            "project_cap": 0,
            "cap_reset_day": 0
        }
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }
    res = requests.get("https://api.twitter.com/2/usage/tweets", headers=headers)
    return res.json()

def create_or_update_agent_config(data: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, str]:
    """
    Create or update an agent configuration.
    
    Args:
        data: Dictionary containing agent configuration data
        
    Returns:
        Tuple containing:
        - Configuration dictionary
        - Success boolean
        - Message string
    """
    try:
        client_id = data.get('client_id')
        if not client_id:
            return {}, False, "Missing client_id"

        db = get_db()
        now = datetime.now(timezone.utc)
        
        # Check for existing config
        existing_config = db.get_agent_config(client_id)
        # auth_data = db.get_twitter_auth(client_id)
        # decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        # bearer_token = decrypted_auth.get("bearer_token")
        
        # if not bearer_token:
        #     bearer_token = generate_bearer_token(decrypted_auth.get("api_key"), decrypted_auth.get("api_secret_key"))
        # api_status = get_api_limit(bearer_token)

        # print(api_status, "API STATUS")

        if existing_config:
            # Update existing config
            config = {
                **existing_config,
                **data,
                'created_at': existing_config['created_at'],
                'updated_at': now,
              
            }
        else:
            # Create new config
            config = {
                **DEFAULT_AGENT_CONFIG,
                **data,
                'client_id': client_id,
                'created_at': now,
                'updated_at': now
            }

        # Save configuration
        result = db.add_agent_config(config)
        if not result:
            return config, False, "Failed to save configuration to database"

        return config, True, "Configuration saved successfully"

    except Exception as e:
        return {}, False, f"Internal error: {str(e)}"

@agent_bp.route('/config', methods=['POST'])
@require_auth
def create_agent_config():
    """Create or update an agent configuration"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        config, success, message = create_or_update_agent_config(data)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 400

        return jsonify({
            'success': True,
            'message': message,
            'configuration': json.loads(json.dumps(config, default=str))
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to process request: {str(e)}'
        }), 500

@agent_bp.route('/config/<client_id>', methods=['GET'])
@require_auth
def get_client_agent_config(client_id):
    """
    Get a client's agent configuration (one user = one agent)
    """
    try:
        db = get_db()
        config = db.get_agent_config(client_id)


        # auth_data = db.get_twitter_auth(client_id)
    
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Get the first (and presumably only) configuration
        
        # Convert ObjectId to string for JSON serialization
        config_json = json.loads(json.dumps(config, default=str))
        
        return jsonify({
            "status": "success",
            "configuration": config_json
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get agent configuration: {str(e)}"
        }), 500

@agent_bp.route('/config/<client_id>', methods=['PUT'])
@require_auth
def update_agent_config(client_id):
    """
    Update a client's agent configuration
    """
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Get the existing configuration
        db = get_db()
        config  = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
       
        
        # Update the configuration with the new data
        for key in data:
            if key in config and key not in ['client_id', 'created_at']:
                config[key] = data[key]
        
        # Update the updated_at timestamp
        config['updated_at'] = datetime.now(timezone.utc)
        
        # Save the updated configuration
        result = db.add_agent_config(config)
        
        return jsonify({
            "success": True,
            "message": "Agent configuration updated successfully",
            "result": result
        })
    
    except Exception as e:
        print(e)
        return jsonify({
            "success": False,
            "message": f"Failed to update agent configuration: {str(e)}"
        }), 500

@agent_bp.route('/config/<client_id>', methods=['DELETE'])
@require_auth
def delete_agent_config(client_id):
    """
    Delete a client's agent configuration
    """
    try:
        db = get_db()
        config = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
       
        
        result = db.delete_agent_config(client_id)
        
        return jsonify({
            "success": True,
            "message": result['message']
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to delete agent configuration: {str(e)}"
        }), 500


@agent_bp.route('/run/<client_id>', methods=['POST'])
# @require_auth
async def run_client_agent(client_id):
    """
    Run a client's agent with a specific prompt or action
    """
    try:
        # Get the request data
        data = request.json
        print(data)
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Validate required fields
        action = data.get('action', 'default')
        question = data.get('question')
        
        # Validate request data
        if not data:
            return jsonify({
                "status": "error", 
                "message": "No data provided"
            }), 400

 
        if not question and action == 'custom':
            return jsonify({
                "status": "error",
                "message": "Question is required for custom action"
            }), 400
        
        # Get the client's agent configuration
        db = get_db()
        config = db.get_agent_config(client_id)
     
    
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        #
        agent_config = config
        agent_name = agent_config.get("agent_name", "default")
        # print(agent_config)
        # Use the session ID for memory persistence
        session_id = f"{client_id}_{agent_name}"
        
        # Select a random question from the agent's question bank if using default action
        if action == 'default' or not question:
            questions = agent_config.get("questions", [])
            if questions and isinstance(questions, list) and len(questions) > 0:
                question = random.choice(questions)
            else:
                question = "What interesting topics should I engage with today?"
        
        # Store original values to restore later
        original_user_id = main.USER_ID
        original_user_name = main.USER_NAME
        
        try:
            # Set global variables with our configuration
            main.set_global_agent_variables(agent_config)
            
            # Check if LLM is available
            # if not main.llm:
            #     return jsonify({
            #         "status": "error",
            #         "message": "Language model not available. Please check your API key configuration."
            #     }), 500
            
            # Execute the agent
            result = main.run_crypto_agent(agent_config)
            # result = db.get_unreplied_tweets(agent_config.get("user_id"))
            print(result)
            return jsonify({
                "status": "success",
                "message": "Agent executed successfully",
                "result": result,
                "question": question
            })
        
        finally:
            # Restore original variables
            main.USER_ID = original_user_id
            main.USER_NAME = original_user_name
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to run agent: {str(e)}"
        }), 500

@agent_bp.route('/history/<client_id>', methods=['GET'])
@require_auth
def get_client_agent_history(client_id):
    """
    Get activity history for a client's agent
    """
    try:
        db = get_db()
        
        # Get the client's agent configuration
        configs = db.get_agent_config(client_id)
        
        if not configs or len(configs) == 0:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Get the first (and presumably only) configuration
        agent_config = configs[0]
        
        # Get the most recent tweets posted by this agent
        user_id = agent_config["user_id"]
        tweets = db.get_last_written_ai_tweets(user_id, limit=10)
        
        # Get the most recent replies posted by this agent
        replies = db.get_last_written_ai_tweet_replies(user_id, limit=10)
        
        # Format the data for JSON response
        tweets_json = json.loads(json.dumps(tweets, default=str))
        replies_json = json.loads(json.dumps(replies, default=str))
        
        return jsonify({
            "status": "success",
            "tweets": tweets_json,
            "replies": replies_json
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get agent history: {str(e)}"
        }), 500

@agent_bp.route('/test/<client_id>', methods=['POST'])
def test_client_agent_config(client_id):
    """
    Test an agent configuration by generating a simple LLM response.
    """
    try:

      
        # Get the request data
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Get the test question and configuration from request data
        test_question = data.get('question')
        agent_config = data.get('config')
        


        if not test_question:
            return jsonify({
                "status": "error",
                "message": "Test question is required"
            }), 400
            
        if not agent_config:
            return jsonify({
                "status": "error",
                "message": "Agent configuration is required"
            }), 400
        
      
      
        llm = main.initialize_llm()
        
        # Create a simple prompt that includes the agent's personality and configuration
        personality = agent_config.get("personality", "")
        style_rules = agent_config.get("styleRules", "")
        content_restrictions = agent_config.get("contentRestrictions", "")
        username = agent_config.get("username", "")
        tweets = agent_config.get("exampleTweets", [])
        prompt = f"""You are {username} with the following personality and rules:

Personality:
{personality}

Style Rules:
{style_rules}

Content Restrictions:
{content_restrictions}

Tweets you can get inspired by (don't repeat them):
{tweets}

Please respond to this question in character:
{test_question}

Remember to:
1. Stay in character
2. Follow the style rules
3. Respect content restrictions
4. Keep the response concise and Twitter-like
"""

        # Generate response using selected LLM
        response = llm.invoke(prompt)
        
        return jsonify({
            "success": True,
            "message": "Test response generated successfully",
            "result": response.content,
            "question": test_question,
           
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to generate test response: {str(e)}"
        }), 500



@agent_bp.route('/reset-twitter-keys/<client_id>', methods=['PUT'])
def reset_twitter_keys(client_id):
    """
    Set 'has_twitter_keys' value to false for a client's agent configuration
    This indicates that the client no longer has valid Twitter API keys
    """
    try:
        # Get database connection
        db = get_db()
        
        # Check if agent config exists for this client
        configs = db.get_agent_config(client_id)
        
        if not configs:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Update agent configurations to set has_twitter_keys to false
        agent_result = db.agent_config.update_many(
            {"client_id": client_id},
            {"$set": {
                "has_twitter_keys": False,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return jsonify({
            "status": "success",
            "message": f"Twitter keys status reset for client ID: {client_id}",
            "agent_configs_updated": agent_result.modified_count
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to reset Twitter keys status: {str(e)}"
        }), 500

@agent_bp.route('/cleanup-twitter-auth/<client_id>', methods=['DELETE'])
def cleanup_twitter_auth(client_id):
    """
    Properly clean up Twitter authentication data to prevent duplicate key errors
    This removes both the client's auth records and any null user_id records that could cause conflicts
    """
    try:
        # Get database connection
        db = get_db()
        
        # Delete the specific client's Twitter auth data
        client_result = db.twitter_auth.delete_many({"client_id": client_id})
        
        # Also delete any records with null user_id to prevent duplicate key errors
        null_result = db.twitter_auth.delete_many({"user_id": None})
        
        # Update agent configurations to mark that Twitter is not authorized
        agent_result = db.agent_config.update_many(
            {"client_id": client_id},
            {"$set": {
                "has_twitter_keys": False,
                "is_twitter_authorized": False,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return jsonify({
            "status": "success",
            "message": f"Twitter authentication data cleaned up for client ID: {client_id}",
            "client_records_deleted": client_result.deleted_count,
            "null_records_deleted": null_result.deleted_count,
            "agent_configs_updated": agent_result.modified_count
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to clean up Twitter authentication data: {str(e)}"
        }), 500


@agent_bp.route('/payment/<client_id>', methods=['POST'])
@require_auth
def process_agent_payment(client_id):
    """
    Process payment for a client's agent and mark it as paid
    This endpoint accepts payment information from the frontend and updates the agent's payment status
    """
    try:
        # Get request data
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No payment data provided"
            }), 400
        
        # Validate required fields
        amount = data.get('amount')
        tx_hash = data.get("txHash")
        if amount is None or tx_hash is None:
            return jsonify({
                "status": "error",
                "message": "Payment amount and txHash are required"
            }), 400
        
        # Try to convert amount to float
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid payment amount format"
            }), 400
        
        # Optional payment ID/reference
        payment_id = data.get('payment_id', f"pay_{int(datetime.now(timezone.utc).timestamp())}")
        
        # Get the database connection
        db = get_db()
        
        # Check if there's an agent config for this client
        config = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Update the agent configuration with payment information
        update_result = db.agent_config.update_one(
            {"client_id": client_id},
            {"$set": {
                "is_paid": True,
                "payment_amount": amount,
                "payment_date": datetime.now(timezone.utc),
                "payment_id": payment_id,
                "updated_at": datetime.now(timezone.utc),
                "tx_hash": tx_hash,
                "is_all_setup": True,
                # Also activate the agent since it's now paid
                "is_active": True
            }}
        )
        
        if update_result.modified_count == 0:
            return jsonify({
                "status": "error",
                "message": "Failed to update agent payment status"
            }), 500
        
        # Get the updated configuration
        updated_config = db.get_agent_config(client_id)
        
        # Convert datetime to string for JSON serialization
        updated_config_json = json.loads(json.dumps(updated_config, default=str))
        
        # Start agent execution in a background thread
        def run_agent_background():
            try:
                # Store original values
                original_user_id = main.USER_ID
                original_user_name = main.USER_NAME
                
                try:
                    main.set_global_agent_variables(updated_config)
                    main.run_crypto_agent(updated_config)
                finally:
                    # Restore original values
                    main.USER_ID = original_user_id
                    main.USER_NAME = original_user_name
            except Exception as e:
                print(f"Error running agent after payment: {str(e)}")
        
        # Start the background thread
        import threading
        agent_thread = threading.Thread(target=run_agent_background)
        agent_thread.daemon = True
        agent_thread.start()

        return jsonify({
            "success": True,
            "message": "Payment processed successfully and agent started",
            "payment": {
                "amount": amount,
                "payment_id": payment_id,
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "client_id": client_id
            }
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to process agent payment: {str(e)}"
        }), 500

@agent_bp.route('/payment/<client_id>', methods=['GET'])
@require_auth
def get_agent_payment_status(client_id):
    """
    Get the payment status for a client's agent
    """
    try:
        # Get the database connection
        db = get_db()
        
        # Check if there's an agent config for this client
        config = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Extract payment information
        payment_info = {
            "is_paid": config.get("is_paid", False),
            "payment_amount": config.get("payment_amount", 0.0),
            "payment_date": config.get("payment_date"),
            "payment_id": config.get("payment_id", ""),
            "is_active": config.get("is_active", False),
            "tx_hash": config.get("tx_hash", ""),
            "is_all_setup": config.get("is_all_setup", False)
        }
   
        
        # Convert datetime to string for JSON serialization
        payment_info_json = json.loads(json.dumps(payment_info, default=str))
        
        return jsonify({
            "success": True,
            "data": payment_info_json,
            "client_id": client_id
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get agent payment status: {str(e)}"
        }), 500

@agent_bp.route('/payment/status/<client_id>', methods=['GET'])
@require_auth
def check_agent_payment_status(client_id):
    """
    Quick check if a client has a paid and active agent
    Returns a simple boolean response for frontend usage
    """
    try:
        # Get the database connection
        db = get_db()
        
        # Check if there's an agent config for this client
        config = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "has_paid_agent": False,
                "client_id": client_id
            })
        
        # Check if the agent is paid and active
        has_paid_agent = config.get("is_paid", False) and config.get("is_active", False)
        
        return jsonify({
            "has_paid_agent": has_paid_agent,
            "client_id": client_id
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to check agent payment status: {str(e)}"
        }), 500

@agent_bp.route('/run-agents', methods=['GET'])
def run_agents():
    """
    Run all agents for all clients
    This endpoint will start a thread to run each active and paid agent
    Requires a valid API key for security
    """
    try:
        # Security check - validate API key
        api_key = request.headers.get('X-API-KEY')
        required_api_key = os.getenv("AGENT_RUNNER_API_KEY")
        
        if not required_api_key:
            return jsonify({
                "status": "error",
                "message": "Server configuration error: AGENT_RUNNER_API_KEY not set"
            }), 500
            
        if not api_key or api_key != required_api_key:
            return jsonify({
                "status": "error",
                "message": "Unauthorized: Invalid or missing API key"
            }), 401
        
        import threading
        from concurrent.futures import ThreadPoolExecutor
        import queue
        from datetime import datetime, timezone
        import time

        # Get the database connection
        db = get_db()
        
        # Get all active and paid agents
        active_agents = db.get_all_active_paid_agents()
        
        if not active_agents or len(active_agents) == 0:
            return jsonify({
                "status": "success",
                "message": "No active and paid agents found"
            })

        # Create a queue for logging messages
        log_queue = queue.Queue()
        
        # Create a dictionary to track rate limits per agent
        rate_limits = {}
        rate_limits_lock = threading.Lock()

        def check_rate_limit(agent_id):
            """Check if agent is rate limited"""
            with rate_limits_lock:
                if agent_id in rate_limits:
                    reset_time = rate_limits[agent_id]
                    if reset_time > datetime.now(timezone.utc).timestamp():
                        return True
            return False

        def mark_rate_limited(agent_id, reset_timestamp):
            """Mark agent as rate limited"""
            with rate_limits_lock:
                rate_limits[agent_id] = reset_timestamp

        def run_agent_thread(agent_config):
            try:
                client_id = agent_config.get("client_id")
                agent_name = agent_config.get("agent_name", "default")
                
                # Check if agent is rate limited
                if check_rate_limit(client_id):
                    log_queue.put(f"Agent {client_id}/{agent_name} is rate limited, skipping execution")
                    return

                # Store original values to restore later
                original_user_id = main.USER_ID
                original_user_name = main.USER_NAME
                
                try:
                    # Set global variables with our configuration
                    main.set_global_agent_variables(agent_config)
                    
                    try:
                        # Execute the agent
                        main.run_crypto_agent(agent_config)
                        log_queue.put(f"Agent executed successfully: {client_id}/{agent_name}")
                    except Exception as e:
                        # Check if it's a rate limit error
                        error_str = str(e).lower()
                        if 'rate limit' in error_str:
                            # Extract reset timestamp from error if available
                            # This is an example - adjust based on your actual error format
                            try:
                                reset_time = int(time.time()) + 900  # Default to 15 minutes if can't parse
                                mark_rate_limited(client_id, reset_time)
                                log_queue.put(f"Agent {client_id}/{agent_name} hit rate limit, will resume after reset")
                            except:
                                log_queue.put(f"Agent {client_id}/{agent_name} hit rate limit with unknown reset time")
                        else:
                            raise  # Re-raise if it's not a rate limit error
                
                finally:
                    # Restore original variables
                    main.USER_ID = original_user_id
                    main.USER_NAME = original_user_name
            
            except Exception as e:
                log_queue.put(f"Error executing agent {agent_config.get('client_id')}/{agent_config.get('agent_name')}: {str(e)}")

        # Use ThreadPoolExecutor to manage concurrent agent execution
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all agents to the executor
            future_to_agent = {executor.submit(run_agent_thread, agent): agent for agent in active_agents}
            
        # Process any logs that were generated
        logs = []
        while not log_queue.empty():
            logs.append(log_queue.get())
        
        return jsonify({
            "status": "success",
            "message": f"Completed execution of {len(active_agents)} agents",
            "agent_count": len(active_agents),
            "execution_logs": logs
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to run agents: {str(e)}"
        }), 500

def get_twitter_rate_limits(client_id: str) -> Dict:
    """
    Get Twitter rate limits for a client, using cache if available and not expired
    """
    try:
        db = get_db()

        now = datetime.now(timezone.utc)
        
        # Check cache first
        cached_limits = db.rate_limits.find_one({"client_id": client_id})
        
        # Return cached data if it's still valid
        if cached_limits:
            cached_until = cached_limits.get('cached_until')
            print(cached_until)
            # Ensure cached_until is timezone-aware
            if isinstance(cached_until, datetime) and cached_until.tzinfo is None:
                cached_until = cached_until.replace(tzinfo=timezone.utc)
            
            # Check if we're in a rate limit error state
            if cached_limits.get('has_rate_limit_error'):
                rate_limit_reset = cached_limits.get('rate_limit_reset')
                if isinstance(rate_limit_reset, datetime) and rate_limit_reset.tzinfo is None:
                    rate_limit_reset = rate_limit_reset.replace(tzinfo=timezone.utc)
                
                # If we're still in the rate limit period, return the cached error state
                if rate_limit_reset and rate_limit_reset > now:
                    return {
                        "error": "Rate limit in effect",
                        "limits": cached_limits['rate_limits'],
                        "cached": True,
                        "rate_limited": True,
                        "rate_limit_reset": rate_limit_reset,
                        "last_checked": cached_limits['last_checked']
                    }
                else:
                    # Rate limit period has expired, clear the error state
                    db.rate_limits.update_one(
                        {"client_id": client_id},
                        {"$set": {"has_rate_limit_error": False, "rate_limit_reset": None}}
                    )
            
            # Return valid cached data
            if cached_until > now:
                return {
                    "limits": cached_limits['rate_limits'],
                    "cached": True,
                    "last_checked": cached_limits['last_checked'],
                    "next_check": cached_until,
                    "rate_limited": False
                }
        else:
            # Initialize default rate limits for new clients
            print("Initializing default rate limits")
            default_limits = {
                "client_id": client_id,
                "rate_limits": {
                    "project_usage": 0,
                    "project_cap": 100,
                    "cap_reset_day": 0,
                    "project_id": 0
                },
                "last_checked": now,
                "cached_until": now,  # Will force immediate check
                "has_rate_limit_error": False,
                "rate_limit_reset": None
            }
            
            # Insert default limits
            db.rate_limits.insert_one(default_limits)
        
        # Get fresh data from Twitter
        auth_data = db.get_twitter_auth(client_id)
        if not auth_data:
            raise Exception("No Twitter authentication found")
        print("Twitter authentication found", auth_data)
        decrypted_auth = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
        bearer_token = decrypted_auth.get("bearer_token")
        
        if not bearer_token:
            bearer_token = generate_bearer_token(
                decrypted_auth.get("api_key"), 
                decrypted_auth.get("api_secret_key")
            )
        
        # Call Twitter API
        headers = {
            "Authorization": f"Bearer {bearer_token}"
        }
        
        response = requests.get("https://api.twitter.com/2/usage/tweets", headers=headers)
        
        if response.status_code != 200:
            # If we hit a rate limit, set the rate limit error state
            if response.status_code == 429:
                reset_time = None
                try:
                    reset_time = datetime.fromtimestamp(int(response.headers.get('x-rate-limit-reset', 0)), timezone.utc)
                except:
                    reset_time = now + timedelta(minutes=15)  # Default 15-minute wait if no reset time
                
                mark_rate_limit_error(client_id, reset_time)
                return {
                    "error": "Rate limit exceeded",
                    "limits": cached_limits['rate_limits'] if cached_limits else default_limits['rate_limits'],
                    "cached": True,
                    "rate_limited": True,
                    "rate_limit_reset": reset_time,
                    "last_checked": now
                }
            raise Exception(f"Twitter API error: {response.text}")
        
        # Extract rate limits from response
        api_data = response.json()
        data = api_data.get("data", {})
        rate_limits = {
            "project_usage": int(data.get("project_usage", 0)),
            "project_cap": int(data.get("project_cap", 100)),
            "cap_reset_day": int(data.get("cap_reset_day", 0)),
            "project_id": data.get("project_id", "0")
        }
        
        # Update cache with timezone-aware datetime
        cache_duration = timedelta(hours=2)
        cached_until = now + cache_duration
        
        db.rate_limits.update_one(
            {"client_id": client_id},
            {
                "$set": {
                    "rate_limits": rate_limits,
                    "last_checked": now,
                    "cached_until": cached_until,
                    "has_rate_limit_error": False,
                    "rate_limit_reset": None
                }
            },
            upsert=True
        )
        
        return {
            "limits": rate_limits,
            "cached": False,
            "last_checked": now,
            "next_check": cached_until,
            "rate_limited": False
        }
        
    except Exception as e:
        # For any other errors, return error state but don't mark as rate limited
        return {
            "error": str(e),
            "limits": cached_limits['rate_limits'] if cached_limits else {
                "project_usage": 0,
                "project_cap": 100,
                "cap_reset_day": 0,
                "project_id": 0
            },
            "cached": True,
            "rate_limited": False,
            "last_checked": now
        }

def mark_rate_limit_error(client_id: str, reset_time: datetime) -> None:
    """
    Mark a client as rate limited in the cache
    """
    try:
        db = get_db()
        db.rate_limits.update_one(
            {"client_id": client_id},
            {
                "$set": {
                    "has_rate_limit_error": True,
                    "rate_limit_reset": reset_time
                }
            }
        )
    except Exception as e:
        print(f"Error marking rate limit: {str(e)}")

@agent_bp.route('/twitter/limits/<client_id>', methods=['GET'])
@require_auth
def get_client_rate_limits(client_id):
    """
    Get Twitter rate limits for a client
    Uses cached data if available and not expired (2 hours)
    """
    try:
        result = get_twitter_rate_limits(client_id)
        
        response_data = {
            "status": "success" if not result.get('error') else "error",
            "data": {
                "limits": result['limits'],
                "cached": result['cached'],
                "last_checked": result['last_checked'],
                "rate_limited": result.get('rate_limited', False)
            }
        }
        
        # Add rate limit information if present
        if result.get('rate_limited'):
            response_data['data']['rate_limit_reset'] = result['rate_limit_reset']
            response_data['message'] = result['error']
        
        # Add next check time if available
        if result.get('next_check'):
            response_data['data']['next_check'] = result['next_check']
        
        status_code = 429 if result.get('rate_limited') else 200
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get rate limits: {str(e)}"
        }), 500

@agent_bp.route('/toggle/<client_id>', methods=['PUT'])
@require_auth
def toggle_agent_activation(client_id):
    """Toggle agent activation status (is_active property)"""
    try:
        db = get_db()
        config = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Check if agent is paid
        if not config.get('is_paid', False):
            return jsonify({
                "status": "error",
                "message": "Cannot activate unpaid agent. Please complete payment first."
            }), 403
        
        # Toggle is_active status
        new_status = not config.get('is_active', False)
        
        # Update the configuration
        result = db.agent_config.update_one(
            {"client_id": client_id},
            {
                "$set": {
                    "is_active": new_status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            return jsonify({
                "status": "error",
                "message": "Failed to update agent activation status"
            }), 500
        
        return jsonify({
           "success": True,
            "message": f"Agent {'activated' if new_status else 'deactivated'} successfully",
            "data": {
                "is_active": new_status
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to toggle agent activation: {str(e)}"
        }), 500

# Also add a GET endpoint to check activation status
@agent_bp.route('/status/<client_id>', methods=['GET'])
@require_auth
def get_agent_status(client_id):
    """
    Get agent activation and payment status
    """
    try:
        db = get_db()
        
        # Get current agent configuration
        config = db.get_agent_config(client_id)
        
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        return jsonify({
            "status": "success",
            "data": {
                "client_id": client_id,
                "is_active": config.get('is_active', False),
                "is_paid": config.get('is_paid', False),
                "last_updated": config.get('updated_at', '').isoformat() if config.get('updated_at') else None
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get agent status: {str(e)}"
        }), 500

# @agent_bp.route('/send-tg-message', methods=['POST'])
# @require_auth
# def send_tg_message():
#     """
#     Send a message to a Telegram channel
#     """
#     try:
#         db = get_db()
#         data = request.json
#         message = data.get('message')
#         channel_id = data.get('channel_id')
#         if not message or not channel_id:
#             return jsonify({
#                 "status": "error",
#                 "message": "Message and channel ID are required"
#             }), 400
        
#         # Send message to Telegram channel
#         # bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))

#         bot_builder = (
#     Application.builder()
#     .token(TELEGRAM_BOT_TOKEN)
#     .updater(None)
#     .build()
# )
        
#         bot.send_message(chat_id=channel_id, text=message)

#         return jsonify({
#             "status": "success",
#             "message": "Message sent successfully"
#         })
        
#     except Exception as e:


@agent_bp.route('/pending-replies/<client_id>', methods=['GET'])
@require_auth
def get_pending_replies(client_id):
    """
    Get pending replies for a client that need approval
    """
    try:
        # Get query parameters
        status = request.args.get('status', 'pending')
        
        db = get_db()
        
        # Check if agent config exists for this client
        config = db.get_agent_config(client_id)
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Get pending replies
        pending_replies = db.get_pending_replies(client_id, status)
        
        # Convert to JSON-serializable format
        replies_json = json.loads(json.dumps(pending_replies, default=str))
        
        return jsonify({
            "status": "success",
            "data": replies_json,
            "count": len(pending_replies)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get pending replies: {str(e)}"
        }), 500

@agent_bp.route('/approve-reply/<reply_id>', methods=['PUT'])
@require_auth
def approve_reply(reply_id):
    """
    Approve a pending reply
    """
    try:
        db = get_db()
        
        # Get the reply data
        reply_data = db.get_reply_by_id(reply_id)
        if not reply_data:
            return jsonify({
                "status": "error",
                "message": "Reply not found"
            }), 404
        
        # Check if it's still pending
        if reply_data.get("status") != "pending":
            return jsonify({
                "status": "error",
                "message": f"Reply is not pending (current status: {reply_data.get('status')})"
            }), 400
        
        # Update status to approved
        result = db.update_reply_status(reply_id, "approved")
        
        if result["status"] == "success":
            return jsonify({
                "status": "success",
                "message": "Reply approved successfully",
                "reply_id": reply_id
            })
        else:
            return jsonify({
                "status": "error",
                "message": result["message"]
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to approve reply: {str(e)}"
        }), 500

@agent_bp.route('/reject-reply/<reply_id>', methods=['PUT'])
@require_auth
def reject_reply(reply_id):
    """
    Reject a pending reply
    """
    try:
        db = get_db()
        
        # Get the reply data
        reply_data = db.get_reply_by_id(reply_id)
        if not reply_data:
            return jsonify({
                "status": "error",
                "message": "Reply not found"
            }), 404
        
        # Check if it's still pending
        if reply_data.get("status") != "pending":
            return jsonify({
                "status": "error",
                "message": f"Reply is not pending (current status: {reply_data.get('status')})"
            }), 400
        
        # Update status to rejected
        result = db.update_reply_status(reply_id, "rejected")
        
        if result["status"] == "success":
            return jsonify({
                "status": "success",
                "message": "Reply rejected successfully",
                "reply_id": reply_id
            })
        else:
            return jsonify({
                "status": "error",
                "message": result["message"]
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to reject reply: {str(e)}"
        }), 500

@agent_bp.route('/post-approved-reply/<reply_id>', methods=['POST'])
@require_auth
def post_approved_reply(reply_id):
    """
    Post an approved reply to Twitter
    """
    try:
        db = get_db()
        
        # Get the reply data
        reply_data = db.get_reply_by_id(reply_id)
        if not reply_data:
            return jsonify({
                "status": "error",
                "message": "Reply not found"
            }), 404
        
        # Check if it's approved
        if reply_data.get("status") != "approved":
            return jsonify({
                "status": "error",
                "message": f"Reply is not approved (current status: {reply_data.get('status')})"
            }), 400
        
        # Get client configuration and initialize Twitter client
        client_id = reply_data.get("client_id")
        config = db.get_agent_config(client_id)
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Initialize Twitter client
        if not main.TwitterClient.initialize(client_id):
            return jsonify({
                "status": "error",
                "message": "Failed to initialize Twitter client"
            }), 500
        
        # Set global variables for this agent
        main.set_global_agent_variables(config)
        
        # Post the reply
        tweet_id = reply_data.get("original_tweet_id")
        tweet_text = reply_data.get("original_tweet_text", "")
        message = reply_data.get("proposed_reply")
        
        # Use the existing answer tool to post the reply
        result = main.answer_tool._run(tweet_id, tweet_text, message)
        
        if "error" not in result:
            # Mark as posted in database
            posted_tweet_id = result.get("data", {}).get("tweet_id")
            if posted_tweet_id:
                db.mark_reply_as_posted(reply_id, posted_tweet_id)
            
            return jsonify({
                "status": "success",
                "message": "Reply posted successfully",
                "reply_id": reply_id,
                "posted_tweet_id": posted_tweet_id
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to post reply: {result.get('error', 'Unknown error')}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to post approved reply: {str(e)}"
        }), 500

@agent_bp.route('/process-approved-replies/<client_id>', methods=['POST'])
@require_auth
def process_approved_replies(client_id):
    """
    Process all approved replies for a client (post them to Twitter)
    """
    try:
        db = get_db()
        
        # Get all approved replies for this client
        approved_replies = db.get_pending_replies(client_id, "approved")
        
        if not approved_replies:
            return jsonify({
                "status": "success",
                "message": "No approved replies to process",
                "processed_count": 0
            })
        
        # Get client configuration and initialize Twitter client
        config = db.get_agent_config(client_id)
        if not config:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Initialize Twitter client
        if not main.TwitterClient.initialize(client_id):
            return jsonify({
                "status": "error",
                "message": "Failed to initialize Twitter client"
            }), 500
        
        # Set global variables for this agent
        main.set_global_agent_variables(config)
        
        processed_count = 0
        errors = []
        
        for reply_data in approved_replies:
            try:
                reply_id = str(reply_data["_id"])
                tweet_id = reply_data.get("original_tweet_id")
                tweet_text = reply_data.get("original_tweet_text", "")
                message = reply_data.get("proposed_reply")
                
                # Post the reply
                result = main.answer_tool._run(tweet_id, tweet_text, message)
                
                if "error" not in result:
                    # Mark as posted in database
                    posted_tweet_id = result.get("data", {}).get("tweet_id")
                    if posted_tweet_id:
                        db.mark_reply_as_posted(reply_id, posted_tweet_id)
                        processed_count += 1
                else:
                    errors.append(f"Reply {reply_id}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                errors.append(f"Reply {reply_id}: {str(e)}")
        
        response_data = {
            "status": "success",
            "message": f"Processed {processed_count} approved replies",
            "processed_count": processed_count,
            "total_approved": len(approved_replies)
        }
        
        if errors:
            response_data["errors"] = errors
            response_data["error_count"] = len(errors)
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to process approved replies: {str(e)}"
        }), 500


