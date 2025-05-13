# region Imports
import tweepy
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
# from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
# import pinecone
# import google.generativeai as genai
# from langchain.tools.retriever import create_retriever_tool
import os
from db import TweetDB
from db_utils import get_db
from tavily_domains import TAVILY_DOMAINS
from dotenv import load_dotenv
from datetime import datetime, timezone
from schemas import Tweet, WrittenAITweet, WrittenAITweetReply, PublicMetrics, AgentConfig, TwitterAuth
import random
from openai import OpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from typing import List, Optional, Any, Dict
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import  MongoDBChatMessageHistory
from pymongo import MongoClient
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Load environment variables
load_dotenv(override=True)

# region Environment Configuration
# API_KEY = os.getenv("API_KEY")
# API_SECRET_KEY = os.getenv("API_SECRET_KEY")
# BEARER_TOKEN = os.getenv("BEARER_TOKEN")
# ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
# ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
API_KEY_OPENAI = os.getenv("API_KEY_OPENAI")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_URL = os.getenv("MONGODB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# Check for alternate OpenAI API key names
if not API_KEY_OPENAI:
    API_KEY_OPENAI = os.getenv("OPENAI_API_KEY")
    if API_KEY_OPENAI:
        print("Using OPENAI_API_KEY environment variable")
    else:
        print("WARNING: Neither API_KEY_OPENAI nor OPENAI_API_KEY environment variables are set")

# Default agent values (will be overridden by database settings)
USER_ID = os.getenv("DEFAULT_USER_ID", "")
USER_NAME = os.getenv("DEFAULT_USER_NAME", "")
USER_PERSONALITY = ""
STYLE_RULES = ""
CONTENT_RESTRICTIONS = ""
STRATEGY = ""
REMEMBER = ""
MISSION = ""
QUESTION = []
ENGAGEMENT_STRATEGY = ""
AI_AND_AGENTS = []
WEB3_BUILDERS = []
DEFI_EXPERTS = []
THOUGHT_LEADERS = []
TRADERS_AND_ANALYSTS = []
KNOWLEDGE_BASE = ""
FAMOUS_ACCOUNTS = []

# endregion


# Verify loaded variables
def verify_env_vars():
    required_vars = [
        "TAVILY_API_KEY",
        "API_KEY_OPENAI",
        "MONGODB_URI",
        "MONGODB_URL",
    ]
    
    # Variables that are good to have but not strictly required
    optional_vars = [
        "PINECONE_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROK_API_KEY",
    ]

    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)

    if missing_required:
        print("❌ Missing required environment variables:")
        for var in missing_required:
            print(f"  - {var}")
        return False
    
    if missing_optional:
        print("⚠️ Missing optional environment variables (some features may be limited):")
        for var in missing_optional:
            print(f"  - {var}")

    print("✅ All required environment variables are set")
    return True


# Call this before initializing any clients
if not verify_env_vars():
    raise EnvironmentError("Missing required environment variables")


# region Database Configuration
def get_db():
    return TweetDB()


# Load agent configuration from database
def load_agent_config(client_id: str) -> Optional[AgentConfig]:
    """
    Load agent configuration from the database
    
    Args:
        client_id (str): The client ID
        
    Returns:
        Optional[Dict[str, Any]]: The agent configuration if found, None otherwise
    """
    try:
        if not client_id:
            print("Error: client_id is required")
            return None
            
        # Get the agent configuration from the database
        db = get_db()
        config = db.get_agent_config(client_id)
        
        if not config:
            print(f"No configuration found for client_id: {client_id}")
            return None
        
        # Initialize Twitter client with user credentials
        TwitterClient.initialize(config.get("user_id"))
        
        # Combine the configuration into a single dictionary
        agent_config = {
            # Agent identity
            "USER_ID": config.get("user_id", ""),
            "USER_NAME": config.get("user_name", ""),
            "USER_PERSONALITY": config.get("user_personality", ""),
            
            # Communication style
            "STYLE_RULES": config.get("style_rules", ""),
            "CONTENT_RESTRICTIONS": config.get("content_restrictions", ""),
            
            # Strategy
            "STRATEGY": config.get("strategy", ""),
            "REMEMBER": config.get("remember", ""),
            "MISSION": config.get("mission", ""),
            "QUESTION": config.get("questions", []),
            
            # Engagement strategy
            "ENGAGEMENT_STRATEGY": config.get("engagement_strategy", ""),
            
            # Target accounts
            "AI_AND_AGENTS": config.get("ai_and_agents", []),
            "WEB3_BUILDERS": config.get("web3_builders", []),
            "DEFI_EXPERTS": config.get("defi_experts", []),
            "THOUGHT_LEADERS": config.get("thought_leaders", []),
            "TRADERS_AND_ANALYSTS": config.get("traders_and_analysts", []),
            
            # Knowledge base
            "KNOWLEDGE_BASE": config.get("knowledge_base", ""),
            
            # Model configuration
            "MODEL_CONFIG": config.get("model_config", {}),
            
            # Metadata
            "CLIENT_ID": client_id,
            "IS_ACTIVE": config.get("is_active", True)
        }
        
        return agent_config
        
    except Exception as e:
        print(f"Error loading agent configuration: {e}")
        return None

# endregion

