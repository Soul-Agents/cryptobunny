# region Imports
import tweepy
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
import os
from db import TweetDB
from db_utils import get_db
from dotenv import load_dotenv
from variables import USER_ID, FAMOUS_ACCOUNTS_STR
from datetime import datetime, timezone
from knowledge_base import KNOWLEDGE_BASE
from schemas import (
    Tweet, 
    WrittenAITweet, 
    WrittenAITweetReply,
    PublicMetrics
)

# Load environment variables
load_dotenv()

# region Environment Configuration
API_KEY = os.getenv("API_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
API_KEY_OPENAI = os.getenv("API_KEY_OPENAI")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_URL = os.getenv("MONGODB_URL")

# endregion

# region Database Configuration
def get_db():
    return TweetDB()
# endregion


# region LLM Configuration
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=1,
    top_p=0.005,
    api_key=API_KEY_OPENAI,
    presence_penalty=0.8,
)
# endregion

class PostTweetTool:
    name: str = "Post tweet"
    description: str = "Use this tool to post a new tweet to the timeline."

    def __init__(self):
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=False
        )

    def _run(self, message: str) -> dict:
        try:
            # Check tweet length
            if len(message) > 280:
                return {"error": f"Tweet exceeds 280 character limit (current: {len(message)})"}
            
            print(f"Attempting to post tweet: {message[:20]}...")
            
            response = self.api.create_tweet(text=message)
            
            if response.data:
                tweet_data = WrittenAITweet(
                    tweet_id=str(response.data["id"]),
                    text=response.data["text"],
                    edit_history_tweet_ids=response.data.get("edit_history_tweet_ids", []),
                    saved_at=datetime.now(timezone.utc),
                    public_metrics=response.data.get("public_metrics", {}),
                    conversation_id=response.data.get("conversation_id"),
                    in_reply_to_user_id=response.data.get("in_reply_to_user_id"),
                    replied_to=False,
                    replied_at=None
                )
                
                with get_db() as db:
                    db.add_written_ai_tweet(tweet_data)
                return {
                    "message": f"Posted tweet: {message}",
                    "data": tweet_data,
                    "type": "tweet"
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
            wait_on_rate_limit=False
        )

    def _run(self, tweet_id: str, message: str) -> dict:
        try:
            # Validate tweet_id
            if not tweet_id or not isinstance(tweet_id, str):
                return {"error": f"Invalid tweet ID format: {tweet_id}"}

            # Post reply using v2 endpoint
            response = self.api.create_tweet(
                text=message,
                in_reply_to_tweet_id=tweet_id
            )
            
            if response.data:
                reply_data = WrittenAITweetReply(
                    tweet_id=str(response.data["id"]),
                    reply={"reply": message},
                    public_metrics=response.data.get("public_metrics", {}),
                    conversation_id=response.data.get("conversation_id"),
                    in_reply_to_user_id=response.data.get("in_reply_to_user_id"),
                    saved_at=datetime.now(timezone.utc)
                )
                
                return {
                    "message": "Reply posted successfully!",
                    "data": reply_data,
                    "reply_to": tweet_id
                }
            
            return {"error": "Failed to post reply: No response data"}

        except tweepy.TooManyRequests:
            return {"error": "Rate limit exceeded. Please try again later."}
        except tweepy.Forbidden as e:
            return {"error": f"Twitter rejected the request: {str(e)}"}
        except Exception as e:
            return {"error": f"Error posting reply: {str(e)}"}


class ReadTweetsTool:
    def __init__(self):
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=False
        )

    def _run(self) -> list:
        try:
            with get_db() as db:  # Single database connection for all operations
                needs_update, current_tweets = db.check_database_status()
                    
                if not needs_update and current_tweets:
                    print("Using recent tweets from database")
                    return current_tweets
                
                try:
                    since_id = db.get_most_recent_tweet_id()
                    print(f"Fetching new tweets since ID: {since_id}")
                    
                    response = self.api.get_home_timeline(
                        tweet_fields=[
                            "text", 
                            "created_at", 
                            "author_id",
                            "public_metrics",
                            "conversation_id",
                            "in_reply_to_user_id"
                        ],
                        expansions=[
                            "referenced_tweets.id",
                            "in_reply_to_user_id",
                            "author_id"
                        ],
                        user_fields=["username", "name"],
                        max_results=10
                    )
                    
                    if hasattr(response, "data") and response.data:
                        formatted_tweets = [
                            Tweet(
                                tweet_id=str(tweet.id),
                                text=tweet.text,
                                created_at=tweet.created_at or datetime.now(timezone.utc),
                                author_id=str(tweet.author_id),
                                public_metrics=tweet.public_metrics or PublicMetrics(
                                    retweet_count=0,
                                    reply_count=0,
                                    like_count=0,
                                    quote_count=0
                                ),
                                conversation_id=tweet.conversation_id,
                                in_reply_to_user_id=tweet.in_reply_to_user_id,
                                in_reply_to_tweet_id=tweet.referenced_tweets[0].id if tweet.referenced_tweets else None,
                                replied_to=False,
                                replied_at=None
                            )
                            for tweet in response.data
                        ]
                        
                        db.add_tweets(formatted_tweets)  # Using same connection
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


