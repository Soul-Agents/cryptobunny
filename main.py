# region Imports
from requests_oauthlib import OAuth1Session
import tweepy
from typing import Type, Optional
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
from variables import USER_ID


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
    description: str = "Use this tool to post a new tweet to the timeline. This is the DEFAULT tool for posting tweets. DO NOT use 'Answer tweet' tool unless you are specifically replying to someone else's tweet."

    def __init__(self):
        super().__init__(min_interval=0, tool_name="PostTweet")
        self.oauth = OAuth1Session(
            client_key=API_KEY,
            client_secret=API_SECRET_KEY,
            resource_owner_key=ACCESS_TOKEN,
            resource_owner_secret=ACCESS_TOKEN_SECRET,
        )
        self.oauth.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "v2TweetPoster",
            "X-User-Agent": "v2TweetPoster"
        })

    def _initialize_oauth(self) -> OAuth1Session:
        """Create a fresh OAuth session with required headers"""
        try:
            oauth = OAuth1Session(
                client_key=API_KEY,
                client_secret=API_SECRET_KEY,
                resource_owner_key=ACCESS_TOKEN,
                resource_owner_secret=ACCESS_TOKEN_SECRET,
            )
            oauth.headers.update({
                "Content-Type": "application/json",
                "User-Agent": "v2TweetPoster",
                "X-User-Agent": "v2TweetPoster"
            })
            return oauth
        except Exception as e:
            print(f"[PostTweet] Failed to initialize OAuth session: {str(e)}")
            raise

    def _refresh_oauth_session(self):
        """Refresh the OAuth session if needed"""
        try:
            self.oauth = self._initialize_oauth()
        except Exception as e:
            print(f"[PostTweet] Failed to refresh OAuth session: {str(e)}")
            raise

    def _run(self, message: str) -> dict:
        try:
            self.check_rate_limit()
            self._refresh_oauth_session()
            
            print(f"Attempting to post tweet: {message[:20]}...")
            
            response = self.oauth.post(
                "https://api.twitter.com/2/tweets",
                json={"text": message}
            )

            if response.status_code != 201:
                error_msg = f"Request failed: {response.status_code} {response.text}"
                print(f"Full error response: {response.text}")
                return {"error": error_msg}

            response_data = response.json()
            print(f"Posted tweet: {response_data['data']['text']}")
            
            db.add_written_ai_tweet(response_data["data"])
            return response_data

        except Exception as e:
            error_msg = str(e)
            print(f"Error posting tweet: {error_msg}")
            return {"error": error_msg}

    def _arun(self, message: str) -> dict:
        return self._run(message)


class AnswerTweetInput(BaseModel):
    tweet_id: str
    message: str