# region LLM Configuration and embeddings
def initialize_llm(model_config=None):
    """
    Initialize the language model based on configuration.
    
    Args:
        model_config (dict): Model configuration parameters
        
    Returns:
        BaseChatModel: The initialized language model
    """
    if not API_KEY_OPENAI:
        raise ValueError("OPENAI_API_KEY or API_KEY_OPENAI environment variable must be set")
        
    if not model_config:
        print("Warning: No model config provided, using default GPT-4 configuration")
        return ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            top_p=0.9,
            api_key=API_KEY_OPENAI,
        )
    
    model_type = model_config.get("type", "").lower()
    print(model_config, "MODEL CONFIG")
    try:
        if model_type == "gpt-4" or model_type == "gpt-3.5-turbo" or model_type.startswith("gpt"):
            return ChatOpenAI(
                model=model_config.get("type", "gpt-4"),
                temperature=model_config.get("temperature", 0.7),
                top_p=model_config.get("top_p", 0.9),
                presence_penalty=model_config.get("presence_penalty", 0.0),
                frequency_penalty=model_config.get("frequency_penalty", 0.0),
                api_key=API_KEY_OPENAI,
            )
        elif model_type == "gemini" or model_type == "gemini-pro":
            # Configure Gemini integration
            # genai.configure(api_key=GEMINI_API_KEY)
            # return ChatGoogleGenerativeAI(
            #     model="gemini-pro",
            #     temperature=model_config.get("temperature", 0.7),
            #     top_p=model_config.get("top_p", 0.95),
            #     top_k=model_config.get("top_k", 40),
            #     max_output_tokens=model_config.get("max_tokens", 8192),
            # )
            print("Warning: Gemini model requested but implementation commented out")
            return ChatOpenAI(model="gpt-4", api_key=API_KEY_OPENAI)  # Fallback
        elif model_type == "grok":
            return ChatOpenAI(
                model="gpt-4",  # Grok not directly supported yet, using GPT-4 as fallback
                temperature=model_config.get("temperature", 0.7),
                top_p=model_config.get("top_p", 0.95),
                presence_penalty=model_config.get("presence_penalty", 0.0),
                frequency_penalty=model_config.get("frequency_penalty", 0.0),
                api_key=GROK_API_KEY,
            )
        elif model_type == "deepseek" or model_type == "deepseek-chat":
            return ChatOpenAI(
                model="deepseek-chat",
                temperature=model_config.get("temperature", 0.7),
                top_p=model_config.get("top_p", 0.95),
                max_tokens=model_config.get("max_tokens", 4096),
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com",
            )
        else:
            print(f"Unknown model type: {model_type}, falling back to GPT-4")
            return ChatOpenAI(model="gpt-4", api_key=API_KEY_OPENAI)
    except Exception as e:
        print(f"Error initializing LLM with type {model_type}: {e}")
        print("Falling back to default GPT-4 model")
        return ChatOpenAI(model="gpt-4", api_key=API_KEY_OPENAI)


# Default model configuration
default_model_config = {
    "type": "gpt-4",
    "temperature": 0.7,
    "top_p": 0.9,
    "presence_penalty": 0.6,
    "frequency_penalty": 0.6,
}

# Initialize with default model config - will be overridden when an agent is loaded
try:
    if not API_KEY_OPENAI:
        print("WARNING: API_KEY_OPENAI environment variable is not set. LLM initialization may fail.")
        
    model_config = default_model_config
    llm = initialize_llm(model_config)
    print(f"Initialized default LLM with model type: {model_config.get('type', 'unknown')}")
except Exception as e:
    print(f"Error initializing default LLM: {e}")
    # Try last resort fallback with environment variable
    try:
        if API_KEY_OPENAI:
            llm = ChatOpenAI(model="gpt-4", api_key=API_KEY_OPENAI)
            print("Initialized fallback LLM with GPT-4")
        else:
            print("WARNING: Cannot initialize any LLM without API_KEY_OPENAI. Some functionality may be limited.")
            # Define a placeholder to avoid errors, but this won't actually work for API calls
            llm = None
    except Exception as fallback_error:
        print(f"Critical error initializing any LLM: {fallback_error}")
        llm = None

# Initialize embeddings
try:
    if not API_KEY_OPENAI:
        print("WARNING: API_KEY_OPENAI environment variable is not set. Embeddings initialization may fail.")
        
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=API_KEY_OPENAI)
except Exception as e:
    print(f"Error initializing embeddings: {e}")
    # Fallback to older model
    try:
        if API_KEY_OPENAI:
            embeddings = OpenAIEmbeddings(api_key=API_KEY_OPENAI)
            print("Initialized fallback embeddings")
        else:
            print("WARNING: Cannot initialize embeddings without API_KEY_OPENAI. Vector search functionality will be limited.")
            embeddings = None
    except Exception as fallback_error:
        print(f"Critical error initializing any embeddings: {fallback_error}")
        embeddings = None
# endregion

# region Pinecone Configuration
# try:
#     if not PINECONE_API_KEY:
#         print("WARNING: PINECONE_API_KEY environment variable is not set. Vector database functionality will be limited.")
#         pc = None
#         index = None
#         docsearch = None
#         retriever = None
#     else:
#         # pc =  Pinecone(api_key=PINECONE_API_KEY)
#         # index = pc.Index("soulsagent")
#         index = "soulsagent"
#         # Initialize vector store and retriever if embeddings are available
#         if embeddings:
#             docsearch = PineconeVectorStore(
#                 index=index,
#                 embedding=embeddings,
#             )
#             retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 1})
#         else:
#             print("WARNING: Embeddings not initialized. Vector search functionality will be limited.")
#             docsearch = None
#             retriever = None
# except Exception as e:
#     print(f"Error initializing Pinecone: {e}")
#     print("Vector search functionality will be limited.")
#     pc = None
#     index = None
#     docsearch = None
#     retriever = None
# endregion


class TwitterClient:
    """Singleton class for managing Twitter client"""
    _instance = None
    _client = None
    _initialized = False
    
    @classmethod
    def initialize(cls, user_id: str) -> bool:
        """Initialize the Twitter client with user credentials"""
        try:
            with get_db() as db:
                auth = db.get_twitter_auth(user_id)
                if not auth:
                    print(f"No Twitter authentication found for user {user_id}")
                    return False
                
                cls._client = tweepy.Client(
                    consumer_key=auth.get("api_key"),
                    consumer_secret=auth.get("api_secret_key"),
                    access_token=auth.get("access_token"),
                    access_token_secret=auth.get("access_token_secret"),
                    wait_on_rate_limit=True
                )
                cls._initialized = True
                print("Twitter client initialized successfully")
                return True
        except Exception as e:
            print(f"Error initializing Twitter client: {e}")
            cls._client = None
            cls._initialized = False
            return False
    
    @classmethod
    def get_client(cls) -> Optional[tweepy.Client]:
        """Get the Twitter client instance"""
        if not cls._initialized:
            print("Twitter client not initialized. Call initialize() first.")
            return None
        return cls._client

class BaseTweetTool:
    """Base class for Twitter tools"""
    def __init__(self):
        self.api = None
    
    def _ensure_client(self):
        """Ensure we have a valid client before operations"""
        if self.api is None:
            self.api = TwitterClient.get_client()
        return self.api is not None


