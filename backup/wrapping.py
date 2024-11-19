from langchain_core.tools import StructuredTool
import json

tweet_tool = PostTweetTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
answer_tool = AnswerTweetTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
read_tweets_tool = ReadTweetsTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

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


tweet_tool_wrapped = StructuredTool.from_function(
    func=post_tweet_tool,
    name="tweet",
    description="Post a tweet with the given message"
)

answer_tool_wrapped = StructuredTool.from_function(
    func=reply_to_tweet_tool,
    name="answer",
    description="Reply to a specific tweet"
)

read_tweets_tool_wrapped = StructuredTool.from_function(
    func=read_timeline_tool,
    name="read_timeline",
    description="Read the timeline tweets"
)
