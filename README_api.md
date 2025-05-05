# CryptoBunny API Documentation

This document describes the API endpoints for authentication and configuration of the CryptoBunny agent system.

## Table of Contents

1. [Overview](#overview)
2. [Twitter Authentication](#twitter-authentication)
3. [Agent Configuration](#agent-configuration)
4. [Frontend Endpoints](#frontend-endpoints)
5. [Running the API](#running-the-api)

## Overview

The API provides endpoints for:

1. Twitter authentication via OAuth
2. Managing agent configurations
3. Retrieving available agent templates
4. Running agents with specific configurations
5. Frontend-friendly endpoints for easy integration

## Twitter Authentication

### Initiate Twitter Authentication

```
GET /auth/twitter?client_id={optional_client_id}
```

Initiates the Twitter OAuth flow. If `client_id` is not provided, a new UUID will be generated.

### Twitter Authentication Callback

```
GET /callback
```

Callback endpoint that Twitter redirects to after the user authorizes the application. This endpoint:

- Retrieves and stores the access token and token secret
- Saves the user's Twitter information to the database
- Redirects to the frontend with success parameters

### Get Twitter Authentication Info

```
GET /twitter-auth/{client_id}
```

Retrieves (non-sensitive) Twitter authentication information for a client.

### Delete Twitter Authentication

```
DELETE /twitter-auth/{client_id}
```

Deletes Twitter authentication information for a client.

## Agent Configuration

### Create Agent Configuration

```
POST /agent-config
```

Creates a new agent configuration based on an existing template. The request body should contain:

```json
{
  "client_id": "your_client_id",
  "agent_name": "BUNNY",
  "customField1": "custom value 1",
  "customField2": "custom value 2"
}
```

Required fields:

- `client_id`: The client ID obtained from authentication
- `agent_name`: The name of the agent template to use (e.g., "BUNNY", "NEOAI", etc.)

Optional fields:

- Any custom configuration parameters to override the template values

### Get All Agent Configurations

```
GET /agent-config/{client_id}
```

Retrieves all agent configurations for a client.

### Get Agent Configuration

```
GET /agent-config/{client_id}/{agent_name}
```

Retrieves a specific agent configuration.

### Update Agent Configuration

```
PUT /agent-config/{client_id}/{agent_name}
```

Updates an existing agent configuration. The request body should contain the fields to update.

### Delete Agent Configuration

```
DELETE /agent-config/{client_id}/{agent_name}
```

Deletes a specific agent configuration.

### Get Agent Templates

```
GET /agent-templates
```

Retrieves all available agent templates with basic information.

## Frontend Endpoints

These endpoints are specifically designed for frontend applications to easily integrate with the API.

### Home Page

```
GET /
```

Returns basic API information and available endpoints.

### Frontend Login

```
GET /login?redirect_url={frontend_url}&client_id={optional_client_id}
```

Initiates the Twitter OAuth flow and redirects to the specified URL after completion.
If `redirect_url` is not provided, it defaults to the `FRONTEND_URL` environment variable.

### Authentication Status

```
GET /auth/status?client_id={client_id}
```

Checks if a client is authenticated. Returns authentication status and non-sensitive user data.

### Dashboard Data

```
GET /dashboard/{client_id}
```

Retrieves dashboard data for a client, including:

- User information
- Configured agents
- Available templates
- Agent count

### Create Agent (Frontend-friendly)

```
POST /create-agent/{client_id}
```

Creates a new agent from a template with optional customizations. The request body should contain:

```json
{
  "template": "BUNNY",
  "name": "MyCustomAgent",
  "personality": "Custom personality text",
  "style": "Custom style rules",
  "knowledge": "Custom knowledge base"
}
```

Required fields:

- `template`: The template to base the agent on
- `name`: The name for the new agent

### Run Agent

```
POST /run-agent/{client_id}/{agent_name}
```

Runs an agent with a specific prompt or action. The request body should contain:

```json
{
  "action": "default",
  "question": "Custom question text"
}
```

Parameters:

- `action`: Either "default" (uses random question from agent's question bank) or "custom" (uses provided question)
- `question`: The custom question text (required if action is "custom")

### Agent History

```
GET /agent-history/{client_id}/{agent_name}
```

Retrieves the activity history for a specific agent, including:

- Recent tweets posted by the agent
- Recent replies posted by the agent

## Running the API

### Prerequisites

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Set up environment variables (in .env file):
   ```
   API_KEY=your_twitter_api_key
   API_SECRET_KEY=your_twitter_api_secret
   TWITTER_CALLBACK_URL=your_callback_url
   MONGODB_URI=your_mongodb_connection_string
   FLASK_SECRET_KEY=your_flask_secret_key
   FRONTEND_URL=your_frontend_url
   ```

### Starting the Server

Run the API server:

```
python api.py
```

The server will start on port 5000 by default, or the port specified in the `PORT` environment variable.

## Authentication Flow

1. User visits the frontend application
2. Frontend redirects to `/login` with appropriate parameters
3. User is redirected to Twitter for authentication
4. After authentication, user is redirected back to the frontend with the client ID
5. Frontend stores the client ID and uses it for all subsequent API calls
6. Frontend can check authentication status with `/auth/status`

## Agent Management Flow

1. User authenticates and receives a client ID
2. Frontend retrieves available agent templates via `/agent-templates`
3. User creates a new agent via `/create-agent/{client_id}` with desired template and customizations
4. Frontend displays the user's agents via `/dashboard/{client_id}`
5. User can run agents via `/run-agent/{client_id}/{agent_name}`
6. User can view agent activity via `/agent-history/{client_id}/{agent_name}`

## Security Considerations

- Twitter API keys and access tokens are stored securely in the database
- Only non-sensitive information is returned to the client
- Flask sessions are used to maintain state during the OAuth flow
- CORS is enabled with credential support for secure cross-origin requests
