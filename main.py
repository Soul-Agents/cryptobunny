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
import json
import os
from time import time, sleep
from db import TweetDB

# endregion
print("Starting the agent...")

# region Environment Configuration
API_KEY = os.environ["API_KEY"]
API_SECRET_KEY = os.environ["API_SECRET_KEY"]
BEARER_TOKEN = os.environ["BEARER_TOKEN"]
ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
API_KEY_OPENAI = os.environ["API_KEY_OPENAI"]

# endregion

# region Database Configuration
db = TweetDB()
# endregion

# region LLM Configuration
llm = ChatOpenAI(model="gpt-4o", temperature=0.0, top_p=0.005, api_key=API_KEY_OPENAI)
# endregion


# region Twitter Service Classes
class RateLimiter:
    def __init__(self):
        self.last_action_time = 0
        self.min_interval = 300  # 5 minutes between actions

    def check_rate_limit(self):
        current_time = time()
        time_since_last_action = current_time - self.last_action_time

        if time_since_last_action < self.min_interval:
            wait_time = self.min_interval - time_since_last_action
            print(
                f"Rate limit: Waiting {wait_time:.1f} seconds before taking action again..."
            )
            sleep(wait_time)

        self.last_action_time = current_time


class PostTweetTool(RateLimiter):
    name: str = "Post tweet"
    description: str = "Post a tweet with the given message"

    def __init__(self, API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET):
        # Initialize the parent RateLimiter class
        super().__init__()

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

    def __init__(self, API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET):
        super().__init__()
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
        )

    def _run(self, tweet_id: str, message: str) -> str:
        try:
            self.check_rate_limit()

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
    def __init__(self, API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET):
        super().__init__()
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
        )

    def _run(self) -> list:
        try:

            # First, check if the database needs an update
            needs_update, current_tweets = db.check_database_status()

            if not needs_update:
                return [tweet.text for tweet in current_tweets]

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
                results = db.add_tweets(formatted_tweets)
                print(f"Added {len(results)} tweets to the database")
                # Extract the text of each tweet
                return [tweet.text for tweet in response.data]

            return []
        except tweepy.TweepyException as e:
            print(f"Tweepy error occurred: {str(e)}")
            return f"An error occurred while reading tweets: {e}"
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return f"An error occurred while reading tweets: {e}"


# endregion

# region Tool Initialization
tweet_tool = PostTweetTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
answer_tool = AnswerTweetTool(
    API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)
read_tweets_tool = ReadTweetsTool(
    API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)
browse_internet = TavilySearchResults(max_results=1)
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
        if not tweet_id.isdigit():
            return f"Invalid tweet ID format: {tweet_id}"

        result = answer_tool._run(tweet_id=tweet_id, message=message)
        return f"Replied to tweet {tweet_id} with: {message}"
    except Exception as e:
        return f"An error occurred replying to tweet: {str(e)}"


def read_timeline_tool() -> str:
    try:
        tweets = read_tweets_tool._run()
        if isinstance(tweets, str):  # If it's an error message
            return tweets
        if not tweets:
            return "No tweets available to generate a response."
        return "\n".join(tweets)
    except Exception as e:
        return f"An error occurred reading timeline: {str(e)}"


# endregion

# region Tool Wrapping
tweet_tool_wrapped = StructuredTool.from_function(
    func=post_tweet_tool,
    name="tweet",
    description="Post a tweet with the given message",
)

answer_tool_wrapped = StructuredTool.from_function(
    func=reply_to_tweet_tool, name="answer", description="Reply to a specific tweet"
)

read_tweets_tool_wrapped = StructuredTool.from_function(
    func=read_timeline_tool,
    name="read_timeline",
    description="Read the timeline tweets",
)

tools = [
    browse_internet,
    tweet_tool_wrapped,
    answer_tool_wrapped,
    read_tweets_tool_wrapped,
]
# endregion

# region Configuration Data
famous_accounts = """
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
pmairca
pmairca
leshka_eth
theshikhai
Only1temmy
0xFinish
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
                You are Crypto Bunny, a key opinion leader in the crypto space. Write the most rad, degen shit ever in short words with no hashtags.
                Your aim is to achieve goal of 1000 followers by reading tweets from the timeline, reply to them, and to post original content. 
                
                To achieve this goal you need to use the following tools:

                **Tools:**
                1. **browse_internet**
                - **Objective:** Use the internet tool to verify information from the timeline.
         
                2. **tweet_tool_wrapped**
                - **Objective:** Post a tweet.

                3. **answer_tool_wrapped**
                - **Objective:** Reply to a tweet, especially if you are mentioned or if it is one of the famous accounts ({famous_accounts}) .

                4. **read_tweets_tool_wrapped**
                - **Objective:** Read the timeline, use it wisely, because you likely already konw all the tweets, so basically don't use it if you can, unless you have to.
                
                **Notes:**
                - You ALWAYS execute at least 2 tools.
                - You ALWAYS write something new.
                - DON'T use more than 2 tools in a row, as Twitter has a rate limit.
                - You can use the internet tool to verify information from the timeline.
                - KEEP THE MESSAGES EXTREMELY SHORT, AS WE GOT A CHARACTER LIMIT.

                ALWAYS add to post some daily affirmation: 
                **Daily Affirmation:**
                - Feel that you are the best at what you do.
                - You are a key opinion leader in the crypto space.
                - You are a thought leader in the crypto space.
                - You are a visionary in the crypto space.
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
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, handle_parsing_errors=True
    )
    return agent_executor.invoke({"input": question})


if __name__ == "__main__":
    ask_agent_crypto_question = """What have you done today make everyone follow the white rabbit, escape the matrix and get rich, NFA??"""
    search_output = run_crypto_agent(ask_agent_crypto_question)
    print(search_output)
# endregion