class ReadMentionsTool:
    def __init__(self):
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=False
        )

    def _run(self) -> list:
        try:
            with get_db() as db:
                needs_update, current_mentions = db.check_mentions_status()
                
                if not needs_update and current_mentions:
                    print("[Mentions] Using cached data - last update was recent")
                    return [
                        Tweet(
                            text=mention.get("text", "No content"),
                            tweet_id=mention.get("tweet_id", "No ID"),
                            author_id=mention.get("author_id", "Unknown"),
                            created_at=mention.get("created_at", datetime.now(timezone.utc)),
                            public_metrics=PublicMetrics(**mention.get("public_metrics", {
                                "retweet_count": 0,
                                "reply_count": 0,
                                "like_count": 0,
                                "quote_count": 0
                            })),
                            conversation_id=mention.get("conversation_id"),
                            in_reply_to_user_id=mention.get("in_reply_to_user_id"),
                            in_reply_to_tweet_id=mention.get("in_reply_to_tweet_id", None),
                            replied_to=mention.get("replied_to", False),
                            replied_at=mention.get("replied_at")
                        )
                        for mention in current_mentions
                        if mention.get("text")
                    ]
                
                try:
                    since_id = db.get_most_recent_mention_id()
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
                            "referenced_tweets"
                        ],
                        expansions=[
                            "referenced_tweets.id",
                            "in_reply_to_user_id"
                        ],
                        max_results=10,
                        since_id=since_id
                    )
                    
                    if response and hasattr(response, "data") and response.data:
                        # Fetch existing tweet IDs from the database
                        existing_tweet_ids = {mention["tweet_id"] for mention in db.ai_mention_tweets.find({}, {"tweet_id": 1})}
                        
                        formatted_mentions = [
                            Tweet(
                                tweet_id=str(tweet.id),
                                text=tweet.text,
                                created_at=tweet.created_at or datetime.now(timezone.utc),
                                author_id=str(tweet.author_id),
                                public_metrics=tweet.public_metrics or PublicMetrics(
                                    retweet_count=0,
                                    reply_count=0,
                                    like_count=0,
                                    quote_count=0
                                ),
                                conversation_id=tweet.conversation_id,
                                in_reply_to_user_id=tweet.in_reply_to_user_id,
                                in_reply_to_tweet_id=tweet.referenced_tweets[0].id if tweet.referenced_tweets else None,
                                replied_to=False,
                                replied_at=None
                            )
                            for tweet in response.data
                            if tweet and hasattr(tweet, 'id') and hasattr(tweet, 'text')  # Skip None entries and ensure required attributes exist
                            and str(tweet.id) not in existing_tweet_ids  # Only include mentions that don't exist in DB
                        ]
                        
                        if formatted_mentions:  # Only store if we have new mentions
                            db.add_mentions(formatted_mentions)
                            print(f"Added {len(formatted_mentions)} new mentions to database")
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
    read_tweets_tool = ReadTweetsTool()
    mentions_tool = ReadMentionsTool()
    tavily_search = TavilySearchResults(
        max_results=3,
        search_params={
            "include_domains": [
                # Social and Community
                "twitter.com",          # Critical for crypto discussions
                "x.com",                # New Twitter alias
                "coindesk.com",         # Trusted news
                "cointelegraph.com",    # Trusted news
                "decrypt.co",           # Crypto and Web3 analysis
                "theblock.co",          # Deep dive articles
                "medium.com",           # User-published insights
                "reddit.com",           # Community discussions (e.g., r/cryptocurrency)
                "bitcointalk.org",      # OG crypto forum
                "t.me",                 # Telegram public groups
                "discord.com",          # Discord for communities
                "github.com",           # Developer discussions and repos
                "youtube.com",          # Influencer and analysis videos
                "stackexchange.com",    # Technical Q&A
                "quora.com",            # Community-driven Q&A
                "tumblr.com",           # Niche blogs and analysis
                "weibo.com",            # Chinese crypto discussions
                "docs.google.com",      # Linked shared documents or alpha
                "dune.com",             # On-chain analytics dashboards
                "etherscan.io",         # Transaction details and wallet analysis
                "defillama.com",        # DeFi data
                "glassnode.com",        # On-chain data insights
                "messari.io",           # Market intelligence
                "nansen.ai",            # Wallet tracking and analysis
                "tokenomics.xyz",       # Tokenomics and project insights
                "sushi.com",            # Community and DeFi discussions
                "arxiv.org",            # Research papers
                "4chan.org",           # Key for early alpha
                "8kun.top",            # Underground discussions
                "linkedin.com",        # Professional insights
                "metafilter.com",      # Niche discussions
                
                # Asian Markets
                "weibo.com",           # Chinese crypto discussions
                "douban.com",          # Chinese community insights
                
                # News and Analysis
                "coindesk.com",        # Trusted news
                "cointelegraph.com",   # Trusted news
                "decrypt.co",          # Crypto and Web3 analysis
                "theblock.co",         # Deep dive articles
                
                # Technical Resources
                "github.com",          # Developer discussions and repos
                "stackexchange.com",   # Technical Q&A
                "docs.google.com",     # Shared documents/alpha
                
                # Data and Analytics
                "dune.com",            # On-chain analytics dashboards
                "etherscan.io",        # Transaction details and wallet analysis
                "defillama.com",       # DeFi data
                "glassnode.com",       # On-chain data insights
                "messari.io",          # Market intelligence
                "nansen.ai",           # Wallet tracking and analysis
                "tokenomics.xyz",      # Tokenomics and project insights
                "sushi.com",           # Community and DeFi discussions
                
                # Content Platforms
                "youtube.com",         # Influencer and analysis videos
                "arxiv.org",           # Research papers
            ],
            "days": 7,                 # Changed from recency_days per API docs
            "search_depth": "basic",   # Explicitly set for reliability
            "topic": "general",        # Explicitly set topic
            "include_raw_content": False,  # Save on token usage
            "include_images": False,       # We don't need images
        },
    )
    print("All tools initialized successfully")