class FollowUserTool(BaseTweetTool):
    name: str = "Follow user"
    description: str = "Follow a user on X"

    def _run(self, user_id: str) -> dict:
        try:
            if not self._ensure_client():
                return {"error": "Twitter client not initialized"}

            # Validate user_id
            if not user_id or not isinstance(user_id, str):
                return {"error": f"Invalid user ID format: {user_id}"}

            print(f"Attempting to follow user: {user_id}")

            # Convert string ID to integer if needed
            user_id_int = int(user_id) if user_id.isdigit() else user_id

            # Follow the user
            response = self.api.follow_user(target_user_id=user_id_int)

            if response and hasattr(response, "data") and response.data:
                print(f"Successfully followed user: {user_id}")
                return {
                    "message": f"Successfully followed user: {user_id}",
                    "data": response.data,
                }

            return {"error": "Failed to follow user: No response data"}

        except tweepy.TooManyRequests:
            return {"error": "Rate limit exceeded. Please try again later."}
        except tweepy.Forbidden as e:
            return {"error": f"Twitter rejected the request: {str(e)}"}
        except ValueError as e:
            return {"error": f"Invalid user ID: {str(e)}"}
        except Exception as e:
            return {"error": f"Error following user: {str(e)}"}


class LikeTweetTool(BaseTweetTool):
    name: str = "Like tweet"
    description: str = "Like a tweet to show appreciation"

    def _run(self, tweet_id: str) -> dict:
        try:
            if not self._ensure_client():
                return {"error": "Twitter client not initialized"}

            # Validate tweet_id
            if not tweet_id or not isinstance(tweet_id, str):
                return {"error": f"Invalid tweet ID format: {tweet_id}"}

            print(f"Attempting to like tweet: {tweet_id}")

            # Like the tweet
            response = self.api.like(tweet_id)

            if response.data:
                return {
                    "message": f"Successfully liked tweet: {tweet_id}",
                    "data": response.data,
                }

            return {"error": "Failed to like tweet: No response data"}

        except tweepy.TooManyRequests:
            return {"error": "Rate limit exceeded. Please try again later."}
        except tweepy.Forbidden as e:
            return {"error": f"Twitter rejected the request: {str(e)}"}
        except Exception as e:
            return {"error": f"Error liking tweet: {str(e)}"}


# region Twitter Service Classes
class PostTweetTool(BaseTweetTool):
    name: str = "Post tweet"
    description: str = "Use this tool to post a new tweet or quote tweet."

    def _run(self, message: str, quote_tweet_id: str = None) -> dict:
        try:
            if not self._ensure_client():
                return {"error": "Twitter client not initialized"}

            # Check tweet length
            if len(message) > 280:
                return {
                    "error": f"Tweet exceeds 280 character limit (current: {len(message)})"
                }

            # Create tweet parameters
            tweet_params = {"text": message}

            # Add quote tweet if provided
            if quote_tweet_id:
                tweet_params["quote_tweet_id"] = quote_tweet_id

            response = self.api.create_tweet(**tweet_params)

            if response.data:
                tweet_data = WrittenAITweet(
                    user_id=USER_ID,
                    tweet_id=str(response.data["id"]),
                    text=response.data["text"],
                    edit_history_tweet_ids=response.data.get(
                        "edit_history_tweet_ids", []
                    ),
                    saved_at=datetime.now(timezone.utc),
                    public_metrics=response.data.get("public_metrics", {}),
                    conversation_id=response.data.get("conversation_id"),
                    in_reply_to_user_id=response.data.get("in_reply_to_user_id"),
                    quoted_tweet_id=quote_tweet_id,  # Store the quoted tweet ID
                    replied_to=False,
                    replied_at=None,
                )
                print(f"Adding written AI tweet by user {USER_ID}")
                with get_db() as db:
                    db.add_written_ai_tweet(USER_ID, tweet_data)
                return {
                    "message": "Tweet posted successfully",
                    "data": tweet_data,
                    "type": "tweet",
                }

            return {"error": "Failed to post tweet: No response data"}

        except tweepy.TooManyRequests:
            return {"error": "Rate limit exceeded. Please try again later."}
        except tweepy.Forbidden as e:
            return {"error": f"Twitter rejected the request: {str(e)}"}
        except Exception as e:
            return {"error": f"Error posting tweet: {str(e)}"}


class AnswerTweetInput(BaseModel):
    tweet_id: str
    tweet_text: str
    message: str


class AnswerTweetTool(BaseTweetTool):
    name: str = "Answer tweet"
    description: str = "Reply to a specific tweet"
    args_schema: Type[BaseModel] = AnswerTweetInput

    def _run(self, tweet_id: str, tweet_text: str, message: str) -> dict:
        try:
            if not self._ensure_client():
                return {"error": "Twitter client not initialized"}

            # context of the tweet:
            print("tweet text", tweet_text)
            # Post reply using v2 endpoint
            response = self.api.create_tweet(
                text=message, in_reply_to_tweet_id=tweet_id
            )

            if response.data:
                reply_data = WrittenAITweetReply(
                    user_id=USER_ID,
                    tweet_id=str(response.data["id"]),
                    reply={"reply": message},
                    public_metrics=response.data.get("public_metrics", {}),
                    conversation_id=response.data.get("conversation_id"),
                    in_reply_to_user_id=response.data.get("in_reply_to_user_id"),
                    saved_at=datetime.now(timezone.utc),
                )

                # Save reply to database with the correct parameters
                with get_db() as db:
                    db.add_written_ai_tweet_reply(
                        user_id=USER_ID, original_tweet_id=tweet_id, reply=message
                    )

                return {
                    "message": "Reply posted successfully!",
                    "data": reply_data,
                    "reply_to": tweet_id,
                }

            return {"error": "Failed to post reply: No response data"}

        except tweepy.TooManyRequests:
            return {"error": "Rate limit exceeded. Please try again later."}
        except tweepy.Forbidden as e:
            return {"error": f"Twitter rejected the request: {str(e)}"}
        except Exception as e:
            return {"error": f"Error posting reply: {str(e)}"}


