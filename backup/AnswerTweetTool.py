import tweepy
from typing import Type, Optional
from pydantic import BaseModel

# Define the input schema for the tool
class AnswerTweetInput(BaseModel):
    tweet_id: str
    message: str

class AnswerTweetTool:
    name: str = "Answer tweet"
    description: str = "Use this tool when you need to reply to a tweet"
    args_schema: Type[BaseModel] = AnswerTweetInput

    def __init__(self, API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET):
        # Initialize the Twitter API client
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
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

answer_tool = AnswerTweetTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# tweet_id = "1830327642488447259"
# reply_message = "GM QwQiao! 🐰 Crypto Bunny here! Always excited to see your insights! Let's keep building and learning together! 🚀"

# result = answer_tool._run(
#     tweet_id=tweet_id,
#     message=reply_message
# )
# print(result)