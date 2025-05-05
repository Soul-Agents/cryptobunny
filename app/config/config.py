import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    # Flask configuration
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
    DEBUG = False
    TESTING = False
    
    # Twitter API configuration
    TWITTER_CALLBACK_URL = os.getenv("TWITTER_CALLBACK_URL", "http://localhost:8000/auth/callback")
    
    # Frontend URL for redirects after auth
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


# Configuration dictionary to easily switch between environments
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}

# Get the current configuration
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name[env] 