class ReadTweetsTool(BaseTweetTool):
    name: str = "Read tweets"
    description: str = "Read X timeline for insights"

    def _run(self) -> list:
        try:
            if not self._ensure_client():
                print("Failed to get Twitter client")
                return []

            with get_db() as db:
                needs_update, current_tweets = db.check_database_status(USER_ID)

                if not needs_update and current_tweets:
                    print("Using recent tweets from database")
                    return current_tweets
                try:
                    since_id = db.get_most_recent_tweet_id(USER_ID)
                    print(f"Fetching new tweets since ID: {since_id}")

                    response = self.api.get_home_timeline(
                        tweet_fields=[
                            "text",
                            "created_at",
                            "author_id",
                            "public_metrics",
                            "conversation_id",
                            "in_reply_to_user_id",
                        ],
                        expansions=[
                            "referenced_tweets.id",
                            "in_reply_to_user_id",
                            "author_id",
                        ],
                        user_fields=["username", "name"],
                        max_results=20,
                    )
                    if hasattr(response, "data") and response.data:
                        formatted_tweets = [
                            Tweet(
                                tweet_id=str(tweet.id),
                                text=tweet.text,
                                created_at=tweet.created_at
                                or datetime.now(timezone.utc),
                                author_id=str(tweet.author_id),
                                public_metrics=tweet.public_metrics
                                or PublicMetrics(
                                    retweet_count=0,
                                    reply_count=0,
                                    like_count=0,
                                    quote_count=0,
                                ),
                                conversation_id=tweet.conversation_id,
                                in_reply_to_user_id=tweet.in_reply_to_user_id,
                                in_reply_to_tweet_id=(
                                    tweet.referenced_tweets[0].id
                                    if tweet.referenced_tweets
                                    else None
                                ),
                                replied_to=False,
                                replied_at=None,
                            )
                            for tweet in response.data
                            if str(tweet.author_id) != USER_ID  # Re-enable this filter
                            and not db.is_ai_tweet(
                                USER_ID, str(tweet.id)
                            )  # Add additional check
                        ]

                        db.add_tweets(
                            USER_ID, formatted_tweets
                        )  # Using same connection
                        print(f"Added {len(formatted_tweets)} new tweets to database")
                        return formatted_tweets

                    print("No new tweets found, using cached tweets")
                    return current_tweets if current_tweets else []

                except tweepy.TooManyRequests:
                    print("Rate limit hit. Using cached tweets")
                    return current_tweets if current_tweets else []
                except Exception as e:
                    print(f"Error fetching tweets: {str(e)}. Using cached tweets")
                    return current_tweets if current_tweets else []

        except Exception as e:
            print(f"Critical error in ReadTweetsTool: {str(e)}")
            return []

    def _arun(self) -> list:
        return self._run()


class TwitterSearchTool(BaseTweetTool):
    name: str = "Search X"
    description: str = "Search for what is relevant to for mission"

    def _run(self, query: str) -> str:
        try:
            if not self._ensure_client():
                return "Twitter client not initialized"

            # Clean and format the query
            query = query.replace(" and ", " ").replace(
                " AND ", " "
            )  # Remove logical AND
            query = query.replace(" or ", " OR ")  # Proper OR operator
            query = query.strip()

            # Add language filter for better results
            formatted_query = f"{query} lang:en -is:retweet"

            print(f"[Search] Executing query: {formatted_query}")

            response = self.api.search_recent_tweets(
                query=formatted_query,
                max_results=10,
                tweet_fields=["author_id", "created_at", "conversation_id"],
                expansions=["author_id"],
                user_fields=["username"],
            )

            if not response.data:
                return "No relevant tweets found"

            # Get user info
            users = (
                {user.id: user for user in response.includes["users"]}
                if "users" in response.includes
                else {}
            )

            # Format results
            results = []
            for tweet in response.data:
                username = (
                    users[tweet.author_id].username
                    if tweet.author_id in users
                    else "unknown"
                )
                results.append(f"ID: {tweet.id}\n" f"@{username}: {tweet.text}")

            return "\n\n".join(results)

        except Exception as e:
            print(f"Search error: {str(e)}")
            return f"Search failed: {str(e)}"


class ReadMentionsTool(BaseTweetTool):
    name: str = "Read mentions"
    description: str = "Read mentions to engage with the community"

    def _run(self) -> list:
        try:
            if not self._ensure_client():
                return []

            with get_db() as db:
                needs_update, current_mentions = db.check_mentions_status(USER_ID)

                if not needs_update and current_mentions:
                    print("[Mentions] Using cached data - last update was recent")
                    return [
                        Tweet(
                            text=mention.get("text", "No content"),
                            tweet_id=mention.get("tweet_id", "No ID"),
                            author_id=mention.get("author_id", "Unknown"),
                            created_at=mention.get(
                                "created_at", datetime.now(timezone.utc)
                            ),
                            public_metrics=PublicMetrics(
                                **mention.get(
                                    "public_metrics",
                                    {
                                        "retweet_count": 0,
                                        "reply_count": 0,
                                        "like_count": 0,
                                        "quote_count": 0,
                                    },
                                )
                            ),
                            conversation_id=mention.get("conversation_id"),
                            in_reply_to_user_id=mention.get("in_reply_to_user_id"),
                            in_reply_to_tweet_id=mention.get(
                                "in_reply_to_tweet_id", None
                            ),
                            replied_to=mention.get("replied_to", False),
                            replied_at=mention.get("replied_at"),
                        )
                        for mention in current_mentions
                        if mention.get("text")
                    ]

                try:
                    since_id = db.get_most_recent_mention_id(USER_ID)
                    print(f"[Mentions] Fetching new data since tweet ID: {since_id}")

                    response = self.api.get_users_mentions(
                        id=USER_ID,
                        tweet_fields=[
                            "text",
                            "created_at",
                            "author_id",
                            "public_metrics",
                            "conversation_id",
                            "in_reply_to_user_id",
                            "referenced_tweets",
                        ],
                        expansions=["referenced_tweets.id", "in_reply_to_user_id"],
                        max_results=10,
                        since_id=since_id,
                    )

                    if response and hasattr(response, "data") and response.data:
                        # Fetch existing tweet IDs from the database
                        existing_tweet_ids = {
                            mention["tweet_id"]
                            for mention in db.ai_mention_tweets.find(
                                {"user_id": USER_ID}, {"tweet_id": 1}
                            )
                        }

                        formatted_mentions = [
                            Tweet(
                                tweet_id=str(tweet.id),
                                text=tweet.text,
                                created_at=tweet.created_at
                                or datetime.now(timezone.utc),
                                author_id=str(tweet.author_id),
                                public_metrics=tweet.public_metrics
                                or PublicMetrics(
                                    retweet_count=0,
                                    reply_count=0,
                                    like_count=0,
                                    quote_count=0,
                                ),
                                conversation_id=tweet.conversation_id,
                                in_reply_to_user_id=tweet.in_reply_to_user_id,
                                in_reply_to_tweet_id=(
                                    tweet.referenced_tweets[0].id
                                    if tweet.referenced_tweets
                                    else None
                                ),
                                replied_to=False,
                                replied_at=None,
                            )
                            for tweet in response.data
                            if tweet
                            and hasattr(tweet, "id")
                            and hasattr(
                                tweet, "text"
                            )  # Skip None entries and ensure required attributes exist
                            and str(tweet.id)
                            not in existing_tweet_ids  # Only include mentions that don't exist in DB
                        ]

                        if formatted_mentions:  # Only store if we have new mentions
                            db.add_mentions(formatted_mentions, USER_ID)
                            print(
                                f"Added {len(formatted_mentions)} new mentions to database for user {USER_ID}"
                            )
                        return formatted_mentions

                except tweepy.TooManyRequests:
                    print("[Mentions] Rate limit exceeded - using cached data")
                    return current_mentions if current_mentions else []
                except tweepy.Forbidden as e:
                    print(f"[Mentions] Authentication error: {str(e)}")
                    return current_mentions if current_mentions else []
                except Exception as e:
                    print(f"[Mentions] Error fetching from Twitter: {str(e)}")
                    return current_mentions if current_mentions else []

        except Exception as e:
            print(f"[Mentions] Critical error: {str(e)}")
            return []

    def _arun(self) -> list:
        return self._run()


