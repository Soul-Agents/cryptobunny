from typing import TypedDict, Optional
from datetime import datetime


class BaseTweet(TypedDict):
    tweet_id: str
    text: str
    created_at: datetime
    author_id: int


class Tweet(BaseTweet):
    user: str
    user_id: str
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]
    in_reply_to_tweet_id: Optional[str]
    like_count: int
    reply_count: int
    retweet_count: int
    quote_count: int


class WrittenAITweet(BaseTweet):
    prompt: str
    model: str
    temperature: float
    max_tokens: int
    response_tweet_id: Optional[str]


class ReplyToAITweet(TypedDict):
    id: int
    text: str
    created_at: datetime
    author_id: str
    in_reply_to_tweet_id: int
