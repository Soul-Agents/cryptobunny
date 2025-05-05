from datetime import datetime, timezone
from typing import Dict, Any, Optional

class TwitterAuth:
    """Model for Twitter authentication data"""
    
    def __init__(
        self,
        client_id: str,
        user_id: str,
        username: str,
        api_key: str,
        api_secret_key: str,
        access_token: str,
        access_token_secret: str,
        bearer_token: str = "",
        has_agent_config: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.client_id = client_id
        self.user_id = user_id
        self.username = username
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.bearer_token = bearer_token
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.has_agent_config = has_agent_config
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary for database storage"""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "username": self.username,
            "api_key": self.api_key,
            "api_secret_key": self.api_secret_key,
            "bearer_token": self.bearer_token,
            "access_token": self.access_token,
            "access_token_secret": self.access_token_secret,
            "has_agent_config": self.has_agent_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TwitterAuth':
        """Create a TwitterAuth instance from a dictionary"""
        return cls(
            client_id=data.get("client_id"),
            user_id=data.get("user_id"),
            username=data.get("username"),
            api_key=data.get("api_key"),
            api_secret_key=data.get("api_secret_key"),
            bearer_token=data.get("bearer_token", ""),
            access_token=data.get("access_token"),
            access_token_secret=data.get("access_token_secret"),
            has_agent_config=data.get("has_agent_config", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def get_safe_data(self) -> Dict[str, Any]:
        """Return a dictionary with sensitive information removed"""
        return {
            "client_id": self.client_id,
            "user_id": self.user_id,
            "username": self.username,
            "has_agent_config": self.has_agent_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        } 