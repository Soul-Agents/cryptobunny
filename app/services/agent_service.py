import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import uuid
import time
import asyncio
import random
import traceback

from app.utils.db import get_db
from app.agents.agent_runner import run_agent
from app.utils.config import Config
from app.services.twitter_service import twitter_service

logger = logging.getLogger(__name__)

class AgentService:
    """Service for handling AI agent operations"""
    
    def __init__(self):
        self.agents = {}
        self.agent_tasks = {}
        self.running = False
        self.config = Config()
        self.agent_types = ["tweeter", "scheduler", "analyzer"]
    
    @staticmethod
    def get_agent_configs(client_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get all agent configurations for a client
        
        Args:
            client_id: Client ID to get configurations for
            
        Returns:
            Tuple of (success, configs_data)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Get agent configurations
            configs = db.get_agent_configs(client_id)
            
            if not configs:
                return True, {
                    "status": "success",
                    "configs": []
                }
            
            return True, {
                "status": "success",
                "configs": configs
            }
        
        except Exception as e:
            logger.error(f"Error getting agent configs: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get agent configurations: {str(e)}"
            }
    
    @staticmethod
    def get_agent_config(client_id: str, config_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get a specific agent configuration
        
        Args:
            client_id: Client ID to get configuration for
            config_id: Configuration ID to get
            
        Returns:
            Tuple of (success, config_data)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Get the specific agent configuration
            config = db.get_agent_config(client_id, config_id)
            
            if not config:
                return False, {
                    "status": "error",
                    "message": "Agent configuration not found"
                }
            
            return True, {
                "status": "success",
                "config": config
            }
        
        except Exception as e:
            logger.error(f"Error getting agent config: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get agent configuration: {str(e)}"
            }
    
    @staticmethod
    def create_agent_config(client_id: str, config_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new agent configuration
        
        Args:
            client_id: Client ID to create configuration for
            config_data: Configuration data for the agent
            
        Returns:
            Tuple of (success, created_config)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Add timestamps to config data
            now = datetime.now()
            config_data["created_at"] = now
            config_data["updated_at"] = now
            config_data["client_id"] = client_id
            
            # Required fields validation
            required_fields = ["name", "prompt", "type"]
            for field in required_fields:
                if field not in config_data:
                    return False, {
                        "status": "error",
                        "message": f"Missing required field: {field}"
                    }
            
            # Create the agent configuration
            config_id = db.create_agent_config(client_id, config_data)
            
            # Get the newly created configuration
            config = db.get_agent_config(client_id, config_id)
            
            return True, {
                "status": "success",
                "message": "Agent configuration created successfully",
                "config": config
            }
        
        except Exception as e:
            logger.error(f"Error creating agent config: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to create agent configuration: {str(e)}"
            }
    
    @staticmethod
    def update_agent_config(client_id: str, config_id: str, config_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Update an existing agent configuration
        
        Args:
            client_id: Client ID to update configuration for
            config_id: Configuration ID to update
            config_data: Updated configuration data
            
        Returns:
            Tuple of (success, updated_config)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Get the existing configuration
            existing_config = db.get_agent_config(client_id, config_id)
            if not existing_config:
                return False, {
                    "status": "error",
                    "message": "Agent configuration not found"
                }
            
            # Update timestamp
            config_data["updated_at"] = datetime.now()
            
            # Update the configuration
            success = db.update_agent_config(client_id, config_id, config_data)
            
            if not success:
                return False, {
                    "status": "error",
                    "message": "Failed to update agent configuration"
                }
            
            # Get the updated configuration
            updated_config = db.get_agent_config(client_id, config_id)
            
            return True, {
                "status": "success",
                "message": "Agent configuration updated successfully",
                "config": updated_config
            }
        
        except Exception as e:
            logger.error(f"Error updating agent config: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to update agent configuration: {str(e)}"
            }
    
    @staticmethod
    def delete_agent_config(client_id: str, config_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete an agent configuration
        
        Args:
            client_id: Client ID to delete configuration for
            config_id: Configuration ID to delete
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Get the existing configuration
            existing_config = db.get_agent_config(client_id, config_id)
            if not existing_config:
                return False, {
                    "status": "error",
                    "message": "Agent configuration not found"
                }
            
            # Delete the configuration
            success = db.delete_agent_config(client_id, config_id)
            
            if not success:
                return False, {
                    "status": "error",
                    "message": "Failed to delete agent configuration"
                }
            
            return True, {
                "status": "success",
                "message": "Agent configuration deleted successfully"
            }
        
        except Exception as e:
            logger.error(f"Error deleting agent config: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to delete agent configuration: {str(e)}"
            }
    
    @staticmethod
    def run_agent(client_id: str, config_id: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Run an agent with the specified configuration
        
        Args:
            client_id: Client ID to run agent for
            config_id: Configuration ID to use for running the agent
            context: Optional context data for the agent
            
        Returns:
            Tuple of (success, result_data)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Get the agent configuration
            config = db.get_agent_config(client_id, config_id)
            if not config:
                return False, {
                    "status": "error",
                    "message": "Agent configuration not found"
                }
            
            # Prepare context
            if context is None:
                context = {}
            
            # Add client info to context
            context["client_id"] = client_id
            context["user_id"] = auth_data.get("user_id")
            context["user_name"] = auth_data.get("user_name")
            
            # Run the agent
            agent_result = run_agent(config, context)
            
            # Log the agent run
            run_data = {
                "client_id": client_id,
                "config_id": config_id,
                "config_name": config.get("name", ""),
                "context": context,
                "result": agent_result,
                "created_at": datetime.now()
            }
            db.log_agent_run(run_data)
            
            return True, {
                "status": "success",
                "message": "Agent run completed",
                "result": agent_result
            }
        
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to run agent: {str(e)}"
            }
    
    @staticmethod
    def get_agent_runs(client_id: str, limit: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Get recent agent runs for a client
        
        Args:
            client_id: Client ID to get runs for
            limit: Maximum number of runs to return
            
        Returns:
            Tuple of (success, runs_data)
        """
        try:
            db = get_db()
            
            # Check if client is authenticated
            auth_data = db.get_twitter_auth(client_id)
            if not auth_data:
                return False, {
                    "status": "error",
                    "message": "Not authenticated"
                }
            
            # Get agent runs
            runs = db.get_agent_runs(client_id, limit)
            
            return True, {
                "status": "success",
                "runs": runs
            }
        
        except Exception as e:
            logger.error(f"Error getting agent runs: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get agent runs: {str(e)}"
            }

    def create_agent(self, client_id: str, agent_type: str, agent_name: str, 
                   agent_config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a new agent for a client
        
        Args:
            client_id: Client ID to create agent for
            agent_type: Type of agent (tweeter, scheduler, analyzer)
            agent_name: Name for the agent
            agent_config: Configuration for the agent
            
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
            
            if not agent_type or agent_type not in self.agent_types:
                return False, {
                    "status": "error",
                    "message": f"Agent type must be one of: {', '.join(self.agent_types)}"
                }
            
            if not agent_name:
                return False, {
                    "status": "error",
                    "message": "Agent name is required"
                }
            
            # Generate a unique agent ID
            agent_id = f"{agent_type}_{uuid.uuid4().hex}"
            
            # Prepare agent data
            agent_data = {
                "agent_id": agent_id,
                "client_id": client_id,
                "agent_type": agent_type,
                "agent_name": agent_name,
                "config": agent_config or {},
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_run": None,
                "next_run": None
            }
            
            # If it's a scheduler agent, set next run time
            if agent_type == "scheduler":
                frequency = agent_config.get("frequency", "daily")
                time_of_day = agent_config.get("time_of_day", "09:00")
                
                # Calculate next run time
                now = datetime.now()
                if frequency == "daily":
                    hours, minutes = map(int, time_of_day.split(":"))
                    next_run = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    if next_run <= now:
                        next_run = next_run + timedelta(days=1)
                else:
                    # Default to running in 24 hours
                    next_run = now + timedelta(days=1)
                
                agent_data["next_run"] = next_run.isoformat()
            
            # Store agent in database
            db = get_db()
            db.store_agent(agent_id, agent_data)
            
            return True, {
                "status": "success",
                "agent_id": agent_id,
                "message": f"{agent_type.capitalize()} agent '{agent_name}' created successfully"
            }
        
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to create agent: {str(e)}"
            }
    
    def get_agent(self, client_id: str, agent_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Get agent details
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of agent to get
            
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
            
            if not agent_id:
                return False, {
                    "status": "error",
                    "message": "Agent ID is required"
                }
            
            # Get agent data
            db = get_db()
            agent_data = db.get_agent(agent_id)
            
            if not agent_data:
                return False, {
                    "status": "error",
                    "message": "Agent not found"
                }
            
            # Check if client owns the agent
            if agent_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Unauthorized: Client does not own this agent"
                }
            
            # Return agent data
            return True, {
                "status": "success",
                "agent": agent_data
            }
        
        except Exception as e:
            logger.error(f"Error getting agent: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get agent: {str(e)}"
            }
    
    def list_agents(self, client_id: str, agent_type: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        List all agents for a client
        
        Args:
            client_id: Client ID to list agents for
            agent_type: Optional filter by agent type
            
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
            
            # Validate agent type if provided
            if agent_type and agent_type not in self.agent_types:
                return False, {
                    "status": "error",
                    "message": f"Agent type must be one of: {', '.join(self.agent_types)}"
                }
            
            # Get agents from database
            db = get_db()
            agents = db.get_client_agents(client_id, agent_type)
            
            # Return agent list
            return True, {
                "status": "success",
                "agents": agents
            }
        
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to list agents: {str(e)}"
            }
    
    def update_agent(self, client_id: str, agent_id: str, 
                   update_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Update an existing agent
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of agent to update
            update_data: Data to update for the agent
            
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
            
            if not agent_id:
                return False, {
                    "status": "error",
                    "message": "Agent ID is required"
                }
            
            # Get agent data
            db = get_db()
            agent_data = db.get_agent(agent_id)
            
            if not agent_data:
                return False, {
                    "status": "error",
                    "message": "Agent not found"
                }
            
            # Check if client owns the agent
            if agent_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Unauthorized: Client does not own this agent"
                }
            
            # Update fields
            allowed_updates = ["agent_name", "config", "status"]
            updates_applied = []
            
            for field, value in update_data.items():
                if field in allowed_updates:
                    agent_data[field] = value
                    updates_applied.append(field)
            
            # Always update the updated_at timestamp
            agent_data["updated_at"] = datetime.now().isoformat()
            updates_applied.append("updated_at")
            
            # If config was updated and it's a scheduler agent, recalculate next_run
            if "config" in updates_applied and agent_data.get("agent_type") == "scheduler":
                frequency = agent_data["config"].get("frequency", "daily")
                time_of_day = agent_data["config"].get("time_of_day", "09:00")
                
                # Calculate next run time
                now = datetime.now()
                if frequency == "daily":
                    hours, minutes = map(int, time_of_day.split(":"))
                    next_run = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    if next_run <= now:
                        next_run = next_run + timedelta(days=1)
                else:
                    # Default to running in 24 hours
                    next_run = now + timedelta(days=1)
                
                agent_data["next_run"] = next_run.isoformat()
                updates_applied.append("next_run")
            
            # Save updated agent data
            db.store_agent(agent_id, agent_data)
            
            return True, {
                "status": "success",
                "agent_id": agent_id,
                "updated_fields": updates_applied,
                "message": f"Agent updated successfully"
            }
        
        except Exception as e:
            logger.error(f"Error updating agent: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to update agent: {str(e)}"
            }
    
    def delete_agent(self, client_id: str, agent_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Delete an agent
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of agent to delete
            
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
            
            if not agent_id:
                return False, {
                    "status": "error",
                    "message": "Agent ID is required"
                }
            
            # Get agent data
            db = get_db()
            agent_data = db.get_agent(agent_id)
            
            if not agent_data:
                return False, {
                    "status": "error",
                    "message": "Agent not found"
                }
            
            # Check if client owns the agent
            if agent_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Unauthorized: Client does not own this agent"
                }
            
            # Delete agent
            db.delete_agent(agent_id)
            
            return True, {
                "status": "success",
                "agent_id": agent_id,
                "message": "Agent deleted successfully"
            }
        
        except Exception as e:
            logger.error(f"Error deleting agent: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to delete agent: {str(e)}"
            }
    
    def run_agent(self, client_id: str, agent_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Run an agent manually
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of agent to run
            
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
            
            if not agent_id:
                return False, {
                    "status": "error",
                    "message": "Agent ID is required"
                }
            
            # Get agent data
            db = get_db()
            agent_data = db.get_agent(agent_id)
            
            if not agent_data:
                return False, {
                    "status": "error",
                    "message": "Agent not found"
                }
            
            # Check if client owns the agent
            if agent_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Unauthorized: Client does not own this agent"
                }
            
            # Check if agent is active
            if agent_data.get("status") != "active":
                return False, {
                    "status": "error",
                    "message": "Agent is not active"
                }
            
            # Record that we're running the agent
            agent_data["last_run"] = datetime.now().isoformat()
            agent_data["running"] = True
            db.store_agent(agent_id, agent_data)
            
            # Create a run record
            run_id = f"run_{uuid.uuid4().hex}"
            run_data = {
                "run_id": run_id,
                "agent_id": agent_id,
                "client_id": client_id,
                "started_at": datetime.now().isoformat(),
                "status": "running",
                "results": None
            }
            
            db.store_agent_run(run_id, run_data)
            
            # Execute the agent based on its type
            try:
                agent_type = agent_data.get("agent_type")
                agent_config = agent_data.get("config", {})
                
                results = None
                
                if agent_type == "tweeter":
                    results = self._run_tweeter_agent(client_id, agent_id, agent_config)
                elif agent_type == "scheduler":
                    results = self._run_scheduler_agent(client_id, agent_id, agent_config)
                elif agent_type == "analyzer":
                    results = self._run_analyzer_agent(client_id, agent_id, agent_config)
                else:
                    raise ValueError(f"Unknown agent type: {agent_type}")
                
                # Update run record with results
                run_data["completed_at"] = datetime.now().isoformat()
                run_data["status"] = "completed"
                run_data["results"] = results
                db.store_agent_run(run_id, run_data)
                
                # Update agent data
                agent_data["running"] = False
                agent_data["last_run_status"] = "success"
                agent_data["last_run_results"] = results
                
                # If it's a scheduler agent, calculate next run time
                if agent_type == "scheduler":
                    frequency = agent_config.get("frequency", "daily")
                    time_of_day = agent_config.get("time_of_day", "09:00")
                    
                    now = datetime.now()
                    if frequency == "daily":
                        hours, minutes = map(int, time_of_day.split(":"))
                        next_run = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                        if next_run <= now:
                            next_run = next_run + timedelta(days=1)
                    elif frequency == "hourly":
                        next_run = now + timedelta(hours=1)
                    elif frequency == "weekly":
                        # Run on same day next week
                        next_run = now + timedelta(days=7)
                    else:
                        # Default to running in 24 hours
                        next_run = now + timedelta(days=1)
                    
                    agent_data["next_run"] = next_run.isoformat()
                
                # Save agent data
                db.store_agent(agent_id, agent_data)
                
                return True, {
                    "status": "success",
                    "run_id": run_id,
                    "results": results,
                    "message": "Agent run completed successfully"
                }
            
            except Exception as e:
                logger.error(f"Agent run error: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Update run record with error
                run_data["completed_at"] = datetime.now().isoformat()
                run_data["status"] = "error"
                run_data["error"] = str(e)
                db.store_agent_run(run_id, run_data)
                
                # Update agent data
                agent_data["running"] = False
                agent_data["last_run_status"] = "error"
                agent_data["last_run_error"] = str(e)
                db.store_agent(agent_id, agent_data)
                
                return False, {
                    "status": "error",
                    "run_id": run_id,
                    "message": f"Agent run failed: {str(e)}"
                }
        
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            logger.error(traceback.format_exc())
            return False, {
                "status": "error",
                "message": f"Failed to run agent: {str(e)}"
            }
    
    def _run_tweeter_agent(self, client_id: str, agent_id: str, 
                          agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a tweeter agent
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of the agent
            agent_config: Agent configuration
            
        Returns:
            Results of the agent run
        """
        # In a real implementation, this would use AI to generate tweets
        # For this demo, we'll use a simple template approach
        
        templates = agent_config.get("templates", [
            "Check out our latest updates! #CryptoBunny",
            "Exciting news from the #CryptoBunny team!",
            "Stay tuned for more updates from #CryptoBunny"
        ])
        
        # Select a template
        content = random.choice(templates)
        
        # Post the tweet
        success, result = twitter_service.post_tweet(client_id, content)
        
        if not success:
            raise Exception(f"Failed to post tweet: {result.get('message')}")
        
        return {
            "tweet_id": result.get("tweet_id"),
            "content": content
        }
    
    def _run_scheduler_agent(self, client_id: str, agent_id: str, 
                            agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a scheduler agent
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of the agent
            agent_config: Agent configuration
            
        Returns:
            Results of the agent run
        """
        # Get target agent ID
        target_agent_id = agent_config.get("target_agent_id")
        if not target_agent_id:
            raise ValueError("Scheduler agent requires a target agent ID")
        
        # Get target agent
        db = get_db()
        target_agent = db.get_agent(target_agent_id)
        
        if not target_agent:
            raise ValueError(f"Target agent {target_agent_id} not found")
        
        if target_agent.get("client_id") != client_id:
            raise ValueError(f"Client does not own target agent {target_agent_id}")
        
        # Run the target agent
        success, result = self.run_agent(client_id, target_agent_id)
        
        if not success:
            raise Exception(f"Failed to run target agent: {result.get('message')}")
        
        return {
            "scheduled_agent_id": target_agent_id,
            "scheduled_agent_type": target_agent.get("agent_type"),
            "scheduled_run_id": result.get("run_id"),
            "scheduled_results": result.get("results")
        }
    
    def _run_analyzer_agent(self, client_id: str, agent_id: str, 
                           agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run an analyzer agent
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of the agent
            agent_config: Agent configuration
            
        Returns:
            Results of the agent run
        """
        # Get data source
        data_source = agent_config.get("data_source", "tweets")
        
        # Get tweets
        success, result = twitter_service.get_client_tweets(client_id)
        
        if not success:
            raise Exception(f"Failed to get client tweets: {result.get('message')}")
        
        tweets = result.get("tweets", [])
        
        if not tweets:
            return {
                "analysis": "No tweets found to analyze"
            }
        
        # In a real implementation, this would analyze the tweets with AI
        # For this demo, we'll provide some simple statistics
        
        # Count tweets
        tweet_count = len(tweets)
        
        # Calculate average tweet length
        total_length = sum(len(tweet.get("content", "")) for tweet in tweets)
        avg_length = total_length / tweet_count if tweet_count > 0 else 0
        
        # Find most recent tweet
        most_recent = max(tweets, key=lambda x: x.get("created_at", "")) if tweets else None
        
        return {
            "tweet_count": tweet_count,
            "average_length": avg_length,
            "most_recent_tweet": most_recent.get("content") if most_recent else None,
            "most_recent_time": most_recent.get("created_at") if most_recent else None,
            "analysis_time": datetime.now().isoformat()
        }
    
    def get_agent_runs(self, client_id: str, agent_id: str, 
                      limit: int = 10) -> Tuple[bool, Dict[str, Any]]:
        """
        Get run history for an agent
        
        Args:
            client_id: Client ID that owns the agent
            agent_id: ID of agent to get runs for
            limit: Maximum number of runs to return
            
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
            
            if not agent_id:
                return False, {
                    "status": "error",
                    "message": "Agent ID is required"
                }
            
            # Get agent data
            db = get_db()
            agent_data = db.get_agent(agent_id)
            
            if not agent_data:
                return False, {
                    "status": "error",
                    "message": "Agent not found"
                }
            
            # Check if client owns the agent
            if agent_data.get("client_id") != client_id:
                return False, {
                    "status": "error",
                    "message": "Unauthorized: Client does not own this agent"
                }
            
            # Get agent runs
            runs = db.get_agent_runs(agent_id, limit)
            
            # Return run history
            return True, {
                "status": "success",
                "agent_id": agent_id,
                "runs": runs
            }
        
        except Exception as e:
            logger.error(f"Error getting agent runs: {str(e)}")
            return False, {
                "status": "error",
                "message": f"Failed to get agent runs: {str(e)}"
            }


# Create a singleton instance
agent_service = AgentService() 