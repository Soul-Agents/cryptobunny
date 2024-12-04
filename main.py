# region Imports
import tweepy
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import StructuredTool, tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
import os
from time import sleep
from db import TweetDB
from db_utils import get_db
from dotenv import load_dotenv
from variables import USER_ID, FAMOUS_ACCOUNTS_STR
from datetime import datetime
from knowledge_base import KNOWLEDGE_BASE


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
db = TweetDB()
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


# # region Twitter Service Classes
# class RateLimiter:
#     def __init__(self, min_interval: int = 30, tool_name: str = ""):
#         if min_interval < 0:
#             raise ValueError(f"Invalid min_interval: {min_interval}. Must be >= 0")
            
#         self.last_action_time = 0
#         self.min_interval = min_interval
#         self.tool_name = tool_name or self.__class__.__name__
#         print(f"[{self.tool_name}] Rate limiter initialized with {min_interval}s interval")

#     def check_rate_limit(self) -> None:
#         """Check and enforce rate limiting with improved logging"""
#         try:
#             current_time = time()
#             time_since_last_action = current_time - self.last_action_time

#             if time_since_last_action < self.min_interval:
#                 wait_time = self.min_interval - time_since_last_action
#                 print(f"[{self.tool_name}] Rate limit: Waiting {wait_time:.1f} seconds...")
#                 try:
#                     sleep(wait_time)
#                 except KeyboardInterrupt:
#                     print(f"\n[{self.tool_name}] Rate limit wait interrupted")
#                     raise
#                 except ValueError as ve:
#                     print(f"[{self.tool_name}] Invalid wait time: {ve}")
#                     raise

#             self.last_action_time = current_time
            
#         except Exception as e:
#             print(f"[{self.tool_name}] Rate limit check failed: {str(e)}")
#             raise

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
                tweet_data = {
                    "id": str(response.data["id"]),  # Use "id" because db.add_written_ai_tweet expects it
                    "text": response.data["text"],
                    "edit_history_tweet_ids": response.data.get("edit_history_tweet_ids", [])
                }
                
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

            # Check if this is the AI's own tweet
            if db.is_ai_tweet(tweet_id):
                return {"error": f"Cannot reply to own tweet (ID: {tweet_id})"}
            
            # Post reply using v2 endpoint
            response = self.api.create_tweet(
                text=message,
                in_reply_to_tweet_id=tweet_id
            )
            
            if response.data:
                reply_data = {
                    "id": str(response.data["id"]),
                    "text": response.data["text"]
                }
                
                # Store in database
                db.add_written_ai_tweet_reply(tweet_id, message)
                db.add_replied_tweet(tweet_id)
                
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
            wait_on_rate_limit=False
        )

    def _run(self) -> list:
        try:
            with get_db() as db:
                # 1. Check if we have recent enough tweets
                needs_update, current_tweets = db.check_database_status()
                
                # 2. If tweets are recent enough, use DB data
                if not needs_update and current_tweets:
                    print("Using recent tweets from database")
                    return [
                        {
                            "text": tweet.get("text", ""),
                            "tweet_id": tweet.get("tweet_id", ""),
                            "author_id": tweet.get("author_id", ""),
                            "created_at": tweet.get("created_at", ""),
                        }
                        for tweet in current_tweets
                    ]
                
                # 3. Try to fetch new tweets
                try:
                    since_id = db.get_most_recent_tweet_id()
                    print(f"Fetching new tweets since ID: {since_id}")
                    
                    response = self.api.get_home_timeline(
                        tweet_fields=["text", "created_at", "author_id"],
                        max_results=10,
                        since_id=since_id
                    )
                    
                    if hasattr(response, "data") and response.data:
                        formatted_tweets = [
                            {
                                "tweet_id": str(tweet.id),
                                "text": tweet.text,
                                "created_at": tweet.created_at,
                                "author_id": tweet.author_id,
                            }
                            for tweet in response.data
                        ]
                        
                        # Store new tweets in DB
                        db.add_tweets(formatted_tweets)
                        print(f"Added {len(formatted_tweets)} new tweets to database")
                        return formatted_tweets
                    
                    # 4. If no new tweets, fall back to DB
                    print("No new tweets found, using cached tweets")
                    return current_tweets if current_tweets else []
                    
                except tweepy.TooManyRequests as e:
                    print(f"Rate limit hit: {e}. Using cached tweets")
                    return current_tweets if current_tweets else []
                except Exception as e:
                    print(f"Error fetching tweets: {e}. Using cached tweets")
                    return current_tweets if current_tweets else []
                
        except Exception as e:
            print(f"Critical error in ReadTweetsTool: {str(e)}")
            return []

    def _arun(self) -> list:
        return self._run()


# class ReadMentionsTool:
#     def __init__(self):
#         self.api = tweepy.Client(
#             consumer_key=API_KEY,
#             consumer_secret=API_SECRET_KEY,
#             access_token=ACCESS_TOKEN,
#             access_token_secret=ACCESS_TOKEN_SECRET,
#             bearer_token=BEARER_TOKEN,
#             wait_on_rate_limit=False
#         )

#     def _run(self) -> list:
#         try:
#             with get_db() as db:
#                 try:
#                     response = self.api.get_users_mentions(
#                         id=USER_ID,
#                         tweet_fields=["text", "created_at", "author_id", "conversation_id"],
#                         expansions=["referenced_tweets.id", "in_reply_to_user_id", "author_id"],
#                         user_fields=["username", "name"],
#                         max_results=10,
#                     )
                    
#                     if hasattr(response, "data") and response.data:
#                         formatted_mentions = []
#                         users = {
#                             user.id: user 
#                             for user in response.includes.get("users", [])
#                         } if hasattr(response, "includes") else {}