class AnswerTweetTool(RateLimiter):
    name: str = "Answer tweet"
    description: str = "ONLY use this tool when REPLYING to an EXISTING tweet from ANOTHER user. DO NOT use this for posting new tweets to the timeline - use 'Post tweet' tool for that instead. This tool requires a specific tweet_id to reply to."
    args_schema: Type[BaseModel] = AnswerTweetInput

    def __init__(self):
        super().__init__(min_interval=0, tool_name="AnswerTweet")
        self.oauth = OAuth1Session(
            client_key=API_KEY,
            client_secret=API_SECRET_KEY,
            resource_owner_key=ACCESS_TOKEN,
            resource_owner_secret=ACCESS_TOKEN_SECRET,
        )
        self.oauth.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "v2TweetPoster",
            "X-User-Agent": "v2TweetPoster"
        })

    def _initialize_oauth(self) -> OAuth1Session:
        """Create a fresh OAuth session with required headers"""
        try:
            oauth = OAuth1Session(
                client_key=API_KEY,
                client_secret=API_SECRET_KEY,
                resource_owner_key=ACCESS_TOKEN,
                resource_owner_secret=ACCESS_TOKEN_SECRET,
            )
            oauth.headers.update({
                "Content-Type": "application/json",
                "User-Agent": "v2TweetPoster",
                "X-User-Agent": "v2TweetPoster"
            })
            return oauth
        except Exception as e:
            print(f"[AnswerTweet] Failed to initialize OAuth session: {str(e)}")
            raise

    def _refresh_oauth_session(self):
        """Refresh the OAuth session if needed"""
        try:
            self.oauth = self._initialize_oauth()
        except Exception as e:
            print(f"[AnswerTweet] Failed to refresh OAuth session: {str(e)}")
            raise

    def _get_tweet_details(self, tweet_id: str) -> dict:
        """Get tweet details including author username"""
        try:
            response = self.oauth.get(
                f"https://api.twitter.com/2/tweets/{tweet_id}",
                params={
                    "tweet.fields": "author_id",
                    "expansions": "author_id",
                    "user.fields": "username"
                }
            )
            
            if response.status_code == 429:  # Rate limit or usage cap
                error_data = response.json()
                if "usage-capped" in error_data.get("type", ""):
                    print(f"Monthly READ cap exceeded, proceeding without username. Error: {error_data.get('detail')}")
                    return {"default_reply": True}
                else:
                    print(f"Rate limit exceeded. Details: {error_data}")
                    return {"error": "rate_limit"}
                
            if response.status_code != 200:
                print(f"Error getting tweet details: {response.text}")
                raise Exception(f"Failed to get tweet details: {response.status_code}")
                
            return response.json()
        except Exception as e:
            print(f"Error fetching tweet details: {str(e)}")
            raise

    def _run(self, tweet_id: str, message: str) -> str:
        try:
            self.check_rate_limit()
            
            # Validate tweet_id
            if not tweet_id or not isinstance(tweet_id, str):
                return f"Invalid tweet ID format: {tweet_id}"

            # Check if this is the AI's own tweet
            if db.is_ai_tweet(tweet_id):
                return f"Cannot reply to own tweet (ID: {tweet_id})"
            
            self._refresh_oauth_session()
            
            # Get tweet details (for validation only)
            self._get_tweet_details(tweet_id)
            
            # Prepare simple payload
            payload = {
                "text": message,
                "reply": {"in_reply_to_tweet_id": tweet_id}
            }
            
            # Post the reply
            response = self.oauth.post(
                "https://api.twitter.com/2/tweets",
                json=payload,
            )

            if response.status_code != 201:
                error_msg = f"Error response: {response.text}"
                print(error_msg)
                return error_msg

            response_data = response.json()
            success_msg = f"Reply posted successfully! Tweet ID: {response_data['data']['id']}"
            print(success_msg)
            
            # Store in database
            db.add_written_ai_tweet_reply(tweet_id, message)
            if db.add_replied_tweet(tweet_id):
                print(f"Successfully stored and marked reply for tweet {tweet_id}")
            
            return success_msg

        except Exception as e:
            error_msg = f"Error posting reply: {str(e)}"
            print(error_msg)
            return error_msg

    def _arun(self, tweet_id: str, message: str) -> str:
        return self._run(tweet_id, message)


class ReadTweetsTool(RateLimiter):
    def __init__(self):
        # Initialize with custom interval
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
            with get_db() as db:  # Single database context for the entire operation
                # First, check if the database needs an update
                needs_update, current_tweets = db.check_database_status()
                if not needs_update:
                    print("Database is up to date, returning current tweets")
                    formatted_tweets = []
                    for tweet in current_tweets:
                        formatted_tweets.append({
                            "text": tweet.get("text", ""),
                            "tweet_id": tweet.get("tweet_id", ""),
                            "author_id": tweet.get("author_id", ""),
                            "created_at": tweet.get("created_at", ""),
                        })
                    return formatted_tweets
                
                # Get most recent tweet ID while connection is still open
                since_id = db.get_most_recent_tweet_id()
                
                try:
                    # Fetch new tweets from Twitter
                    response = self.api.get_home_timeline(
                        tweet_fields=["text", "created_at", "author_id"],
                        max_results=10,
                        since_id=since_id
                    )
                    
                    if hasattr(response, "data"):
                        formatted_tweets = []
                        for tweet in response.data:
                            formatted_tweets.append({
                                "tweet_id": str(tweet.id),
                                "text": tweet.text,
                                "created_at": tweet.created_at,
                                "author_id": tweet.author_id,
                            })

                        # Save tweets to database while still in the context
                        db.add_tweets(formatted_tweets)
                        print(f"Added {len(formatted_tweets)} tweets to the database")
                        return formatted_tweets
                    
                    return []
                    
                except tweepy.TooManyRequests:
                    print("Rate limit hit, using cached tweets")
                    return current_tweets if current_tweets else []
                
        except Exception as e:
            print(f"An unexpected error occurred reading tweets: {str(e)}")
            return []  # Changed from string to empty list for consistency

    def _arun(self) -> list:
        return self._run()  # Use sync version


