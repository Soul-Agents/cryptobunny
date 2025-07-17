# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Soul Agents CryptoBunny** is a dynamic AI agent system for automated social media engagement on X (Twitter) in the crypto/Web3 space. The system uses MongoDB-stored personalities managed through the SoulSync frontend application.

## Common Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (requires AGENT_NAME environment variable)
python main.py

# Database testing
python db_testing.py

# Add tweets to vector database
python add_tweets_to_vectordb.py
```

## Architecture Overview

### Core Components
- **`main.py`**: Primary application entry point with agent execution logic
- **`variables.py`**: Multi-agent configuration system defining 7 AI personalities
- **`schemas.py`**: Pydantic models for tweet data structures
- **`db.py`**: MongoDB database operations and connection management
- **`db_utils.py`**: Database context manager utilities

### Technology Stack
- **Runtime**: Python 3.12+
- **AI Framework**: LangChain for LLM orchestration
- **LLM Providers**: OpenAI GPT-4, Grok, DeepSeek
- **Vector Database**: Pinecone for knowledge retrieval
- **Database**: MongoDB for data persistence
- **Social API**: Tweepy for Twitter/X integration
- **Search**: Tavily for web search capabilities

### Agent System

The system features dynamic AI personalities managed through MongoDB and the SoulSync frontend:

- **Database-Driven Configuration**: All agent personalities stored in MongoDB
- **Frontend Management**: SoulSync web application for personality customization
- **Dynamic Loading**: Agent configurations loaded from database at runtime
- **Multi-Client Support**: Each client can have unique agent setups
- **Flexible Personality System**: Traits, engagement strategies, and targets configurable via UI

**Note**: The `variables.py` file contains legacy examples - actual personality management is now database-driven.

## Key Configuration

### Required Environment Variables
```bash
# Twitter API credentials
API_KEY=your_twitter_api_key
API_SECRET_KEY=your_twitter_api_secret
BEARER_TOKEN=your_twitter_bearer_token
ACCESS_TOKEN=your_twitter_access_token
ACCESS_TOKEN_SECRET=your_twitter_access_secret

# External APIs
TAVILY_API_KEY=your_tavily_api_key
API_KEY_OPENAI=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GROK_API_KEY=your_grok_api_key

# Database
MONGODB_URI=your_mongodb_uri
MONGODB_URL=your_mongodb_url
PINECONE_API_KEY=your_pinecone_api_key

# Agent Selection (managed via database)
# Agent personalities are now loaded from MongoDB via SoulSync frontend
# Legacy AGENT_NAME environment variable may still be used for backwards compatibility
```

### Agent Configuration
Agent personalities are now managed through:
- **MongoDB Database**: Stores all personality configurations
- **SoulSync Frontend**: Web interface for managing agent personalities
- **Dynamic Loading**: Configurations loaded from database at runtime

Each personality configuration includes:
- Personality definition with example interactions
- Style rules and content restrictions
- Target account lists categorized by type
- Knowledge base with core themes and behaviors
- Model configuration (temperature, top_p, etc.)

**Important**: The `variables.py` file contains legacy examples - actual configuration is database-driven.

## Database Schema

### MongoDB Collections
- **tweets**: Standard tweet data
- **written_ai_tweets**: AI-generated tweets with tracking
- **written_ai_tweets_replies**: AI-generated replies with context
- **ai_mention_tweets**: Tweets mentioning the AI agents

### Data Models (schemas.py)
- **Tweet**: Standard tweet structure with metrics and metadata
- **WrittenAITweet**: AI-generated tweets with tracking
- **WrittenAITweetReply**: AI-generated replies with context
- **PublicMetrics**: Engagement metrics (likes, retweets, etc.)

## Development Guidelines

### Database Operations
- Always use `get_db()` context manager for database operations
- Database connection includes retry logic and error handling
- Use `db_utils.py` for standardized database context management

### Agent Selection
- Agent personalities are loaded from MongoDB database
- Configuration managed through SoulSync frontend application
- Each client can have unique agent configurations
- Legacy `AGENT_NAME` environment variable may still be supported for backwards compatibility
- Only one agent runs at a time - no multi-agent orchestration currently

### Rate Limiting
- Twitter API calls include `wait_on_rate_limit` handling
- Built-in rate limiting prevents API quota exhaustion
- Duplicate detection prevents replying to own tweets

### Core Functionality
- **Timeline Reading**: Monitors Twitter/X timeline for relevant content
- **Smart Replies**: Context-aware responses using vector knowledge base
- **Original Tweets**: Generates and posts original content
- **User Following**: Automated following of relevant accounts
- **Tweet Liking**: Engagement through likes
- **Search Integration**: Both Twitter search and web search capabilities

## Data Management

### Vector Database
- Uses Pinecone for storing and retrieving relevant context
- Run `add_tweets_to_vectordb.py` to populate knowledge base
- Provides context-aware responses based on stored knowledge

### Backup System
- Data exports available in `/exports/` directory
- JSON format backups for all major collections
- Includes tweet data, AI responses, and metadata