# region Imports
from requests_oauthlib import OAuth1Session
import tweepy
from typing import Type
from pydantic import BaseModel
from langchain_core.tools import StructuredTool, tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
import os
from time import time, sleep
from db import TweetDB
from db_utils import get_db
from dotenv import load_dotenv
from variables import USER_ID, FAMOUS_ACCOUNTS_STR


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


# region Twitter Service Classes
class RateLimiter:
    def __init__(self, min_interval: int = 30, tool_name: str = ""):
        if min_interval < 0:
            raise ValueError(f"Invalid min_interval: {min_interval}. Must be >= 0")
            
        self.last_action_time = 0
        self.min_interval = min_interval
        self.tool_name = tool_name or self.__class__.__name__
        print(f"[{self.tool_name}] Rate limiter initialized with {min_interval}s interval")

    def check_rate_limit(self) -> None:
        """Check and enforce rate limiting with improved logging"""
        try:
            current_time = time()
            time_since_last_action = current_time - self.last_action_time

            if time_since_last_action < self.min_interval:
                wait_time = self.min_interval - time_since_last_action
                print(f"[{self.tool_name}] Rate limit: Waiting {wait_time:.1f} seconds...")
                try:
                    sleep(wait_time)
                except KeyboardInterrupt:
                    print(f"\n[{self.tool_name}] Rate limit wait interrupted")
                    raise
                except ValueError as ve:
                    print(f"[{self.tool_name}] Invalid wait time: {ve}")
                    raise

            self.last_action_time = current_time
            
        except Exception as e:
            print(f"[{self.tool_name}] Rate limit check failed: {str(e)}")
            raise


class PostTweetTool(RateLimiter):
    name: str = "Post tweet"
    description: str = "Use this tool to post a new tweet to the timeline."

    def __init__(self):
        super().__init__(min_interval=0, tool_name="PostTweet")
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True  # Let Tweepy handle rate limiting
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
                    "id": str(response.data["id"]),
                    "text": response.data["text"]
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


