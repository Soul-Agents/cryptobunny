# Soul Agents: AI-Powered Social Agents 🐰

A sophisticated multi-agent system for engaging with the crypto and Web3 community on X (Twitter).

## 🌟 Features

- **Multi-Agent System**: Multiple AI personalities with unique characteristics and engagement strategies
- **Intelligent Engagement**: Uses advanced LLMs (GPT, Gemini, DeepSeek) for natural and contextual interactions
- **Vector Database Integration**: Leverages Pinecone for efficient knowledge retrieval and context management
- **Smart Search Capabilities**: Integrated with Tavily for real-time web research and fact verification
- **Automated Social Features**: Handles tweets, replies, likes, and follows with personality-appropriate responses
- **MongoDB Integration**: Robust data persistence and interaction history tracking

## 🛠 Tech Stack

- Python 3.12+
- LangChain for LLM orchestration
- OpenAI, Gemini, DeepSeek for LLM generation
- Pinecone for vector storage
- MongoDB for data persistence
- Tweepy for X (Twitter) API integration
- Tavily for web search capabilities

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

## 🤖 Agent Personalities

- Each agent maintains its unique personality while engaging with the community

## 🔐 Security

- Secure API key management through environment variables
- Rate limiting implementation
- Error handling for API requests
- Safe engagement patterns

---

Created with 💖 by Soul Agents Team
