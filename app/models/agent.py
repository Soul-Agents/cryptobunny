from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

class AgentConfig:
    """Model for agent configuration data"""
    
    def __init__(
        self,
        client_id: str,
        user_id: str = "",
        user_name: str = "",
        user_personality: str = "",
        style_rules: str = "",
        content_restrictions: str = "",
        strategy: str = "",
        remember: str = "",
        mission: str = "",
        questions: List[str] = None,
        engagement_strategy: str = "",
        knowledge_base: str = "",
        accounts_to_follow: List[str] = None,
        thought_leaders: List[str] = None,
        model_config: Dict[str, Any] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        is_active: bool = True,
        example_tweets: List[str] = None,
        # Payment related fields
        is_paid: bool = False,
        payment_amount: float = 0.0,
        payment_date: Optional[datetime] = None,
        payment_id: str = "",
        approval_mode: str = "automatic"  # 'automatic' | 'manual'
    ):
        self.client_id = client_id
        self.user_id = user_id
        self.user_name = user_name
        self.user_personality = user_personality
        self.style_rules = style_rules
        self.content_restrictions = content_restrictions
        self.strategy = strategy
        self.remember = remember
        self.mission = mission
        self.questions = questions or []
        self.engagement_strategy = engagement_strategy
        self.accounts_to_follow = accounts_to_follow or []
        self.thought_leaders = thought_leaders or []
        self.knowledge_base = knowledge_base
        self.model_config = model_config or {
            "type": "gpt-4",
            "temperature": 0.7,
            "top_p": 0.9,
            "presence_penalty": 0.6,
            "frequency_penalty": 0.6,
        }
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.is_active = is_active
        self.example_tweets = example_tweets or []
        # Payment related fields
        self.is_paid = is_paid
        self.payment_amount = payment_amount
        self.payment_date = payment_date
        self.payment_id = payment_id
        self.approval_mode = approval_mode
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary for database storage"""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_personality": self.user_personality,
            "style_rules": self.style_rules,
            "content_restrictions": self.content_restrictions,
            "strategy": self.strategy,
            "remember": self.remember,
            "mission": self.mission,
            "questions": self.questions,
            "engagement_strategy": self.engagement_strategy,
            "accounts_to_follow": self.accounts_to_follow,
            "thought_leaders": self.thought_leaders,
            "knowledge_base": self.knowledge_base,
            "model_config": self.model_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "example_tweets": self.example_tweets,
            # Payment related fields
            "is_paid": self.is_paid,
            "payment_amount": self.payment_amount,
            "payment_date": self.payment_date,
            "payment_id": self.payment_id,
            "approval_mode": self.approval_mode
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Create an AgentConfig instance from a dictionary"""
        return cls(
            client_id=data.get("client_id"),
            user_id=data.get("user_id"),
            user_name=data.get("user_name"),
            user_personality=data.get("user_personality", ""),
            style_rules=data.get("style_rules", ""),
            content_restrictions=data.get("content_restrictions", ""),
            strategy=data.get("strategy", ""),
            remember=data.get("remember", ""),
            mission=data.get("mission", ""),
            questions=data.get("questions", []),
            engagement_strategy=data.get("engagement_strategy", ""),
            accounts_to_follow=data.get("accounts_to_follow", []),
            thought_leaders=data.get("thought_leaders", []),
            knowledge_base=data.get("knowledge_base", ""),
            model_config=data.get("model_config", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_active=data.get("is_active", True),
            example_tweets=data.get("example_tweets", []),
            # Payment related fields
            is_paid=data.get("is_paid", False),
            payment_amount=data.get("payment_amount", 0.0),
            payment_date=data.get("payment_date"),
            payment_id=data.get("payment_id", ""),
            approval_mode=data.get("approval_mode", "automatic")
        ) 