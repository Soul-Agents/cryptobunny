from app.routes.auth import auth_bp
from app.routes.agent import agent_bp
from app.routes.twitter import twitter_bp
from app.routes.dashboard import dashboard_bp

__all__ = ['auth_bp', 'agent_bp', 'twitter_bp', 'dashboard_bp'] 