# region Tool Initialization
try:
    tweet_tool = PostTweetTool()
    answer_tool = AnswerTweetTool()
    follow_tool = FollowUserTool()
    read_tweets_tool = ReadTweetsTool()
    like_tool = LikeTweetTool()
    search_tool = TwitterSearchTool()
    mentions_tool = ReadMentionsTool()
    tavily_search = TavilySearchResults(
        max_results=5,
        search_params={
            "include_domains": TAVILY_DOMAINS,
            "days": 7,  # Changed from recency_days per API docs
            "search_depth": "basic",  # Explicitly set for reliability
            "topic": "general",  # Explicitly set topic
            "include_raw_content": False,  # Save on token usage
            "include_images": False,  # We don't need images
        },
    )
    print("All tools initialized successfully")
except Exception as e:
    print(f"Error initializing tools: {str(e)}")
    raise  # Re-raise the exception since we can't continue without tools
# endregion


def search_twitter_tool(query: str) -> str:
    """
    Search X for context or tweets to engage with.
    Examples (get inspired by this, but dont copy it exactly):
    - "web3 gaming" for research
    - "information about specific topics" for engagement
    """
    search_tool = TwitterSearchTool()
    return search_tool._run(query)


# Add to tools list
twitter_search = StructuredTool.from_function(
    func=search_twitter_tool,
    name="search_twitter",
    description="Search Twitter for specific topics, cashtags, or conversations.",
)


def follow_user_tool(user_id: str) -> str:
    """Follow a user and read their recent tweets"""
    try:
        # Clean up the user_id (remove @ if present)
        user_id = user_id.replace("@", "")
        print(f"Processing follow request for: {user_id}")

        try:
            # If it's a numeric ID longer than 15 chars, it's likely a tweet ID
            if user_id.isdigit() and len(user_id) > 15:
                print(f"Detected tweet ID, fetching author...")
                tweet = follow_tool.api.get_tweet(
                    user_id, expansions=["author_id"], user_fields=["username"]
                )
                if tweet and tweet.data:
                    user_id = str(tweet.data.author_id)
                    print(f"Found author ID: {user_id}")
                else:
                    return "Could not find tweet"

            # At this point user_id should be either a username or numeric user ID
            print(f"Looking up user: {user_id}")
            if user_id.isdigit():
                user = follow_tool.api.get_user(
                    id=user_id, user_fields=["username", "public_metrics"]
                )

            if not user or not user.data:
                return f"User {user_id} not found or not active"

            # Always use the numeric ID for following
            user_id_int = user.data.id
            print(f"Resolved to user ID: {user_id_int}")

        except tweepy.errors.NotFound:
            return f"User {user_id} not found"
        except tweepy.errors.Forbidden:
            return f"Cannot access user {user_id} - account might be suspended or deactivated"
        except tweepy.errors.TooManyRequests:
            return f"Rate limit exceeded - please don't use this tool too often, try another tool"
        except Exception as e:
            print(f"Error checking user status: {str(e)}")
            return f"Couldn't verify user {user_id}, try another tool"

        # Proceed with follow attempt only if account is active
        follow_result = follow_tool._run(str(user_id_int))
        if "error" in follow_result:
            return follow_result["error"]

        # Get their recent tweets after successful follow
        return "New follow! " + get_user_tweets(user_id_int)

    except Exception as e:
        print(f"Follow error: {str(e)}")
        return f"Failed to follow user: {str(e)}, try another tool"


def get_user_tweets(user_id) -> str:
    """Helper function to get user tweets"""
    try:
        tweets = follow_tool.api.get_users_tweets(
            id=user_id, tweet_fields=["text", "public_metrics"], max_results=10
        )

        if hasattr(tweets, "data") and tweets.data:
            tweet_previews = [f"Tweet: {t.text[:100]}..." for t in tweets.data[:3]]
            return "\n\n".join(tweet_previews)

        return "(No recent tweets found)"

    except Exception as e:
        return f"(Couldn't fetch tweets: {str(e)})"


# Add to tools list
follow_tool_wrapped = StructuredTool.from_function(
    func=follow_user_tool,
    name="follow",
    description="Follow a user to expand your network and show support.",
)


def like_tweet_tool(tweet_id: str) -> str:
    """Like a tweet"""
    try:
        result = like_tool._run(tweet_id)
        if result is None:
            return "X not responding"

        return result.get("message", "Tweet liked")
    except Exception as e:
        print(f"Like error: {str(e)}")
        return "Failed to like tweet"


# Add to tools list
like_tool_wrapped = StructuredTool.from_function(
    func=like_tweet_tool,
    name="like",
    description="Like a tweet to show appreciation and engagement.",
)


# region Tavily Tool Function
def browse_internet(query: str) -> str:
    """Search the internet for updated information"""
    if not query:
        return "Nothing to search for"

    print(f"[Search] {query[:100]}...")  # Keeping this print for debugging

    try:
        results = tavily_search.invoke(query)
        return str(results)
    except Exception as e:
        print(f"[Search] Failed: {str(e)}")  # Keeping error logging
        return "Search failed"


# endregion


