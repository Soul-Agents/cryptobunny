# Soul Agents: AI-Powered Social Agents 🐰

A sophisticated multi-agent system for engaging with the crypto and Web3 community on X (Twitter).

**Production-ready platform** serving 5 clients with $28 MRR (targeting $1k+), featuring AI agents with dynamic personalities managed through MongoDB and configured via the SoulSync frontend.

✨ **Boost your social media presence** • **Post relevant content** • **Engage authentically** • **Grow your followers**

*Let the AI handle the hard work while you focus on building your project.*

## 🌟 Features

### Core Capabilities
- **Dynamic AI Agent System**: AI personalities dynamically loaded from MongoDB database and configured via SoulSync frontend
- **Advanced LLM Integration**: GPT-4, Grok, DeepSeek for natural and contextual interactions
- **Vector Database Intelligence**: Pinecone for efficient knowledge retrieval and context-aware responses
- **Real-time Web Research**: Tavily integration for fact verification and current events
- **Comprehensive Social Automation**: Tweets, replies, likes, follows, timeline monitoring, and mentions
- **MongoDB Analytics**: Robust data persistence with interaction history and performance tracking
- **Smart Duplicate Prevention**: Avoids replying to own tweets and duplicate interactions
- **Rate Limiting Protection**: Built-in Twitter API rate limit handling

### Advanced Features
- **Conversation Memory**: LangChain integration for contextual conversations
- **Target Account Categorization**: AI & Agents, Web3 Builders, DeFi Experts, and more
- **Multi-Model Temperature Tuning**: Fine-tuned parameters for each personality
- **Database-Backed Analytics**: Tweet history, engagement metrics, and performance tracking
- **Flexible Agent Selection**: Environment-based agent switching for different use cases
- **Real-Time Web Search**: Tavily integration for up-to-date information in tweets (ElizaOS lacks this)
- **Rich Personality Configuration**: UI-driven persona customization with knowledge base integration

### In Development
- **AI-Enabled Social Trading**: Automated trading insights and social signals
- **Enhanced Discovery Service**: Automated content and account discovery with scoring
- **Advanced Scheduling**: Variance-based posting intervals for natural behavior
- **Plugin Architecture**: Modular components for better extensibility
## 🛠 Tech Stack

### Core Technologies
- **Python 3.12+** - Modern Python runtime
- **LangChain** - LLM orchestration and conversation management
- **OpenAI GPT-4, Grok, DeepSeek** - Multiple LLM providers for diverse personalities
- **Pinecone** - Vector database for intelligent knowledge retrieval
- **MongoDB** - Document database for tweet storage and analytics
- **Tweepy** - Twitter API v2 integration with rate limiting
- **Tavily** - Web search and real-time information gathering
- **Pydantic** - Data validation and serialization
- **python-dotenv** - Environment variable management

## 📋 Prerequisites

- Python 3.12 or higher
- MongoDB instance
- Pinecone account
- X (Twitter) Developer Account with Elevated access
- OpenAI API key
- Tavily API key

## 🚀 Setup

1. Clone the repository:

```bash
git clone (https://github.com/Soul-Agents/cryptobunny.git)
cd cryptobunny
```

2. Create and activate a virtual environment:

