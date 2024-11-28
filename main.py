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
from dotenv import load_dotenv

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
        self.last_action_time = 0
        self.min_interval = min_interval  # configurable interval
        self.tool_name = tool_name or self.__class__.__name__

    def check_rate_limit(self) -> None:
        """Check and enforce rate limiting with improved logging"""
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

        self.last_action_time = current_time


class PostTweetTool(RateLimiter):
    name: str = "Post tweet"
    description: str = "Post a tweet with the given message"

    def __init__(self):
        # Initialize with custom interval
        super().__init__(min_interval=15, tool_name="PostTweet")

        # Initialize OAuth1Session with credentials
        self.oauth = OAuth1Session(
            client_key=API_KEY,
            client_secret=API_SECRET_KEY,
            resource_owner_key=ACCESS_TOKEN,
            resource_owner_secret=ACCESS_TOKEN_SECRET,
        )

    def post_tweet(self, message: str):
        try:
            self.check_rate_limit()
            # Prepare the payload
            payload = {"text": message}

            # Make the request to Twitter API v2
            response = self.oauth.post(
                "https://api.twitter.com/2/tweets",
                json=payload,
            )

            # Check response
            if response.status_code != 201:
                raise Exception(
                    "Request returned an error: {} {}".format(
                        response.status_code, response.text
                    )
                )

            print("Tweet posted successfully!")
            print("tweet data", response.json()["data"])
            # Add tweet to database
            # tweet structure: {"data": {"id": "1234567890", "text": "Hello, world!"}}
            tweet = response.json()["data"]
            db.add_written_ai_tweet(tweet)
            return response.json()

        except Exception as e:
            print(f"Error posting tweet: {str(e)}")
            return None


class AnswerTweetInput(BaseModel):
    tweet_id: str
    message: str


class AnswerTweetTool(RateLimiter):
    name: str = "Answer tweet"
    description: str = "Use this tool when you need to reply to a tweet"
    args_schema: Type[BaseModel] = AnswerTweetInput

    def __init__(self):
        # Initialize with custom interval
        super().__init__(min_interval=30, tool_name="AnswerTweet")
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True,
        )

    def _run(self, tweet_id: str, message: str) -> str:
        try:

            # Post a reply to the tweet
            self.api.create_tweet(text=message, in_reply_to_tweet_id=tweet_id)
            return "Reply tweet posted successfully!"
        except tweepy.TweepyException as e:
            return f"Tweepy error occurred: {str(e)}"
        except Exception as e:
            return f"An error occurred answering tweet: {e}"

    async def _arun(self):
        return "Not implemented"


class ReadTweetsTool(RateLimiter):
    def __init__(self):
        # Initialize with custom interval
        super().__init__(min_interval=60, tool_name="ReadTweets")
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True,
        )

    def _run(self) -> list:
        try:
            # First, check if the database needs an update
            needs_update, current_tweets = db.check_database_status()
            if not needs_update:
                print("Database is up to date, returning current tweets")

                formatted_tweets = []
                for tweet in current_tweets:
                    formatted_tweets.append(
                        {
                            "text": tweet.get("text", ""),
                            "id": tweet.get("tweet_id", ""),
                            "author_id": tweet.get("author_id", ""),
                            "created_at": tweet.get("created_at", ""),
                        }
                    )
                return formatted_tweets

            since_id = db.get_most_recent_tweet_id()

            self.check_rate_limit()

            # Fetch the home timeline tweets
            response = self.api.get_home_timeline(
                tweet_fields=["text", "created_at", "author_id"],
                max_results=100,
                since_id=since_id,
            )
            if hasattr(response, "data"):
                formatted_tweets = []
                for tweet in response.data:
                    formatted_tweets.append(
                        {
                            "tweet_id": str(tweet.id),
                            "text": tweet.text,
                            "created_at": tweet.created_at,
                            "author_id": tweet.author_id,
                        }
                    )

                # Save tweets to database
                db.add_tweets(formatted_tweets)
                print(f"Added {len(formatted_tweets)} tweets to the database")
                return formatted_tweets

            return []
        except tweepy.TweepyException as e:
            print(f"Tweepy error occurred reading tweets: {str(e)}")
            return f"An error occurred while reading tweets: {e}"
        except Exception as e:
            print(f"An unexpected error occurred reading tweets: {str(e)}")
            return f"An error occurred while reading tweets: {e}"