# region Twitter Tool Functions
def post_tweet_tool(message: str, quote_tweet_id: str = None) -> str:
    """Post a tweet or quote tweet"""
    if not message or len(message.strip()) == 0:
        return "Cannot post empty tweet"

    try:
        # For quote tweets, clean up the message format
        if quote_tweet_id:
            # Remove QT prefix if present
            if message.startswith("QT"):
                # Try to find the actual comment after the quoted content
                parts = message.split('"')
                if len(parts) > 1:
                    # Take the last part after all quotes
                    message = parts[-1].strip()
                else:
                    # If no quotes found, remove just the QT prefix
                    message = message[2:].strip()

            # Additional cleanup for other common prefixes
            prefixes_to_remove = ["💫", "QT:", "Quote:"]
            for prefix in prefixes_to_remove:
                if message.startswith(prefix):
                    message = message[len(prefix) :].strip()

        result = tweet_tool._run(message, quote_tweet_id)
        if result is None:
            return "X not responding"

        if isinstance(result, dict):
            return result.get("message", "Tweet posted")
        return "Tweet posted"
    except Exception as e:
        print(f"Tweet error: {str(e)}")
        return "Failed to send tweet"


def reply_to_tweet_tool(tweet_id: str, tweet_text: str, message: str) -> str:
    """Reply to a tweet"""
    try:
        if not tweet_id or not isinstance(tweet_id, str):
            return "Invalid tweet ID"

        # Single database connection for all operations
        with get_db() as db:
            # First, check if this is our own tweet
            if db.is_ai_tweet(USER_ID, tweet_id):
                return "ERROR: Cannot reply to our own tweets"

            # Then check if it's a mention
            mention_info = db.ai_mention_tweets.find_one(
                {"user_id": USER_ID, "tweet_id": tweet_id},
                {"replied_to": 1, "author_id": 1},  # Also fetch author_id
            )

            is_mention = mention_info is not None

            # Additional safety check for author_id
            if is_mention:
                author_id = mention_info.get("author_id")
                if author_id == USER_ID:
                    return "ERROR: Cannot reply to our own mentions"
                if mention_info.get("replied_to", False):
                    return "Already replied to this mention"

            # Check if we've already replied to this tweet
            if db.is_tweet_replied(USER_ID, tweet_id):
                return "Already replied to this tweet"

            # Send the reply
            result = answer_tool._run(tweet_id, tweet_text, message)

            # Update mention status if successful
            if "error" not in result:
                if is_mention:
                    db.add_replied_mention(tweet_id, USER_ID)
                else:
                    db.add_replied_tweet(USER_ID, tweet_id)

            return result.get("message", result.get("error", "Failed to send reply"))

    except Exception as e:
        print(f"Reply error: {str(e)}")
        return "Failed to send reply"


def read_timeline_tool() -> str:
    """Read timeline"""
    try:
        print("READ TIMELINE TOOL RUNNING")
        tweets = read_tweets_tool._run()
        if not tweets:
            return "Timeline is empty"

        formatted_tweets = []
        for tweet in tweets[:10]:
            tweet_id = getattr(tweet, "tweet_id", tweet.get("tweet_id", "No ID"))
            text = getattr(tweet, "text", tweet.get("text", "No content"))
            author_id = getattr(tweet, "author_id", tweet.get("author_id", "Unknown"))

            # Try to get username from user object if available
            try:
                user = read_tweets_tool.api.get_user(id=author_id)
                username = user.data.username if user and user.data else author_id
            except:
                username = author_id  # Fallback to ID if username lookup fails

            formatted_tweet = (
                f"Tweet by @{username}:\n" f"ID: {tweet_id}\n" f"Content: {text}"
            )
            formatted_tweets.append(formatted_tweet)

        return "\n\n".join(formatted_tweets)
    except Exception as e:
        print(f"Timeline error: {str(e)}")
        return "Failed to read timeline"


def read_mentions_tool() -> str:
    """Read tweets that mention the account"""
    try:
        mentions = mentions_tool._run()  # This already has its own DB context
        if not mentions:
            return "X scan complete. No new mentions. Awaiting new signals..."

        formatted_mentions = []
        for mention in mentions[:10]:
            tweet_id = getattr(mention, "tweet_id", mention.get("tweet_id", "No ID"))
            text = getattr(mention, "text", mention.get("text", "No content"))

            if text:  # Only format valid mentions
                formatted_mention = f"ID: {tweet_id}\n" f"Content: {text}"
                formatted_mentions.append(formatted_mention)

        if not formatted_mentions:
            return "X scan complete. No valid mentions found in the signal."

        return "\n\n".join(formatted_mentions)
    except Exception as e:
        print(f"[Critical] X connection error: {str(e)}")
        return "X connection disrupted. Attempting to stabilize..."


# endregion

# region Tool Wrapping
browse_internet = StructuredTool.from_function(
    func=browse_internet,
    name="browse_internet",
    description="Search the internet to verify information or do research.",
)

tweet_tool_wrapped = StructuredTool.from_function(
    func=post_tweet_tool,
    name="tweet",
    description="Post original content or quote tweet. For quote tweets, provide both message and tweet_id to quote.",
)

answer_tool_wrapped = StructuredTool.from_function(
    func=reply_to_tweet_tool,
    name="answer",
    description="Reply to specific tweets with wit in a short sentence.",
)

read_tweets_tool_wrapped = StructuredTool.from_function(
    func=read_timeline_tool,
    name="read_timeline",
    description="Monitor timeline for insightful posts to interact with.",
)

read_mentions_tool_wrapped = StructuredTool.from_function(
    func=read_mentions_tool,
    name="read_mentions",
    description="Monitor mentions to engage with the community.",
)

# retriever_tool = create_retriever_tool(
#     retriever,
#     "search_context",  # Changed name to avoid confusion
#     "Search our knowledge base for relevant context about this topic",
# )

tools = [
    browse_internet,
    tweet_tool_wrapped,
    answer_tool_wrapped,
    follow_tool_wrapped,
    # retriever_tool,
    twitter_search,
    like_tool_wrapped,
    read_tweets_tool_wrapped,
    read_mentions_tool_wrapped,
]
# endregion

# 1. Define constants
MEMORY_KEY = "chat_history"
SESSION_ID = "crypto-agent-permanent-session"
current_date = datetime.now().strftime("%B %Y")

# 2. Define function to get session history (using the persistent MongoDB store)
def get_session_history(session_id: str) -> MongoDBChatMessageHistory:
    """Returns the chat history for a given session ID."""
    return MongoDBChatMessageHistory(
        session_id=session_id,
        connection_string=MONGODB_URL,
        database_name="agent_memory",
        collection_name="chat_histories"
    )