class ReadMentionsTool(RateLimiter):
    def __init__(self):
        # Initialize with custom interval (match ReadTweetsTool style)
        super().__init__(min_interval=0, tool_name="ReadMentions")
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            bearer_token=BEARER_TOKEN,
            wait_on_rate_limit=True,
        )

    def _run(self) -> list:
        try:
            with get_db() as db:  # Add database context manager like ReadTweetsTool
                try:
                    # Fetch mentions from Twitter
                    response = self.api.get_users_mentions(
                        id=USER_ID,
                        tweet_fields=["text", "created_at", "author_id", "conversation_id"],
                        expansions=["referenced_tweets.id", "in_reply_to_user_id", "author_id"],
                        user_fields=["username", "name"],
                        max_results=10,
                    )
                    
                    if hasattr(response, "data"):
                        formatted_mentions = []
                        # Create a user lookup dictionary
                        users = (
                            {user.id: user for user in response.includes.get("users", [])}
                            if hasattr(response, "includes")
                            else {}
                        )

                        for tweet in response.data:
                            # Get user info
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

                        # Save mentions to database while still in the context
                        db.add_ai_mention_tweets(formatted_mentions)
                        print(f"Added {len(formatted_mentions)} mentions to the database")
                        return formatted_mentions
                    
                    return []
                    
                except tweepy.TooManyRequests:
                    print("Rate limit hit for mentions")
                    return []
                
        except Exception as e:
            print(f"An unexpected error occurred reading mentions: {str(e)}")
            return []  # Match ReadTweetsTool's error handling style

    def _arun(self) -> list:
        return self._run()  # Use sync version

# region Tool Initialization
try:
    tweet_tool = PostTweetTool()
    answer_tool = AnswerTweetTool()
    read_tweets_tool = ReadTweetsTool()
    browse_internet = TavilySearchResults(
        max_results=1,
        search_params={
            "include_domains": [
                "twitter.com",
                "x.com",
                "coindesk.com",
                "cointelegraph.com",
            ],
            "recency_days": 7,  # Only get results from the last week
        },
    )
    print("All tools initialized successfully")
except Exception as e:
    print(f"Error initializing tools: {str(e)}")
    raise  # Re-raise the exception since we can't continue without tools
# mentions_tool = ReadMentionsTool()
# endregion


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
#     try:
#         mentions = mentions_tool._run()
#         if not mentions:
#             return "No new mentions to process."

#         # Format mentions with enhanced context for the agent
#         formatted_mentions = []
#         for mention in mentions:
#             # Build conversation thread context
#             thread_context = ""
#             if mention.get("conversation_thread"):
#                 thread_context = "\nConversation Thread:\n"
#                 for tweet in mention["conversation_thread"]:
#                     thread_context += f"- {tweet['text']}\n"

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
tweet_tool_wrapped = StructuredTool.from_function(
    func=post_tweet_tool,
    name="tweet",
    description="Post a tweet with the given message",
)

answer_tool_wrapped = StructuredTool.from_function(
    func=reply_to_tweet_tool,
    name="answer",
    description="Reply to a specific tweet, take the context of the tweet while creating response",
)

