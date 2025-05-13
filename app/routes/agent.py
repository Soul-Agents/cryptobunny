import json
import random
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from functools import wraps

from app.utils.db import get_db
from app.models.agent import AgentConfig
import main  # Import main module for agent execution
import jwt
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
    'is_active': False
}

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
        
        if existing_config:
            # Update existing config
            config = {
                **existing_config,
                **data,
                'created_at': existing_config['created_at'],
                'updated_at': now
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
        is_paid = db
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
@require_auth
def run_client_agent(client_id):
    """
    Run a client's agent with a specific prompt or action
    """
    try:
        # Get the request data
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400
        
        # Validate required fields
        action = data.get('action', 'default')
        question = data.get('question')
        
        if not question and action == 'custom':
            return jsonify({
                "status": "error",
                "message": "Question is required for custom action"
            }), 400
        
        # Get the client's agent configuration
        db = get_db()
        configs = db.get_agent_config(client_id)
        
        if not configs or len(configs) == 0:
            return jsonify({
                "status": "error",
                "message": f"No agent configuration found for client ID: {client_id}"
            }), 404
        
        # Get the first (and presumably only) configuration
        agent_config = configs[0]
        agent_name = agent_config.get("agent_name", "default")
        
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
            if not main.llm:
                return jsonify({
                    "status": "error",
                    "message": "Language model not available. Please check your API key configuration."
                }), 500
            
            # Execute the agent
            result = main.run_crypto_agent(question, session_id)
            
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
        
        prompt = f"""You are a Twitter bot with the following personality and rules:

Personality:
{personality}

Style Rules:
{style_rules}

Content Restrictions:
{content_restrictions}

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
        
        return jsonify({
            "success": True,
            # "message": "Agent payment processed successfully",
            # "payment": {
            #     "amount": amount,
            #     "payment_id": payment_id,
            #     "payment_date": datetime.now(timezone.utc).isoformat(),
            #     "client_id": client_id
            # },
            # "configuration": updated_config_json
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
            "tx_hash": config.get("tx_hash", "")
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
        # Get the database connection
        db = get_db()
        
        # Get all active and paid agents
        active_agents = db.get_all_active_paid_agents()
        
        if not active_agents or len(active_agents) == 0:
            return jsonify({
                "status": "success",
                "message": "No active and paid agents found"
            })
        def run_agent_thread(agent_config):
            try:
                print(agent_config, "agent_config")

                client_id = agent_config.get("client_id")
                agent_name = agent_config.get("agent_name", "default")
                
                
                # Store original values to restore later
                original_user_id = main.USER_ID
                original_user_name = main.USER_NAME
                
                try:
                    # Set global variables with our configuration
                    main.set_global_agent_variables(agent_config)
                    
                    # Execute the agent
                    main.run_crypto_agent(agent_config)
                    
                    print(f"Agent executed successfully: {client_id}/{agent_name}")
                
                finally:
                    # Restore original variables
                    main.USER_ID = original_user_id
                    main.USER_NAME = original_user_name
            
            except Exception as e:
                print(f"Error executing agent {agent_config.get('client_id')}/{agent_config.get('agent_name')}: {str(e)}")
        
        # Start a thread for each agent
        threads = []
        for agent in active_agents:
            thread = threading.Thread(target=run_agent_thread, args=(agent,))
            thread.daemon = True  # Make threads daemon so they don't block application shutdown
            thread.start()
            threads.append(thread)
        
        return jsonify({
            "status": "success",
            "message": f"Started execution of {len(active_agents)} agents",
            "agent_count": len(active_agents)
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to run agents: {str(e)}"
        }), 500

    
    