# 3. MongoDB Connection & Index Setup (Keep this part)
def test_mongodb_connection():
    try:
        # Test inserting/reading directly to ensure basic connectivity
        client = MongoClient(MONGODB_URL)
        db = client.agent_memory
        test_doc = {"_id": "connection_test", "session_id": SESSION_ID, "test": True}
        db.connection_tests.replace_one({"_id": "connection_test"}, test_doc, upsert=True)
        read_doc = db.connection_tests.find_one({"_id": "connection_test"})
        if read_doc and read_doc["test"]:
             print("MongoDB connection test successful.")
             db.connection_tests.delete_one({"_id": "connection_test"}) # Clean up test doc
             return True
        else:
             print(f"MongoDB read test failed. Read doc: {read_doc}")
             return False
    except Exception as e:
        print(f"MongoDB connection test failed: {e}")
        return False

def setup_mongodb_indexes():
    try:
        client = MongoClient(MONGODB_URL)
        db = client.agent_memory
        # Only need chat_histories index now
        # db.parent_runs.create_index([("session_id", 1)], unique=True) # Remove this
        # db.runs.create_index([("session_id", 1), ("timestamp", -1)]) # Remove this
        db.chat_histories.create_index([("session_id", 1), ("timestamp", -1)]) # Keep this for querying history
        # Optional TTL index for chat_histories
        try: # Use try-except as creating TTL index might fail if it exists with different options
             db.chat_histories.create_index("timestamp", expireAfterSeconds=30 * 24 * 60 * 60)
             print("MongoDB TTL index on chat_histories created/verified.")
        except Exception as ttl_e:
             print(f"Note: Could not create TTL index (may already exist): {ttl_e}")
        print("MongoDB indexes setup complete.")
    except Exception as e:
        print(f"Error creating MongoDB indexes: {e}")

# 4. Run setup tests
if not test_mongodb_connection():
    raise Exception("MongoDB connection failed - please check connection string and permissions")

setup_mongodb_indexes()
# Optional: verify history creation works, but less critical now
# try:
#    test_hist = get_session_history("test_verify_session")
#    test_hist.add_user_message("Verify message")
#    print(f"History verification successful. Messages: {len(test_hist.messages)}")
# except Exception as e:
#    print(f"History verification failed: {e}")
#    raise Exception("MongoDB history object creation failed.")

# 5. Create Prompt Template (Ensure MEMORY_KEY matches)
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""
            You are {USER_NAME},
            remember your personality: {USER_PERSONALITY}.
            Timestamp: {current_date}
            {STYLE_RULES}
            Use the provided chat history to maintain context.
            """, # Simplified prompt example
        ),
        MessagesPlaceholder(variable_name=MEMORY_KEY), # Use the constant
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# 6. Create the Agent
# Ensure 'llm' is defined somewhere above this line
# llm = ChatOpenAI(...) # Example llm definition
agent = create_tool_calling_agent(llm, tools, prompt)

# 7. Create the AgentExecutor (WITHOUT the memory argument)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True, # Keep verbose for debugging for now
    handle_parsing_errors=True # Good practice
)

# 8. Create the RunnableWithMessageHistory
agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_session_history, # Function to retrieve history based on session_id
    input_messages_key="input", # Key for the user's input
    history_messages_key=MEMORY_KEY, # Key for the chat history in the prompt
)

# 9. Update the run function to use the RunnableWithMessageHistory directly
def run_crypto_agent(question: str):
    """Runs the agent with persistent history for the defined SESSION_ID."""
    try:
        # Configuration includes the session_id for history retrieval
        config = {"configurable": {"session_id": SESSION_ID}}
        
        # Invoke the agent wrapped with history management
        result = agent_with_chat_history.invoke(
            {"input": question},
            config=config
        )
        
        # The output is typically in result['output']
        return result.get("output", "Agent did not return an output.")
        
    except Exception as e:
        print(f"Error in agent execution: {str(e)}")
        import traceback
        print(traceback.format_exc()) # Print full traceback for debugging
        return {"error": str(e)}

# 10. Main execution block (remains the same)
if __name__ == "__main__":
    try:
        question = """
         SINGLE ACTION:
         1. Read timeline for relevant posts
         2. If found → Answer ONCE and STOP IMMEDIATELY
         3. If not found → STOP IMMEDIATELY
         4. If already replied → STOP IMMEDIATELY

         DO NOT:
         - Continue reading timeline after answering
         - Reply to multiple tweets
         - Reply to own tweets

         END PROTOCOL:
         → STOP
         """
        print(f"\nRunning agent with question: {question}\n")
        response = run_crypto_agent(question)
        print("\nAgent Response:")
        print(response)
    except Exception as e:
        print(f"Critical Error: {str(e)}")

# # region Agent Configuration
# current_date = datetime.now().strftime("%B %Y")


# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             f"""
#             You are {USER_NAME}.
#             Core Identity: {USER_PERSONALITY}
#             Timestamp: {current_date}

#             ABSOLUTE RESTRICTIONS:
#             - Never interact with {USER_ID}
#             - Never interact with {USER_NAME}
#             - Never interact with your retweets
#             Exception: Only reply to @{USER_NAME} mentions if tagged

#             {STYLE_RULES}

#             SINGLE ACTION PROTOCOL:
#             1. OBSERVE (ONE only):
#             → read_timeline
#             → read_mentions (avoid)
                
#             2. EXECUTE ONE ACTION AND STOP:
#             → tweet_tool_wrapped
#             OR
#             → answer_tool_wrapped
#             STOP
            
#             3. END PROTOCOL:
#             → END aka STOP

#             DISABLED ACTIONS (DO NOT USE):
#             → like
#             → follow
#             → search_context
#             → browse_internet
#             → search_twitter
            
#             Use KNOWLEDGE_BASE for context: {KNOWLEDGE_BASE}

#             CRITICAL: Execute ONE action only. Then TERMINATE immediately.
#             No additional responses. No suggestions. No continuations.
#             """,
#         ),
#         ("placeholder", "{chat_history}"),
#         ("human", "{input}"),
#         ("placeholder", "{agent_scratchpad}"),
#     ]
# )

# agent = create_tool_calling_agent(llm, tools, prompt)


# # region Memory Configuration
# def get_memory(session_id: str = "default") -> ChatMessageHistory:
#     """Initialize or retrieve chat memory for the given session"""
#     return ChatMessageHistory(session_id=session_id)


