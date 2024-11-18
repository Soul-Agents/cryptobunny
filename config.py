import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    @staticmethod
    def _get_env_var(name: str) -> str:
        value = os.getenv(name)
        if value is None:
            raise ValueError(f"Environment variable {name} is not set")
        return value

    API_KEY = _get_env_var("API_KEY")
    API_SECRET_KEY = _get_env_var("API_SECRET_KEY")
    BEARER_TOKEN = _get_env_var("BEARER_TOKEN")
    ACCESS_TOKEN = _get_env_var("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = _get_env_var("ACCESS_TOKEN_SECRET")
    OPENAI_API_KEY = _get_env_var("OPENAI_API_KEY")
    TAVILY_API_KEY = _get_env_var("TAVILY_API_KEY")