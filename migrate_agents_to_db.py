#!/usr/bin/env python3
"""
Utility script to migrate agent configurations from variables.py to the database.
This is a one-time migration tool to be run after the codebase has been updated
to use database-based agent configurations instead of the variables file.

Usage:
    python migrate_agents_to_db.py --client-id <client_id>

This will create database entries for all agents defined in the old variables.py file.
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from db import TweetDB, get_db
from schemas import AgentConfig, TwitterAuth
import json

# Attempt to import the variables file if it exists
try:
    from variables import AGENTS
except ImportError:
    print("Error: variables.py file not found. Please ensure the file exists.")
    print("This script is intended to migrate from variables.py to the database.")
    sys.exit(1)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Migrate agent configurations from variables.py to the database')
    parser.add_argument('--client-id', type=str, required=True, help='Client ID to associate with the migrated agents')
    return parser.parse_args()

def migrate_agents(client_id):
    """
    Migrate all agent configurations from variables.py to the database
    """
    # Load environment variables
    load_dotenv()
    
    # Connect to the database
    db = get_db()
    
    # Check if Twitter auth exists for this client ID
    auth_data = db.get_twitter_auth(client_id)
    if not auth_data:
        # Create a default auth if it doesn't exist
        auth_data = TwitterAuth(
            client_id=client_id,
            user_id=os.getenv("DEFAULT_USER_ID", ""),
            user_name=os.getenv("DEFAULT_USER_NAME", ""),
            api_key=os.getenv("API_KEY", ""),
            api_secret_key=os.getenv("API_SECRET_KEY", ""),
            bearer_token=os.getenv("BEARER_TOKEN", ""),
            access_token=os.getenv("ACCESS_TOKEN", ""),
            access_token_secret=os.getenv("ACCESS_TOKEN_SECRET", ""),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add_twitter_auth(auth_data)
        print(f"Created default Twitter auth for client ID: {client_id}")
    
    # Check that AGENTS is a dictionary
    if not isinstance(AGENTS, dict):
        print("Error: AGENTS in variables.py is not a dictionary.")
        sys.exit(1)
    
    # Count of successful migrations
    success_count = 0
    error_count = 0
    
    # Migrate each agent configuration
    for agent_name, agent_config in AGENTS.items():
        try:
            print(f"Migrating configuration for agent: {agent_name}")
            
            # Validate agent configuration
            if not isinstance(agent_config, dict):
                print(f"Warning: Configuration for {agent_name} is not a dictionary. Skipping.")
                error_count += 1
                continue
                
            # Create the agent configuration object with defaults for missing values
            config_data = AgentConfig(
                client_id=client_id,
                agent_name=agent_name,
                user_id=agent_config.get("USER_ID", auth_data["user_id"]),
                user_name=agent_config.get("USER_NAME", auth_data["user_name"]),
                user_personality=agent_config.get("USER_PERSONALITY", ""),
                style_rules=agent_config.get("STYLE_RULES", ""),
                content_restrictions=agent_config.get("CONTENT_RESTRICTIONS", ""),
                strategy=agent_config.get("STRATEGY", ""),
                remember=agent_config.get("REMEMBER", ""),
                mission=agent_config.get("MISSION", ""),
                questions=agent_config.get("QUESTION", []),
                engagement_strategy=agent_config.get("ENGAGEMENT_STRATEGY", ""),
                ai_and_agents=agent_config.get("AI_AND_AGENTS", []),
                web3_builders=agent_config.get("WEB3_BUILDERS", []),
                defi_experts=agent_config.get("DEFI_EXPERTS", []),
                thought_leaders=agent_config.get("THOUGHT_LEADERS", []),
                traders_and_analysts=agent_config.get("TRADERS_AND_ANALYSTS", []),
                knowledge_base=agent_config.get("KNOWLEDGE_BASE", ""),
                model_config=agent_config.get("MODEL_CONFIG", {}),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_active=True
            )
            
            # Save the configuration to the database
            result = db.add_agent_config(config_data)
            print(f"Migrated agent configuration for {agent_name}: {result['status']}")
            success_count += 1
            
        except Exception as e:
            print(f"Error migrating agent {agent_name}: {e}")
            error_count += 1
    
    print(f"\nMigration summary:")
    print(f"  - Successfully migrated: {success_count} agents")
    print(f"  - Errors: {error_count} agents")
    
    if success_count > 0:
        print("\nYou can now update your .env file with:")
        print(f"DEFAULT_CLIENT_ID={client_id}")
        print("And set AGENT_NAME to one of the migrated agents to use it as default")

def main():
    # Parse command line arguments
    args = parse_arguments()
    client_id = args.client_id
    
    # Migrate the agents
    migrate_agents(client_id)
    print("Migration completed successfully!")

if __name__ == "__main__":
    main() 