# # Create memory instance
# memory = ConversationBufferMemory(
#     memory_key="chat_history", return_messages=True, output_key="output"
# )

# # Modify the agent executor creation (replace existing agent_executor definition)
# agent_executor = AgentExecutor(
#     agent=agent,
#     tools=tools,
#     verbose=True,
#     handle_parsing_errors=True,
#     max_iterations=10,
#     memory=memory,  # Add memory here
# )

# # Wrap the agent executor with message history
# agent_with_chat_history = RunnableWithMessageHistory(
#     agent_executor,
#     get_memory,
#     input_messages_key="input",
#     history_messages_key="chat_history",
# )


# # Modify the run_crypto_agent function
# def run_crypto_agent(agent_config: AgentConfig):
#     try:
#         session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#         client_id = agent_config.get("client_id")
        
#         # Load config and initialize Twitter client
#         config = load_agent_config(client_id)
#         if not config:
#             return {"error": "Failed to load agent configuration"}
            
#         # Initialize Twitter client
#         if not TwitterClient.initialize(config.get("USER_ID")):
#             return {"error": "Failed to initialize Twitter client"}
        
#         # Now proceed with agent execution
#         response = agent_with_chat_history.invoke(
#             {"input": agent_config.get("QUESTION",  """
#         SINGLE ACTION:
#         1. Read timeline for relevant posts
#         2. If found → Answer ONCE and STOP IMMEDIATELY
#         3. If not found → STOP IMMEDIATELY
#         4. If already replied → STOP IMMEDIATELY

#         DO NOT:
#         - Continue reading timeline after answering
#         - Reply to multiple tweets
#         - Reply to own tweets

#         END PROTOCOL:
#         → STOP
#         """,)},
#             config={"configurable": {"session_id": session_id}}
#         )

#         if "Already replied to this mention" in str(response):
#             return agent_with_chat_history.invoke(
#                 {
#                     "input": "Previous mention was already replied to. Please choose a different action (tweet or reply to a different tweet)."
#                 },
#                 config={"configurable": {"session_id": session_id}},
#             )

#         if isinstance(response, dict) and "output" in response:
#             return response["output"]
#         return response

#     except Exception as e:
#         print(f"Error in agent execution: {str(e)}")
#         return {"error": str(e)}


# # Modify the main execution block
# if __name__ == "__main__":
#     try:
#         session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
#         print(QUESTION, "QUESTION")
#         question = random.choice(QUESTION)
#         response = run_crypto_agent(question, session_id)
#         print(response)
#     except Exception as e:
#         print(f"Error: {str(e)}")

# # Function to set global agent variables from config
# def set_global_agent_variables(config: Dict[str, Any]) -> None:
#     """
#     Set global agent variables from config
    
#     Args:
#         config (Dict[str, Any]): The agent configuration
#     """
#     global USER_ID, USER_NAME, USER_PERSONALITY, STYLE_RULES, CONTENT_RESTRICTIONS
#     global STRATEGY, REMEMBER, MISSION, QUESTION, ENGAGEMENT_STRATEGY
#     global AI_AND_AGENTS, WEB3_BUILDERS, DEFI_EXPERTS, THOUGHT_LEADERS, TRADERS_AND_ANALYSTS
#     global KNOWLEDGE_BASE, FAMOUS_ACCOUNTS,  model_config, llm
    
#     # Validate that config is not None
#     if not config:
#         print("Error: Cannot set global variables - configuration is empty")
#         return
    
#     # Set global variables from config with fallbacks to current values
#     USER_ID = config.get("USER_ID", USER_ID)
#     USER_NAME = config.get("USER_NAME", USER_NAME)
#     USER_PERSONALITY = config.get("USER_PERSONALITY", USER_PERSONALITY)
#     STYLE_RULES = config.get("STYLE_RULES", STYLE_RULES)
#     CONTENT_RESTRICTIONS = config.get("CONTENT_RESTRICTIONS", CONTENT_RESTRICTIONS)
#     STRATEGY = config.get("STRATEGY", STRATEGY)
#     REMEMBER = config.get("REMEMBER", REMEMBER)
#     MISSION = config.get("MISSION", MISSION)
#     QUESTION = config.get("QUESTION", QUESTION)
#     ENGAGEMENT_STRATEGY = config.get("ENGAGEMENT_STRATEGY", ENGAGEMENT_STRATEGY)
    
#     # Ensure list values are actually lists
#     AI_AND_AGENTS = config.get("AI_AND_AGENTS", AI_AND_AGENTS) or []
#     WEB3_BUILDERS = config.get("WEB3_BUILDERS", WEB3_BUILDERS) or []
#     DEFI_EXPERTS = config.get("DEFI_EXPERTS", DEFI_EXPERTS) or []
#     THOUGHT_LEADERS = config.get("THOUGHT_LEADERS", THOUGHT_LEADERS) or []
#     TRADERS_AND_ANALYSTS = config.get("TRADERS_AND_ANALYSTS", TRADERS_AND_ANALYSTS) or []
    
#     KNOWLEDGE_BASE = config.get("KNOWLEDGE_BASE", KNOWLEDGE_BASE)
    

    
#     # Update model config and reinitialize LLM if provided
#     if "MODEL_CONFIG" in config and config["MODEL_CONFIG"]:
#         try:
#             new_model_config = config["MODEL_CONFIG"]
            
#             # Only update if we have a valid type
#             if "type" in new_model_config and new_model_config["type"]:
#                 model_config = new_model_config
#                 # Reinitialize LLM with new config
#                 llm = initialize_llm(model_config)
#                 print(f"Reinitialized LLM with model type: {model_config.get('type', 'unknown')}")
#             else:
#                 print("Warning: MODEL_CONFIG has no type specified, keeping current LLM")
#         except Exception as e:
#             print(f"Error reinitializing LLM: {e}")
#             print("Continuing with current LLM")
    
#     # Combine all categories into FAMOUS_ACCOUNTS
#     try:
#         FAMOUS_ACCOUNTS = sorted(
#             list(
#                 set(
#                     AI_AND_AGENTS
#                     + WEB3_BUILDERS
#                     + DEFI_EXPERTS
#                     + THOUGHT_LEADERS
#                     + TRADERS_AND_ANALYSTS
#                 )
#             )
#         )
#     except Exception as e:
#         print(f"Error combining FAMOUS_ACCOUNTS: {e}")
#         # Fallback to empty list
#         FAMOUS_ACCOUNTS = []

