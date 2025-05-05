# Migrating from variables.py to Database Configuration

This document describes the changes made to move agent configurations from the `variables.py` file to the database.

## Overview

Previously, agent configurations were stored in a static `variables.py` file. This approach had several limitations:

- Changes required code modifications
- No ability to manage multiple configurations for the same agent
- No client-specific customizations
- No way to modify configurations at runtime

The new approach stores all agent configurations in the MongoDB database, providing:

- Dynamic configuration management
- Client-specific agent configurations
- Runtime configuration changes
- Separation of configuration from code

## Key Changes

1. Removed dependencies on `variables.py` from:

   - `main.py`
   - `db.py`
   - `api.py`

2. Added new functions to load and manage agent configurations:

   - `load_agent_config()` - Loads configuration from the database
   - `set_global_agent_variables()` - Sets global variables from a configuration
   - `initialize_from_env()` - Initializes from environment variables

3. Updated API endpoints to use database configurations:

   - Modified `/run-agent/<client_id>/<agent_name>`
   - Updated `/agent-config` endpoints
   - Changed `/agent-templates` to use database

4. Added a migration script:
   - `migrate_agents_to_db.py` - Utility to migrate existing configurations

## How to Migrate

1. Set up the `.env` file with required environment variables:

   ```
   DEFAULT_CLIENT_ID=your_client_id
   AGENT_NAME=agent_name
   ```

2. Run the migration script to transfer existing configurations:

   ```
   python migrate_agents_to_db.py --client-id your_client_id
   ```

3. Verify the configurations in the database:
   ```
   # Using the API
   curl http://localhost:5000/agent-config/your_client_id
   ```

## Environment Variables

The following environment variables are used:

- `DEFAULT_CLIENT_ID` - Default client ID to use when loading configurations
- `AGENT_NAME` - Default agent name to load at startup
- `DEFAULT_USER_ID` - Fallback user ID (optional)
- `DEFAULT_USER_NAME` - Fallback username (optional)

## Schema

Agent configurations use the `AgentConfig` schema:

```python
class AgentConfig(TypedDict):
    client_id: str
    agent_name: str
    user_id: str
    user_name: str
    user_personality: str
    style_rules: str
    content_restrictions: str
    strategy: str
    remember: str
    mission: str
    questions: List[str]
    engagement_strategy: str
    ai_and_agents: List[str]
    web3_builders: List[str]
    defi_experts: List[str]
    thought_leaders: List[str]
    traders_and_analysts: List[str]
    knowledge_base: str
    model_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool
```

## API Endpoints

- `GET /agent-config/<client_id>` - Get all agent configurations for a client
- `GET /agent-config/<client_id>/<agent_name>` - Get a specific agent configuration
- `POST /agent-config` - Create or update an agent configuration
- `PUT /agent-config/<client_id>/<agent_name>` - Update a specific configuration
- `DELETE /agent-config/<client_id>/<agent_name>` - Delete a configuration
- `GET /agent-templates` - Get a list of available agent templates

## Compatibility

The changes maintain backward compatibility with code that expected global variables.
New code should prefer using the database functions directly rather than relying on
global variables populated from the database.