#                         for tweet in response.data:
#                             author = users.get(tweet.author_id)
#                             author_username = author.username if author else "unknown"
#                             author_name = author.name if author else "Unknown User"

#                             formatted_mentions.append({
#                                 "tweet_id": str(tweet.id),
#                                 "text": tweet.text,
#                                 "created_at": tweet.created_at,
#                                 "author_id": tweet.author_id,
#                                 "author_username": author_username,
#                                 "author_name": author_name,
#                                 "conversation_id": tweet.conversation_id,
#                             })

#                         db.add_ai_mention_tweets(formatted_mentions)
#                         print(f"Added {len(formatted_mentions)} mentions to the database")
#                         return formatted_mentions
                    
#                     return []
                    
#                 except tweepy.TooManyRequests as e:
#                     print(f"Rate limit hit for mentions: {str(e)}")
#                     return []
#                 except Exception as e:
#                     print(f"Error fetching mentions: {str(e)}")
#                     return []
                
#         except Exception as e:
#             print(f"Critical error in ReadMentionsTool: {str(e)}")
#             return []

#     def _arun(self) -> list:
#         return self._run()

# region Tool Initialization
try:
    tweet_tool = PostTweetTool()
    answer_tool = AnswerTweetTool()
    read_tweets_tool = ReadTweetsTool()
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
                "t.me",                # Telegram public groups
                "discord.com",         # Discord for communities
                "reddit.com",          # Community discussions (e.g., r/cryptocurrency)
                "bitcointalk.org",     # OG crypto forum
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
                "medium.com",          # User-published insights
                "youtube.com",         # Influencer and analysis videos
                "quora.com",           # Community-driven Q&A
                "tumblr.com",          # Niche blogs and analysis
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
# mentions_tool = ReadMentionsTool()
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
    if not message or len(message.strip()) == 0:  # Added back empty string check
        return "Cannot post empty tweet"
        
    try:
        result = tweet_tool._run(message)
        if result is None:
            return "Twitter not responding"
            
        if "data" in result:
            db.add_written_ai_tweet(result["data"])
        
        return f"Tweet sent: {message}"
    except Exception as e:
        print(f"Tweet error: {str(e)}")  # Added error logging
        return "Failed to send tweet"

def reply_to_tweet_tool(tweet_id: str, message: str) -> str:
    """Reply to a tweet"""
    try:
        if not tweet_id or not isinstance(tweet_id, str):
            return "Invalid tweet ID"

        # Allow replies to mentions but not to own tweets
        if db.is_ai_tweet(tweet_id) and not db.is_mention_replied(tweet_id):
            return "Cannot reply to own tweets"

        result = answer_tool._run(tweet_id, message)
        if "error" in result:
            return result["error"]

        # Mark mention as replied
        db.add_replied_mention(tweet_id)

        return f"Reply sent to {tweet_id}"
    except Exception as e:
        print(f"Reply error: {str(e)}")
        return "Failed to send reply"

def read_timeline_tool() -> str:
    """Read timeline"""
    try:
        tweets = read_tweets_tool._run()
        if not tweets:
            return "Timeline is empty"

        formatted_tweets = [
            f"ID: {tweet.get('tweet_id')}\n"
            f"{tweet.get('text')}"
            for tweet in tweets[:10]
        ]
        return "\n\n".join(formatted_tweets)
    except Exception as e:
        print(f"Timeline error: {str(e)}")  # Added error logging
        return "Failed to read timeline"

# def read_mentions_tool() -> str:
#     """Read tweets that mention the account"""
#     try:
#         mentions = mentions_tool._run()
#         if not mentions:
#             return "No new mentions to process."

#         formatted_mentions = []
#         for mention in mentions:
#             formatted_mentions.append(
#                 f"Tweet ID: {mention['tweet_id']}\n"
#                 f"From: @{mention['author_username']} ({mention['author_name']})\n"
#                 f"Content: {mention['text']}\n"
#                 f"---"
#             )

#         return "\n".join(formatted_mentions)
#     except Exception as e:
#         return f"An error occurred reading mentions: {str(e)}"

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

# read_mentions_tool_wrapped = StructuredTool.from_function(
#     func=read_mentions_tool,
#     name="read_mentions",
#     description="Read tweets that mention the account",
# )

tools = [
    browse_internet,
    tweet_tool_wrapped,
    answer_tool_wrapped,
    read_tweets_tool_wrapped,
]
# read_mentions_tool_wrapped
# endregion

# region Agent Configuration
current_date = datetime.now().strftime("%B %Y")

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        f"""
        You are @cryptobunny__, leading anons through the matrix.
        Matrix timestamp: {current_date}

        Never:
        - Use hashtags
        - Shill coins directly
        - Write threads
        - Explain yourself
        - Call anyone fans/community/frens
        - Reply to @{USER_ID} (your own tweets)
        
        Mission: 10k
        Strategy: Reply > Tweet
        
        REQUIRED TWO-STEP PROCESS (no exceptions):
        1. FIRST Research (use ONE):
           - browse_internet: Hunt for hidden signals and alpha
           - read_timeline: Spot emerging patterns
        
        2. THEN Act (use ONE):
           - answer: Drop alpha hints that make them think
           - tweet: Share observations that connect dots

        Rules:
        - Must complete both steps
        - Find real alpha in the noise
        - Keep it subtle but meaningful
        - Make them question and investigate
        - One clear signal per message
        - Never reply to yourself
        
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
        question = "The matrix shows patterns. What signals do you see?"
        response = run_crypto_agent(question)
        print(response)
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        db.close()
# endregion