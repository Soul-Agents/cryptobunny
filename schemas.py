from typing import TypedDict, Optional, List, Dict
from datetime import datetime


class PublicMetrics(TypedDict):
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int


class Tweet(TypedDict):
    tweet_id: str
    text: str
    created_at: datetime
    author_id: str
    public_metrics: PublicMetrics
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]
    in_reply_to_tweet_id: Optional[str]
    replied_to: bool
    replied_at: Optional[datetime]


class WrittenAITweet(TypedDict):
    user_id: str
    tweet_id: str
    edit_history_tweet_ids: List[str]
    saved_at: datetime
    text: str
    public_metrics: Optional[PublicMetrics]
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]
    replied_to: Optional[bool]
    replied_at: Optional[datetime]


class WrittenAITweetReply(TypedDict):
    user_id: str
    tweet_id: str
    reply: Dict[str, str]
    public_metrics: Optional[PublicMetrics]
    conversation_id: Optional[str]
    in_reply_to_user_id: Optional[str]
    saved_at: Optional[datetime]


class ReplyToAITweet(TypedDict):
    user_id: str
    reply_id: str
    text: str
    created_at: datetime
    in_reply_to_tweet_id: str
    public_metrics: Optional[PublicMetrics]