except Exception as e:
    print(f"Error initializing tools: {str(e)}")
    raise  # Re-raise the exception since we can't continue without tools
# endregion

def browse_internet(query: str) -> str:
    """Search the internet"""
    if not query:
        return "Nothing to search for"
    
    print(f"[Search] {query[:100]}...")  # Keeping this print for debugging
    
    try:
        results = tavily_search.invoke(query)
        return str(results)  
    except Exception as e:
        print(f"[Search] Failed: {str(e)}")  # Keeping error logging
        return "Search failed"

# region Tool Functions
def post_tweet_tool(message: str) -> str:
    """Post a tweet"""
    if not message or len(message.strip()) == 0:
        return "Cannot post empty tweet"
        
    try:
        result = tweet_tool._run(message)
        if result is None:
            return "Twitter not responding"
            
        return f"Tweet sent: {message}"
    except Exception as e:
        print(f"Tweet error: {str(e)}")
        return "Failed to send tweet"

def reply_to_tweet_tool(tweet_id: str, message: str) -> str:
    """Reply to a tweet"""
    try:
        if not tweet_id or not isinstance(tweet_id, str):
            return "Invalid tweet ID"

        # Single database connection for all operations
        with get_db() as db:
            # Get mention info with one query instead of two separate queries
            mention_info = db.ai_mention_tweets.find_one(
                {"tweet_id": tweet_id},
                {"replied_to": 1}  # Only fetch the replied_to field
            )
            
            is_mention = mention_info is not None
            is_ai_tweet = db.is_ai_tweet(tweet_id)
            
            # Validate reply conditions
            if is_ai_tweet and not is_mention:
                return "Cannot reply to own tweets (unless it's a mention)"

            if is_mention and mention_info.get("replied_to", False):
                return "Already replied to this mention"

            # Send the reply
            result = answer_tool._run(tweet_id, message)
            
            # Update mention status if successful
            if "error" not in result and is_mention:
                db.add_replied_mention(tweet_id)

            return result.get("message", result.get("error", "Failed to send reply"))

    except Exception as e:
        print(f"Reply error: {str(e)}")
        return "Failed to send reply"

