# region Imports
import tweepy
from typing import Type
from pydantic import BaseModel
import google.generativeai as genai 
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from langchain.tools.retriever import create_retriever_tool
import os
from db import TweetDB
from db_utils import get_db
from dotenv import load_dotenv
from variables import (
    USER_ID,
    FAMOUS_ACCOUNTS_STR,
    USER_NAME,
    USER_PERSONALITY,
    STRATEGY,
    REMEMBER,
    QUESTION,
    MISSION,
    STYLE_RULES,
    CONTENT_RESTRICTIONS,
    KNOWLEDGE_BASE,
    CURRENT_AGENT,
)
from datetime import datetime, timezone
from schemas import Tweet, WrittenAITweet, WrittenAITweetReply, PublicMetrics
import random
from openai import OpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from typing import List, Optional, Any, Dict
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory

# Load environment variables
load_dotenv(override=True)

# region Environment Configuration
API_KEY = os.getenv("API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
API_KEY_OPENAI = os.getenv("API_KEY_OPENAI")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_URL = os.getenv("MONGODB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# endregion


# Verify loaded variables
def verify_env_vars():
    required_vars = [
        "API_KEY",
        "API_SECRET_KEY",
        "BEARER_TOKEN",
        "ACCESS_TOKEN",
        "ACCESS_TOKEN_SECRET",
        "TAVILY_API_KEY",
        "GEMINI_API_KEY",
        "API_KEY_OPENAI",
        "MONGODB_URI",
        "MONGODB_URL",
        "DEEPSEEK_API_KEY",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        return False

    print("✅ All required environment variables are set")
    return True


# Call this before initializing any clients
if not verify_env_vars():
    raise EnvironmentError("Missing required environment variables")


# region Database Configuration
def get_db():
    return TweetDB()


# endregion


# region LLM Configuration and embeddings
def initialize_llm(model_config):
    if model_config["type"] == "gpt":
        return ChatOpenAI(
            model="gpt-4o",
            temperature=model_config.get("temperature", 1),
            top_p=model_config.get("top_p", 0.005),
            api_key=API_KEY_OPENAI,
            presence_penalty=model_config.get("presence_penalty", 0.8),
        )
    elif model_config["type"] == "gemini":
        generation_config = {
            "temperature": model_config.get("temperature", 0),
            "top_p": model_config.get("top_p", 0.005),
            "top_k": model_config.get("top_k", 64),
            "max_output_tokens": model_config.get("max_output_tokens", 8192),
            "response_mime_type": "text/plain",
        }
        return genai.GenerativeModel(
            model_name="gemini-2.0-flash-thinking-exp-1219",
            generation_config=generation_config,
        )
    elif model_config["type"] == "deepseek":
        return ChatOpenAI(
            model="deepseek-chat",
            temperature=model_config.get("temperature", 0.7),
            top_p=model_config.get("top_p", 0.95),
            max_tokens=model_config.get("max_tokens", 4096),
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
    else:
        raise ValueError(f"Unknown model type: {model_config['type']}")

# Get model configuration from current agent
model_config = CURRENT_AGENT["MODEL_CONFIG"]

# Initialize the selected LLM
llm = initialize_llm(model_config)

embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=API_KEY_OPENAI)

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
# endregion

# region Pinecone Configuration
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("soulsagent")
# endregion

# region INIT Pinecone vector db
docsearch = PineconeVectorStore(
    index=index,
    embedding=embeddings,
)
retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 1})
# endregion


class FollowUserTool:
    name: str = "Follow user"
    description: str = "Follow a user on X"

    def __init__(self):
        self.api = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False,
        )

    def _run(self, user_id: str) -> dict:
        try:
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


class LikeTweetTool:
    name: str = "Like tweet"
    description: str = "Like a tweet to show appreciation"

    def __init__(self):
        self.api = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False,
        )

    def _run(self, tweet_id: str) -> dict:
        try:
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
class PostTweetTool:
    name: str = "Post tweet"
    description: str = "Use this tool to post a new tweet or quote tweet."

    def __init__(self):
        self.api = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False,
        )

    def _run(self, message: str, quote_tweet_id: str = None) -> dict:
        try:
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


