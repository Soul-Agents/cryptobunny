# CryptoBunny API

CryptoBunny is a platform that enables users to create and manage Twitter bots powered by AI agents.

## Project Structure

The API has been restructured for better maintainability and separation of concerns:

```
app/
├── __init__.py                  # Flask app initialization
├── config/                      # Configuration management
│   ├── __init__.py
│   └── config.py                # Environment variables and settings
├── models/                      # Data models
│   ├── __init__.py
│   ├── agent.py                 # Agent models
│   └── twitter.py               # Twitter auth models
├── routes/                      # API routes using blueprints
│   ├── __init__.py
│   ├── agent.py                 # Agent routes
│   ├── auth.py                  # Authentication routes
│   ├── dashboard.py             # Dashboard routes
│   └── twitter.py               # Twitter-specific routes
└── utils/                       # Utilities
    ├── __init__.py
    └── db.py                    # Database utilities
```

## Getting Started

### Prerequisites

- Python 3.8+
- MongoDB
- Twitter Developer Account (for API access)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables (see `.env.example`)
4. Run the application:
   ```
   python wsgi.py
   ```

## API Endpoints

### Authentication

- `GET /auth/twitter`: Initiate Twitter OAuth flow
- `GET /auth/callback`: Handle Twitter OAuth callback
- `GET /auth/status`: Check authentication status
- `POST /auth/connect-twitter-account`: Start Twitter OAuth with simplified user experience

### Agent Management

- `POST /agent/config`: Create or update agent configuration
- `GET /agent/config/<client_id>`: Get all agent configurations for a client
- `GET /agent/config/<client_id>/<agent_name>`: Get a specific agent configuration
- `PUT /agent/config/<client_id>/<agent_name>`: Update a specific agent configuration
- `DELETE /agent/config/<client_id>/<agent_name>`: Delete a specific agent configuration
- `GET /agent/templates`: Get all available agent templates
- `POST /agent/run/<client_id>/<agent_name>`: Run an agent with a specific prompt or action
- `GET /agent/history/<client_id>/<agent_name>`: Get activity history for a specific agent
- `POST /agent/create/<client_id>`: Create a new agent with provided configuration
- `POST /agent/test/<client_id>/<agent_name>`: Test an agent configuration

### Twitter Operations

- `GET /twitter/auth/<client_id>`: Get Twitter auth info for a client
- `DELETE /twitter/auth/<client_id>`: Delete Twitter auth info
- `POST /twitter/auth`: Save Twitter API keys
- `POST /twitter/validate-credentials`: Validate Twitter API credentials
- `POST /twitter/post-tweet/<client_id>`: Post a tweet on behalf of a user
- `GET /twitter/users`: Get all Twitter users who have connected their accounts

### Dashboard

- `GET /dashboard/<client_id>`: Get dashboard data for a client
- `GET /dashboard/stats/<client_id>`: Get usage statistics for a client
- `GET /dashboard/activity/<client_id>`: Get recent activity for all agents owned by a client

---

Created with 💖 by Soul Agents Team