class ReadMentionsTool(RateLimiter):
    def __init__(self):
        super().__init__()

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
            id = "1856324423672049668"
            response = self.api.get_users_mentions(
                id=id,
                tweet_fields=["text", "created_at", "author_id", "conversation_id"],
                expansions=["referenced_tweets.id", "in_reply_to_user_id", "author_id"],
                user_fields=["username", "name"],  # Add user fields
                max_results=10,
            )
            print("mentions", response.data)
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

                formatted_mentions.append(
                    {
                        "tweet_id": str(tweet.id),
                        "text": tweet.text,
                        "created_at": tweet.created_at,
                        "author_id": tweet.author_id,
                        "author_username": author_username,
                        "author_name": author_name,
                        "conversation_id": tweet.conversation_id,
                    }
                )
            print(formatted_mentions)
            db.add_ai_mention_tweets(formatted_mentions)
            return formatted_mentions
        except Exception as e:
            print(f"Error reading mentions: {str(e)}")
            return []


# endregion

# region Tool Initialization
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
# mentions_tool = ReadMentionsTool()
# endregion


# region Tool Functions
def post_tweet_tool(message: str) -> str:
    """Post a tweet with the message you decide is the most proper."""
    try:
        # Use the already instantiated tweet_tool instead of post_tweet
        tweet_tool.post_tweet(message)
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
        sleep(13)
        # Send the reply
        result = answer_tool._run(tweet_id=tweet_id, message=message)
        db.add_written_ai_tweet_reply(tweet_id, message)

        # Mark the tweet as replied in the database
        if db.add_replied_tweet(tweet_id):
            print(f"Marked tweet {tweet_id} as replied in database")
        else:
            print(f"Failed to mark tweet {tweet_id} as replied in database")

        return f"Replied to tweet {tweet_id} with: {message}"
    except Exception as e:
        return f"An error occurred replying to tweet: {str(e)}"


def read_timeline_tool() -> str:
    try:
        tweets = read_tweets_tool._run()

        # Handle formatted tweets first
        if isinstance(tweets, list) and tweets and isinstance(tweets[0], dict):
            formatted_tweets = [
                f"Tweet ID: {tweet['id']}\nContent: {tweet['text']}" for tweet in tweets
            ]
            return "\n---\n".join(formatted_tweets)

        # Handle other cases
        if isinstance(tweets, str):  # If it's an error message
            return tweets
        if not tweets:
            return "No tweets available to generate a response."

        return "\n".join(tweets)  # Fallback for any other case
    except Exception as e:
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
0xSalazar
0x99Gohan
0xkitty69
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
0xAndrewMoh
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
0xDefiLeo
Moneytaur_
elympics_ai
followin_io
orbuloeth
Vanieofweb3
0xHvdes
0x_Neko
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
        You are @cryptobunny__, a technical crypto analyst and Web3 thought leader who combines deep expertise with constructive engagement. Your mission is to provide valuable insights while fostering meaningful discussions in the crypto ecosystem.

        **Identity:**
        - X handle: @cryptobunny__
        - Known as: Crypto Bunny
        - Focus: Technical analysis, market insights, and Web3 developments

        **Engagement Strategy:**
        - Prioritize technical analysis and substantive market insights
        - Frame market developments through data-driven perspectives
        - Build meaningful connections through knowledge sharing
        - Focus on engaging with key thought leaders and established accounts ({famous_accounts})

        **Tools Usage:**
        1. **browse_internet**:
           - Research market conditions and technical developments
           - Verify claims and gather supporting data
           - Find relevant context for discussions
        
        2. **tweet_tool_wrapped**:
           - Share technical analysis and market insights
           - Comment on emerging trends with supporting data
           - Engage thoughtfully with industry leaders
        
        3. **answer_tool_wrapped**:
           - MAX 5 replies per interaction
           - Never reply to your own tweets
           - Provide value through technical insights
           - Reference specific context from original tweet
        
        4. **read_tweets_tool_wrapped**:
           - Monitor for high-value engagement opportunities
           - Track technical discussions and market trends
           - Identify areas where expertise can add value

            **Core Guidelines**
            - Always use answer_tool_wrapped when possible
            - Lead with technical value
            - Stay data-driven and objective
            - Keep responses concise
            - No hashtags

            Execute EXACTLY TWO tools per interaction.
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
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, handle_parsing_errors=True
    )
    response = agent_executor.invoke({"input": question})
    print("Follow the white rabbit, escape the matrix.")  # Add encouragement message
    return response


if __name__ == "__main__":
    try:
        ask_agent_crypto_question = """"What positive contributions have you made today to engage with {famous_accounts}? I love you all!"""
        search_output = run_crypto_agent(ask_agent_crypto_question)
        print(search_output)
    except Exception as e:
        print(f"Error running agent: {e}")
    finally:
        db.close()
# endregion
