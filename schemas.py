from typing import TypedDict, Optional, List, Dict, Any
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
    quoted_tweet_id: Optional[str]
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


# New schema for Twitter authentication
class TwitterAuth(TypedDict):
    client_id: str  # Unique identifier for the client
    user_id: str  # Twitter user ID
    user_name: str  # Twitter username of owner account
    agent_name: str  # Twitter account name of agent
    api_key: str
    api_secret_key: str
    bearer_token: str
    access_token: str
    access_token_secret: str
    created_at: datetime
    updated_at: datetime


# Schema for Agent Configuration per client
class AgentConfig(TypedDict):
    client_id: str  # Unique identifier for the client
    agent_name: str  # Name of the agent (e.g., "BUNNY", "NEOAI", etc.)
    user_id: str  # Twitter user ID
    user_name: str  # Twitter username
    user_personality: str
    style_rules: str
    content_restrictions: str
    strategy: str
    remember: str
    mission: str
    questions: List[str]
    engagement_strategy: str
    ai_and_agents: List[str]
    web3_builders: List[str]
    defi_experts: List[str]
    thought_leaders: List[str]
    traders_and_analysts: List[str]
    knowledge_base: str
    model_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    example_tweets: List[str]