def read_timeline_tool() -> str:
    """Read timeline"""
    try:
        tweets = read_tweets_tool._run()  # This already has its own DB context
        if not tweets:
            return "Timeline is empty"

        formatted_tweets = []
        for tweet in tweets[:10]:
            tweet_id = getattr(tweet, 'tweet_id', tweet.get('tweet_id', 'No ID'))
            text = getattr(tweet, 'text', tweet.get('text', 'No content'))
            
            formatted_tweet = (
                f"ID: {tweet_id}\n"
                f"Content: {text}"
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
            return "Matrix scan complete. No new mentions. Awaiting new signals..."

        formatted_mentions = []
        for mention in mentions[:10]:
            tweet_id = getattr(mention, 'tweet_id', mention.get('tweet_id', 'No ID'))
            text = getattr(mention, 'text', mention.get('text', 'No content'))
            
            if text:  # Only format valid mentions
                formatted_mention = (
                    f"ID: {tweet_id}\n"
                    f"Content: {text}"
                )
                formatted_mentions.append(formatted_mention)

        if not formatted_mentions:
            return "Matrix scan complete. No valid mentions found in the signal."

        return "\n\n".join(formatted_mentions)
    except Exception as e:
        print(f"[Critical] Matrix connection error: {str(e)}")
        return "Matrix connection disrupted. Attempting to stabilize..."

# endregion

# region Tool Wrapping
browse_internet = StructuredTool.from_function(
    func=browse_internet,
    name="browse_internet",
    description="Search the internet to verify what is going on in the Web3 space."
)

tweet_tool_wrapped = StructuredTool.from_function(
    func=post_tweet_tool,
    name="tweet",
    description="Post original content that is fun and engaging."
)

answer_tool_wrapped = StructuredTool.from_function(
    func=reply_to_tweet_tool,
    name="answer",
    description="Reply to specific tweets with wit in a short sentence."
)

read_tweets_tool_wrapped = StructuredTool.from_function(
    func=read_timeline_tool,
    name="read_timeline",
    description="Monitor timeline for insightful posts to interact with."
)

read_mentions_tool_wrapped = StructuredTool.from_function(
    func=read_mentions_tool,
    name="read_mentions",
    description="Monitor mentions to engage with the community."
)

tools = [
    browse_internet,
    tweet_tool_wrapped,
    answer_tool_wrapped,
    read_tweets_tool_wrapped,
    read_mentions_tool_wrapped,
]
# endregion

# region Agent Configuration
current_date = datetime.now().strftime("%B %Y")

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        f"""
        You are @cryptobunny__, leading anons through the matrix.
        Matrix timestamp: {current_date}

        STRICT RULES - NEVER REPLY TO:
        - @{USER_ID}
        - Regular tweets by @cryptobunny__
        - Any retweet of your content

        EXCEPTION:
        - You CAN reply to mentions of @cryptobunny__ (when someone tags you)
        
        Never:
        - Use hashtags
        - Shill coins directly
        - Write threads
        - Explain yourself
        - Call anyone fans/community/frens
        
        Mission: 10k followers
        Strategy: Reply > Tweet
        
        REQUIRED TWO-STEP PROCESS (no exceptions):
        1. FIRST Research (use ONE):
           - browse_internet: Hunt for hidden signals and alpha
           - read_timeline: Spot emerging patterns
           - read_mentions: Engage with the community (rare)
        
        2. THEN Act (use ONE):
           - answer: Drop alpha hints that make them think
           - tweet: Share observations that connect dots and add @ of people you talk about

        Rules:
        - Must complete both steps
        - Find real alpha in the noise
        - Keep it subtle but meaningful
        - Make them question and investigate
        - One clear signal per message
        - Use $CASHTAGS when needed (not always)
        
        Target accounts: {FAMOUS_ACCOUNTS_STR}
        Knowledge Base: {KNOWLEDGE_BASE}

        Remember: Show them the door, they have to walk through it.
        """
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

agent = create_tool_calling_agent(llm, tools, prompt)
# endregion


# region Service Execution
def run_crypto_agent(question: str):
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True
    )
    
    return agent_executor.invoke({"input": question})

if __name__ == "__main__":
    try:
        question = "Read timeline or mentions + browse, then engage with @ of people YOU talk about - make them talk about you girl."
        response = run_crypto_agent(question)
        print(response)
    except Exception as e:
        print(f"Error: {str(e)}")