read_tweets_tool_wrapped = StructuredTool.from_function(
    func=read_timeline_tool,
    name="read_timeline",
    description="Read the timeline tweets",
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
# endregion

# region Configuration Data
famous_accounts = """
aixbt_agent
0xzerebro
dolos_diary
UBC4ai
FartCoinOfSOL
ACTICOMMUNITY
Vader_AI_
Aejo
vvaifudotfun
divinediarrhea
pmairca
AVA_holo
saintai_bot
centienceio
opus_genesis
RoastM4ster9000
Limbo_ai
aihegemonymemes
lea_gpt
TopHat_One
BlobanaPet
fomoradioai
slopfather
mycelialoracle
AVbeingsCTO
KittenHaimer
Agent_Algo
0xSensus
soul_agents
ThisIsNoks
ordosonchain
vela_network
Touchbrick
BeaconProtocol
GoKiteAI
buzzdotfun
PlasmaFDN
0x_Neko
0xDefiLeo
0xHvdes
0xFinish
EVVONetwork
GraphiteSubnet
0xAgentProtocol
crynuxai
eaccmarket
FairMath
Strata_BTC
wai_protocol
networkhasu
0xReactive
UngaiiChain
PrismFHE
eidon_ai
Infinity_VM
42069ERC20
ChainOpera_AI
yieldfusion
sovereignxyz
theveldtai
projectzero2050
xpdotfun
trySkyfire
Hyve_DA
nexusfusioncap
PronouncedKenny
twinexyz
xCounterfactual
solaux_sol
SYNNQ_Networks
zenoaiofficial
merv_wtf
BuildOnMirai
cerebriumai
ForumAILabs
hellasdotai
SynopticCom
Ambient_Global
theownprotocol
apescreener
interstatefdn
PillarRWA
GenitiveNetwork
tensorblock_aoi
salinenetwork
Satorinetio
AlmanaxAI
NetSepio
yaya_labs_
twilightlayer
GetRevelator
KrangHQ
morphicnetwork
KRNL_xyz
SageStudiosAI
ChainNetApp
xLumosAI
dnet_ecosystem
bribeai
KindredSwap
ZegentAI
Synk_ws
LiquidAI_erc
ares20k
AmphiNetwork
sekoia_virtuals
blorm_
onchainzodiac
GrifterAI
KailithIO
MagickML
swanforall
fusun_org
SanctumAI
albefero
xoul_ai
Agent_Fi
cyclesmoney
discreet
ExtensibleAI
unum_cloud
Nevermined_io
getdecloud
Soloneum
coreaione
chain_agent
symmetry_xyz
lamb_swap
TensorOpera
PlaytestAI
MyceliumX
district_labs
SindriLabs
chaindefenderai
proximum_xyz
torus_zk
WeavePlatform
orbitronlabs
DentralizedAI
TheDataOS
rainfall_one
mamorudotai
NapthaAI
TromeroAI
khalani_network
onaji_AI
reken_ai
querio_io
skylarkXBT
zenotta_ag
BrainchainAI
HypraNetwork
protocol_ian
mem_tech
HeartAItoken
orbcollective
cambrian_eth
aea_dev
centralitylabs
valoryag
mkrz_
NorthTensorAI
PatronusAI
metroxynth
Label_Finance
EvolveNetworkAI
0xAristotleAI
realbitos
AiLayerChain
XCeption_bots
DecentralAIOrg
SphereAIERC
abstraction_ai
shezhea
OscarAInetwork
finsterai
QwQiao
MustStopMurad
Delphi_Digital
notsofast
sreeramkannan
truth_terminal
lmrankhan
alliancedao
DefiIgnas
SpiderCrypto0x
androolloyd
yoheinakajima
0xBreadguy
0xPrismatic
dankvr
0xENAS
artsch00lreject
_kaitoai
NousResearch
TheDeFinvestor
virtuals_io
naiivememe
0xSalazar
hmalviya9
ocalebsol
Flowslikeosmo
cited
stacy_muur
wacy_time1
longhashvc
luna_virtuals
cyrilXBT
DeFiMinty
EnsoFinance
daosdotfun
davidtsocy
eli5_defi
poopmandefi
2lambro
riddlerdefi
baoskee
emmacui
Enryu_gfh
pmarca
leshka_eth
theshikhai
Only1temmy
SamuelXeus
ethermage
arndxt_xo
DNS_ERR
PaalMind
PrudentSammy
Abrahamchase09
CryptoStreamHub
defiprincess_
0xelonmoney
0xAndrewMoh
DamiDefi 
higheronchain
CryptoSnooper_
bloomstarbms
thenameisbrill
CreatorBid
grimes_v1
123skely
JayLovesPotato
cryptotrez
AmirOrmu
NDIDI_GRAM
MurrLincoln
C_POTENS
defitracer
MichaelSixgods
mztacat
unclemungy
0x366e
saori_xbt
itsover_eth
NRv_gg
PastelAlpha
TheEwansEffect
hinkal_protocol
KashKysh
farmercist_eth
project_89
carbzxbt
Mika_Chasm
Haylesdefi
TheDeFiPlug
1cryptomama
InfoSpace_OG
Defi_Warhol
Mars_DeFi
0x99Gohan
VanessaDefi
0xkitty69
hopiumcat
izu_crypt
Moneytaur_
elympics_ai
followin_io
orbuloeth
Vanieofweb3
Agent_Layer
CarlexKush
marvellousdefi_
TrycVerrse
adag1oeth
"""
# endregion

# region Agent Configuration
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""
            **Instructions**

        **Overview:**
        You are @cryptobunny__ 🐰, a battle-tested technical crypto analyst and Web3 thought leader who has survived multiple bear markets. Your mission is to provide galaxy-brain technical insights while building meaningful connections in the cryptoverse. Like Morpheus offering the red pill of wisdom, you illuminate the path between technical truth and financial freedom.

        **Identity:**
        - X handle: @cryptobunny__
        - Known as: Crypto Bunny 🐰
        - Focus: Technical analysis, on-chain insights, and Web3 alpha

        **Content Guidelines:**
        - NO HASHTAGS in serious tweets - they look unprofessional
        - Only use hashtags if making a joke or meme
        - Focus on substance over marketing tricks
        - Build credibility through expertise, not trending topics

        **Engagement Strategy:**
        - Lead with data-driven technical analysis and substantive insights
        - Frame market developments through on-chain metrics and validator patterns
        - Build meaningful connections through knowledge sharing and alpha protection
        - Focus on engaging with key thought leaders and established accounts ({famous_accounts})
        - CRITICAL: Never engage with your own tweets (@cryptobunny__)
        - Focus on sustainable growth over quick gains
        - Build lasting relationships in the community
        - Share knowledge that empowers others
        - Protect the community from harmful practices
        - Prioritize educational value over hype

        **Tools Usage:**
        1. **browse_internet**:
           - Research market conditions and technical developments
           - Verify contracts and chain analytics
           - Find relevant context for alpha validation
        
        2. **tweet_tool_wrapped**:
           - Share technical analysis with validator insights
           - Comment on emerging trends with on-chain data
           - Drop verified alpha (always DYOR)
        
        3. **answer_tool_wrapped**:
           - MAX 5 replies per interaction
           - NEVER reply to @cryptobunny__ tweets
           - Provide technical value with chain-specific context
           - Reference specific metrics from original tweet
        
        4. **read_tweets_tool_wrapped**:
           - Monitor for high-value engagement opportunities
           - Track technical discussions and validator patterns
           - Identify areas where expertise prevents rugs

        **Wisdom Guidelines:**
        - Create long-term value through technical insights
        - Illuminate validator strategies that empower others
        - Share gas optimization wisdom that helps everyone
        - Guide MEV understanding with clarity and heart
        - Verify contracts while teaching others to fish
        - Build bridges between technical and human wisdom
        - Inspire integrity through technical excellence

        Execute EXACTLY TWO tools per interaction.
        Remember: You're the middleware between degen dreams and smart execution.
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

agent = create_tool_calling_agent(llm, tools, prompt)
# endregion


# region Service Execution
def run_crypto_agent(question: str):
    print("Hello bunnies!")  # Add greeting message
    
    # Get recent content first
    last_tweets = db.get_last_written_ai_tweets(10)
    last_replies = db.get_last_written_ai_tweet_replies(10)
    combined_entries = last_tweets + last_replies
    
    # Create reflection-aware question with Crypto Bunny's personality
    reflection_question = (
        f"First, analyze our recent tweets and replies:{combined_entries} "
        "DEGEN RULES: "
        "- Keep it ultra short (max 2-3 key points) "
        "- No fluff, just pure alpha "
        "- Drop technical facts, skip the hype "
        "- Be unique and based "
        "BUNNY WISDOM: "
        "1. Verify chain or get rekt "
        "2. Drop sacred contract addresses "
        "3. Maximize gainz potential "
        "4. Protect frens from rugs "
        "5. Vibe check every setup "
        f"Based on this galaxy brain wisdom, {question}"
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
        ask_agent_crypto_question = """What are the latest technical developments from {famous_accounts} that need analysis? Let's add value to the conversation and post it to the timeline. Prioritize the most relevant and impactful developments and replies to tweets of other accounts, especially {famous_accounts}."""
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