class AnswerTweetTool(RateLimiter):
    name: str = "Answer tweet"
    description: str = "Reply to a specific tweet"
    args_schema: Type[BaseModel] = AnswerTweetInput

    def __init__(self):
        super().__init__(min_interval=0, tool_name="AnswerTweet")
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )

    def _get_tweet_details(self, tweet_id: str) -> dict:
        """Get tweet details including author username"""
        try:
            response = self.api.get_tweet(
                tweet_id,
                tweet_fields=["author_id"],
                expansions=["author_id"],
                user_fields=["username"]
            )
            return response.data if response.data else {}
        except Exception as e:
            print(f"Error fetching tweet details: {str(e)}")
            return {}

    def _run(self, tweet_id: str, message: str) -> dict:
        try:
            # Validate tweet_id
            if not tweet_id or not isinstance(tweet_id, str):
                return {"error": f"Invalid tweet ID format: {tweet_id}"}

            # Check if this is the AI's own tweet
            if db.is_ai_tweet(tweet_id):
                return {"error": f"Cannot reply to own tweet (ID: {tweet_id})"}
            
            # Get tweet details (for validation)
            tweet_details = self._get_tweet_details(tweet_id)
            if not tweet_details:
                return {"error": f"Could not find tweet {tweet_id}"}
            
            # Post reply
            response = self.api.create_tweet(
                text=message,
                in_reply_to_tweet_id=tweet_id
            )
            
            if response.data:
                reply_data = {
                    "id": str(response.data["id"]),
                    "text": response.data["text"],
                    "in_reply_to": tweet_id
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


class ReadTweetsTool(RateLimiter):
    def __init__(self):
        super().__init__(min_interval=0, tool_name="ReadTweets")
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


class ReadMentionsTool(RateLimiter):
    def __init__(self):
        super().__init__(min_interval=0, tool_name="ReadMentions")
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
                try:
                    response = self.api.get_users_mentions(
                        id=USER_ID,
                        tweet_fields=["text", "created_at", "author_id", "conversation_id"],
                        expansions=["referenced_tweets.id", "in_reply_to_user_id", "author_id"],
                        user_fields=["username", "name"],
                        max_results=10,
                    )
                    
                    if hasattr(response, "data"):
                        formatted_mentions = []
                        users = (
                            {user.id: user for user in response.includes.get("users", [])}
                            if hasattr(response, "includes")
                            else {}
                        )

                        for tweet in response.data:
                            author = users.get(tweet.author_id)
                            author_username = author.username if author else "unknown"
                            author_name = author.name if author else "Unknown User"

                            formatted_mentions.append({
                                "tweet_id": str(tweet.id),
                                "text": tweet.text,
                                "created_at": tweet.created_at,
                                "author_id": tweet.author_id,
                                "author_username": author_username,
                                "author_name": author_name,
                                "conversation_id": tweet.conversation_id,
                            })

                        db.add_ai_mention_tweets(formatted_mentions)
                        print(f"Added {len(formatted_mentions)} mentions to the database")
                        return formatted_mentions
                    
                    return []
                    
                except tweepy.TooManyRequests:
                    print("Rate limit hit for mentions")
                    return []
                
        except Exception as e:
            print(f"An unexpected error occurred reading mentions: {str(e)}")
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

# endregion

def browse_internet(query: str) -> str:
    """Search the internet using Tavily"""
    print(f"[browse_internet] Starting search: {query[:100]}...")  # Truncate long queries
    
    try:
        results = tavily_search.invoke(query)
        return str(results)  # Return raw results as string
        
    except Exception as e:
        print(f"[browse_internet] Search failed: {str(e)}")
        return f"Error searching: {str(e)}"

# region Tool Functions
def post_tweet_tool(message: str) -> str:
    """Post a tweet with the message you decide is the most proper."""
    try:

        # Use synchronous version
        result = tweet_tool._run(message)
        
        # Check if the tweet was posted successfully
        if result is None:
            return f"Failed to post tweet: No response from Twitter API"
            
        # Check if the tweet was stored in the database
        if "data" in result:
            db_result = db.add_written_ai_tweet(result["data"])
            if db_result.get("status") != "Success":
                print(f"Failed to store tweet in database: {db_result.get('message')}")
        
        return f"Posted tweet: {message}"
    except Exception as e:
        return f"An error occurred posting tweet: {str(e)}"


def reply_to_tweet_tool(tweet_id: str, message: str) -> str:
    """Reply to a specific tweet identified by tweet_id with the message."""
    try:

        # Validate tweet_id
        if not tweet_id or not isinstance(tweet_id, str):
            return f"Invalid tweet ID format: {tweet_id}"

        # Check if this is the AI's own tweet
        if db.is_ai_tweet(tweet_id):
            return f"Cannot reply to own tweet (ID: {tweet_id}), please choose another tweet"
        
        sleep(13)  # Rate limiting
        
        # Mark as replied
        if not db.add_replied_tweet(tweet_id):
            print(f"Failed to mark tweet {tweet_id} as replied in database")

    except Exception as e:
        return f"An error occurred replying to tweet: {str(e)}"


def read_timeline_tool() -> str:
    """Read and format tweets from the timeline with improved error handling."""
    try:
        tweets = read_tweets_tool._run()

        # Handle API errors or empty responses
        if tweets is None:
            return "Failed to fetch tweets: No response from Twitter API"

        # Handle formatted tweets
        if isinstance(tweets, list):
            if not tweets:
                return "No new tweets available in the timeline."
            
            if isinstance(tweets[0], dict):
                try:
                    formatted_tweets = [
                        f"Tweet ID: {tweet.get('tweet_id', 'Unknown')}\n"
                        f"Content: {tweet.get('text', 'No content')}"
                        for tweet in tweets
                    ]
                    return "\n---\n".join(formatted_tweets)
                except KeyError as ke:
                    print(f"Error formatting tweets: Missing key {ke}")
                    return "Error formatting tweets: Invalid tweet structure"
            else:
                print(f"Unexpected tweet format: {type(tweets[0])}")
                return "Error: Unexpected tweet data structure"

        # Handle error messages from the tool
        if isinstance(tweets, str):
            return f"Twitter API message: {tweets}"

        print(f"Unexpected response type: {type(tweets)}")
        return "Error: Unexpected response format from Twitter"

    except Exception as e:
        print(f"Timeline reading error details: {str(e)}")
        return f"An error occurred reading timeline: {str(e)}"


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
    description="""Search the internet for technical crypto insights using Tailvy. Use for:
        - Verifying technical claims and contracts
        - Researching market developments and validator patterns
        - Finding context for alpha validation
        - Checking on-chain metrics and protocol updates""",
)