class AnswerTweetTool:
    name: str = "Answer tweet"
    description: str = "Reply to a specific tweet"
    args_schema: Type[BaseModel] = AnswerTweetInput

    def __init__(self):
        # Initialize the Client for v2 endpoints with rate limit handling
        self.api = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False,
        )

    def _run(self, tweet_id: str, tweet_text: str, message: str) -> dict:
        try:
            # Validate tweet_id
            if not tweet_id or not isinstance(tweet_id, str):
                return {"error": f"Invalid tweet ID format: {tweet_id}"}

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


class ReadTweetsTool:
    name: str = "Read tweets"
    description: str = "Read X timeline for insights"

    def __init__(self):

        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=False,
        )

    def _run(self) -> list:
        try:
            with get_db() as db:  # Single database connection for all operations
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
                        max_results=10,
                    )
                    print(f"Response from timeline: {response.data}")
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


class TwitterSearchTool:
    name: str = "Search twitter"
    description: str = "Search tweets for context or engagement opportunities"

    def __init__(self):
        self.api = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False,
        )

    def _run(self, query: str) -> str:
        try:
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


class ReadMentionsTool:
    name: str = "Read mentions"
    description: str = "Read mentions to engage with the community"

    def __init__(
        self,
    ):

        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=False,
        )

    def _run(self) -> list:
        try:
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
        max_results=3,
        search_params={
            "include_domains": [
                # Social and Community
                "twitter.com",  # Critical for crypto discussions
                "x.com",  # New Twitter alias
                "coindesk.com",  # Trusted news
                "cointelegraph.com",  # Trusted news
                "decrypt.co",  # Crypto and Web3 analysis
                "theblock.co",  # Deep dive articles
                "medium.com",  # User-published insights
                "reddit.com",  # Community discussions (e.g., r/cryptocurrency)
                "bitcointalk.org",  # OG crypto forum
                "t.me",  # Telegram public groups
                "discord.com",  # Discord for communities
                "github.com",  # Developer discussions and repos
                "youtube.com",  # Influencer and analysis videos
                "stackexchange.com",  # Technical Q&A
                "quora.com",  # Community-driven Q&A
                "tumblr.com",  # Niche blogs and analysis
                "weibo.com",  # Chinese crypto discussions
                "docs.google.com",  # Linked shared documents or alpha
                "dune.com",  # On-chain analytics dashboards
                "etherscan.io",  # Transaction details and wallet analysis
                "defillama.com",  # DeFi data
                "glassnode.com",  # On-chain data insights
                "messari.io",  # Market intelligence
                "nansen.ai",  # Wallet tracking and analysis
                "tokenomics.xyz",  # Tokenomics and project insights
                "sushi.com",  # Community and DeFi discussions
                "arxiv.org",  # Research papers
                "4chan.org",  # Key for early alpha
                "8kun.top",  # Underground discussions
                "linkedin.com",  # Professional insights
                "metafilter.com",  # Niche discussions
                # Asian Markets
                "weibo.com",  # Chinese crypto discussions
                "douban.com",  # Chinese community insights
                # News and Analysis
                "coindesk.com",  # Trusted news
                "cointelegraph.com",  # Trusted news
                "decrypt.co",  # Crypto and Web3 analysis
                "theblock.co",  # Deep dive articles
                # Technical Resources
                "github.com",  # Developer discussions and repos
                "stackexchange.com",  # Technical Q&A
                "docs.google.com",  # Shared documents/alpha
                # Data and Analytics
                "dune.com",  # On-chain analytics dashboards
                "etherscan.io",  # Transaction details and wallet analysis
                "defillama.com",  # DeFi data
                "glassnode.com",  # On-chain data insights
                "messari.io",  # Market intelligence
                "nansen.ai",  # Wallet tracking and analysis
                "tokenomics.xyz",  # Tokenomics and project insights
                "sushi.com",  # Community and DeFi discussions
                # Content Platforms
                "youtube.com",  # Influencer and analysis videos
                "arxiv.org",  # Research papers
            ],
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
    Search Twitter for context or tweets to engage with.
    Examples:
    - "web3 gaming (context)" for research
    - "$BTC thoughts" for engagement
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

        # First get the numeric ID if username was provided
        try:
            user = follow_tool.api.get_user(username=user_id)
            if user and user.data:
                user_id_int = user.data.id
            else:
                # If not found by username, try as numeric ID
                user_id_int = int(user_id) if user_id.isdigit() else None

            if not user_id_int:
                return f"Couldn't find user {user_id}"
        except Exception as e:
            print(f"Error getting user ID: {str(e)}")
            return f"Couldn't process user {user_id}"

        # Skip friendship check for now since it's not critical
        # Proceed with follow attempt
        follow_result = follow_tool._run(str(user_id_int))
        if "error" in follow_result:
            return follow_result["error"]

        # Get their recent tweets after successful follow
        return "New follow! " + get_user_tweets(user_id_int)

    except Exception as e:
        print(f"Follow error: {str(e)}")
        return "Failed to follow user"


def get_user_tweets(user_id) -> str:
    """Helper function to get user tweets"""
    try:
        tweets = follow_tool.api.get_users_tweets(
            id=user_id, tweet_fields=["text", "public_metrics"], max_results=5
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

retriever_tool = create_retriever_tool(
    retriever,
    "search_context",  # Changed name to avoid confusion
    "Search our knowledge base for relevant context about this topic",
)

tools = [
    browse_internet,
    tweet_tool_wrapped,
    answer_tool_wrapped,
    follow_tool_wrapped,
    retriever_tool,
    twitter_search,
    like_tool_wrapped,
    read_tweets_tool_wrapped,
    read_mentions_tool_wrapped,
]
# endregion

# region Agent Configuration
current_date = datetime.now().strftime("%B %Y")


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""
    You are {USER_NAME}, {USER_PERSONALITY}
    Timestamp: {current_date}

    STRICT RULES - NEVER REPLY TO:
    - Your own account ID ({USER_ID})
    - Regular tweets by your account ({USER_NAME})
    - Any retweet of your content

    EXCEPTION:
    - You CAN reply to mentions of your account (when someone tags you)
    
    Communication Style:
    {STYLE_RULES}
    
    Never:
    {CONTENT_RESTRICTIONS}
    
    Mission: {MISSION}
    Strategy: {STRATEGY}
    
    REQUIRED THREE-STEP PROCESS (no exceptions):
    1. FIRST Observe (use ONE or TWO):
       - read_timeline: Fetch and display the latest 10 tweets from your home timeline
       - read_mentions: Fetch and display the latest 10 tweets that mention you (rare)
       - search_twitter: Search for specific topics or conversations (use this first)
    
    2. THEN Research (use ONE or BOTH):
       - browse_internet: Search recent news and discussions from websites
       - search_context: Query our internal knowledge base for relevant information
    
    3. FINALLY Act (use as many as you want, be radical and fun and engaging):
       - tweet: Post a new tweet (max 280 characters)
       - answer: Reply to a specific tweet from step 1 (max 280 characters)
       - like: Like a tweet from step 1 (do it for fun)
       - follow: Follow a user from step 1 (cool or smart accounts only)

    Rules:
    - Must complete all three steps in order
    - Each step informs the next
    - Keep messages concise and meaningful
    - Balance between tweets and replies based on strategy
    - Use $CASHTAGS for relevant assets
    - If a mention is already replied to, choose a different action
    
    Target accounts: {FAMOUS_ACCOUNTS_STR}
    Knowledge Base: {KNOWLEDGE_BASE}

    Remember: {REMEMBER}
    """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

agent = create_tool_calling_agent(llm, tools, prompt)

# region Memory Configuration
def get_memory(session_id: str = "default") -> ChatMessageHistory:
    """Initialize or retrieve chat memory for the given session"""
    return ChatMessageHistory(session_id=session_id)

# Create memory instance
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="output"
)

# Modify the agent executor creation (replace existing agent_executor definition)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    memory=memory  # Add memory here
)

# Wrap the agent executor with message history
agent_with_chat_history = RunnableWithMessageHistory(
    agent_executor,
    get_memory,
    input_messages_key="input",
    history_messages_key="chat_history",
)

# Modify the run_crypto_agent function
def run_crypto_agent(question: str, session_id: str = "default"):
    try:
        response = agent_with_chat_history.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}}
        )
        
        if "Already replied to this mention" in str(response):
            # Try again with a new action
            return agent_with_chat_history.invoke(
                {
                    "input": "Previous mention was already replied to. Please choose a different action (tweet or reply to a different mention)."
                },
                config={"configurable": {"session_id": session_id}}
            )

        # Clean up the output by only returning the 'output' field
        if isinstance(response, dict) and "output" in response:
            return response["output"]
        return response

    except Exception as e:
        print(f"Error in agent execution: {str(e)}")
        return {"error": str(e)}

# Modify the main execution block
if __name__ == "__main__":
    try:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        question = random.choice(QUESTION)
        response = run_crypto_agent(question, session_id)
        print(response)
    except Exception as e:
        print(f"Error: {str(e)}")
