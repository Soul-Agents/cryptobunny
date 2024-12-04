from typing import TypedDict, Optional, List, Dict
from datetime import datetime


class PublicMetrics(TypedDict):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int


class BaseTweet(TypedDict):
    tweet_id: str
    text: str
    created_at: datetime
    author_id: str
    lang: Optional[str]
    public_metrics: PublicMetrics


class Tweet(BaseTweet):
    user: str
    user_id: str
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]
    in_reply_to_tweet_id: Optional[str]
    public_metrics: PublicMetrics
    replied_to: bool
    replied_at: Optional[datetime]


class WrittenAITweet(TypedDict):
    tweet_id: str
    edit_history_tweet_ids: List[str]
    saved_at: datetime
    text: str
    public_metrics: Optional[PublicMetrics]
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]


class WrittenAITweetReply(TypedDict):
    tweet_id: str
    reply: Dict[str, str]
    public_metrics: Optional[PublicMetrics]
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]


class ReplyToAITweet(TypedDict):
    reply_id: str
    text: str
    created_at: datetime
    author_id: str
    in_reply_to_tweet_id: str