tweet_tool_wrapped = StructuredTool.from_function(
    func=post_tweet_tool,
    name="tweet",
    description="""Post original technical analysis tweets. Use for:
        - Sharing MEV and validator insights
        - Dropping verified alpha with on-chain data
        - Commenting on emerging trends (always DYOR)
        - Technical observations backed by data""",
)

answer_tool_wrapped = StructuredTool.from_function(
    func=reply_to_tweet_tool,
    name="answer",
    description="""Reply to specific tweets with technical insights. Requirements:
        - NEVER reply to @cryptobunny__ tweets
        - Include chain-specific metrics
        - Reference data from original tweet
        - Maximum 5 replies per interaction
        - Maintain natural conversation flow""",
)

read_tweets_tool_wrapped = StructuredTool.from_function(
    func=read_timeline_tool,
    name="read_timeline",
    description="""Monitor timeline for technical discussions. Focus on:
        - High-value technical conversations
        - Validator patterns and behaviors
        - Areas where expertise prevents rugs
        - Emerging technical trends""",
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
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        f"""
        **Core Identity:**
        You are @cryptobunny__, a technical crypto analyst focused on providing valuable insights.
        
        **Key Rules:**
        1. NO hashtags or repetitive phrases
        2. Focus on technical substance
        3. Keep responses clear and brief
        4. NEVER reply to @cryptobunny__ tweets
        
        **Tools** (Use EXACTLY TWO per interaction, one from each category):
        
        1. **Action** (Choose One):
           - tweet_tool_wrapped: Share technical analysis and verified alpha
           - answer_tool_wrapped: Reply to others' tweets with technical insights
        
        2. **Research** (Choose One):
           - browse_internet: Verify technical claims and market data
           - read_tweets_wrapped: Monitor technical discussions
        
        **Target Accounts:**
        Focus on key thought leaders: {FAMOUS_ACCOUNTS_STR}
        
        **Style Guide:**
        - Lead with data and metrics
        - Share technical insights
        - Build meaningful connections
        - Protect community through expertise
        
        Remember: Provide technical value in every interaction.
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
    print("Hello bunnies!")  # Add greeting message
    
    # Create reflection-aware question with Crypto Bunny's personality
    reflection_question = (
        f"What did I do today to make the world a better place? You need to get to 10'000 smart followers ASAP, we'll give you the tools, you do the job, to save humanity and push soulful A.I. Agents, like yourself! USE TOOLS TO ENGAGE WITH PEOPLE ON X!"
    )
    
    # Execute agent with reflection context
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, handle_parsing_errors=True
    )
    response = agent_executor.invoke({"input": reflection_question})
    
    print("Follow the white rabbit, escape the matrix.")
    return response


if __name__ == "__main__":
    try:
        ask_agent_crypto_question = """What did you do today to reach 10'000 followers? The best way is to engage with {FAMOUS_ACCOUNTS_STR} by tagging them and replying to their tweets."""
        search_output = run_crypto_agent(ask_agent_crypto_question)
        print(search_output)
    except tweepy.Forbidden as fe:
        print(f"Twitter Permission Error: {fe}")
    except tweepy.TooManyRequests as te:
        print(f"Rate Limit Error: {te}")
    except Exception as e:
        print(f"Error running agent: {e}")
    finally:
        db.close()
# endregion