```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:

```
API_KEY=your_twitter_api_key
API_SECRET_KEY=your_twitter_api_secret
BEARER_TOKEN=your_twitter_bearer_token
ACCESS_TOKEN=your_twitter_access_token
ACCESS_TOKEN_SECRET=your_twitter_access_secret
TAVILY_API_KEY=your_tavily_api_key
API_KEY_OPENAI=your_openai_api_key
MONGODB_URI=your_mongodb_uri
MONGODB_URL=your_mongodb_url
PINECONE_API_KEY=your_pinecone_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GROK_API_KEY=your_grok_api_key
```

5. Verify environment setup:

```bash
python main.py
```

## 🤖 Agent System

Our system features dynamic AI agent personalities managed through MongoDB and configured via the **SoulSync frontend application**:

- **Database-Driven Personalities**: All agent configurations stored in MongoDB
- **Frontend Management**: SoulSync web app for easy personality customization
- **Dynamic Loading**: Agent personalities loaded from database at runtime
- **Flexible Configuration**: Personality traits, engagement strategies, and target accounts configurable via UI
- **Multi-Client Support**: Each client can have unique agent configurations

**Note**: The `variables.py` file contains legacy template examples - actual personality management is now database-driven through the SoulSync frontend.

## 🔐 Security & Best Practices

- **Secure API Management**: All credentials stored in environment variables
- **Rate Limiting Protection**: Built-in Twitter API rate limiting with retry logic
- **Error Handling**: Comprehensive error handling for API requests and database operations
- **Safe Engagement Patterns**: Duplicate prevention and conversation tracking
- **Database Security**: MongoDB connection with retry logic and secure URI handling
- **Input Validation**: Pydantic models for data validation and sanitization
- **Environment Isolation**: Agent-specific configurations prevent cross-contamination

## 📊 Business Metrics

- **5 Active Clients** - Production-ready platform serving real customers
- **$28 Monthly Recurring Revenue** - Growing subscription base
- **Target: $1,000+ MRR** - Scaling towards significant revenue milestone
- **2 Recurring Clients** - Proven customer retention and satisfaction
- **Frontend Integration** - Connected with SoulSync frontend application

## 🆚 Competitive Advantages vs ElizaOS

### Where CryptoBunny Excels
- ✅ **Configurable AI Personalities** - Multiple specialized templates vs single character
- ✅ **Real-Time Web Search** - Tavily integration for current information (ElizaOS lacks this)
- ✅ **Advanced Database Analytics** - MongoDB with comprehensive tweet tracking
- ✅ **Multiple LLM Support** - GPT-4, Grok, DeepSeek integration
- ✅ **Vector Database Intelligence** - Pinecone for context-aware responses
- ✅ **Production-Ready** - Serving 5 clients with proven revenue

### Where We Need to Catch Up
- ❌ **Direct Message Support** - ElizaOS has DM automation, we don't
- ❌ **AI Image Generation** - ElizaOS creates graphics, we only do text
- ❌ **Retweets & Quote Tweets** - Limited engagement action variety
- ❌ **Weighted Discovery Scoring** - Less sophisticated content discovery
- ❌ **Configurable Posting Intervals** - Less flexible autonomous posting

## 🚧 Roadmap & TODO

### High Priority Features (Missing from ElizaOS Comparison)
- [ ] **AI Graphic Generation**: Create visuals, charts, memes, and illustrations to accompany tweets
- [ ] **Retweets & Quote Tweets**: Automated retweeting and quote tweeting with AI-generated commentary
- [ ] **Enhanced Discovery Service**: Weighted scoring algorithms for content and account discovery
- [ ] **Configurable Autonomous Posting**: Scheduled posts with customizable intervals and variance
- [ ] **Multi-Agent Orchestration**: Run multiple personalities simultaneously

### Medium Priority Enhancements
- [ ] **Direct Message (DM) Support**: AI-powered direct message reading and sending via Twitter API
- [ ] **Follower Growth Automation**: Criteria-based following with limits per cycle (min follower count, etc.)
- [ ] **Engagement Action Toggles**: Configurable on/off switches for likes, retweets, quotes
- [ ] **Content Safety Filters**: Advanced filtering and compliance mechanisms
- [ ] **Approval Workflows**: Optional human review processes for sensitive content
- [ ] **Enhanced Caching & Retry**: Sophisticated caching with exponential backoff for rate limits

### Enterprise Features
- [ ] **Microservices Architecture**: Break down into smaller, focused services
- [ ] **Event-Driven Communication**: Implement event-based messaging between components
- [ ] **Horizontal Scaling**: Design for multi-instance deployment
- [ ] **Comprehensive Monitoring**: Advanced logging, metrics collection, and alerting
- [ ] **Configuration Management**: Centralized configuration system with hot reloading

### AI & Social Trading Features
- [ ] **Social Signal Analysis**: Analyze social sentiment for trading insights
- [ ] **Automated Trading Integration**: Connect social signals to trading strategies
- [ ] **Influence Scoring**: Measure and track social influence metrics
- [ ] **Community Growth Analytics**: Advanced metrics for follower quality and engagement

### ElizaOS Feature Parity
- [ ] **Twitter API v2 OAuth**: Upgrade to more robust authentication
- [ ] **Configurable Engagement Cycles**: Set limits on follows/engagements per cycle
- [ ] **Quality Account Filtering**: Minimum follower count and engagement thresholds
- [ ] **Content Type Expansion**: Support for polls, threads, and multimedia content
- [ ] **Dry Run Mode**: Testing mode for new features without live posting

## 🤝 Contributing

We welcome contributions! Please read our contributing guidelines and submit pull requests for any improvements.


---

Created with 💖 by Soul Agents Team
