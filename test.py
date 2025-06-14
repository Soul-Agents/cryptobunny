import os
from dotenv import load_dotenv

load_dotenv(override=True)


SESSION_ID = "crypto-agent-permanent-session"
MONGODB_URL = os.getenv("MONGODB_URL")
from langchain_community.chat_message_histories import MongoDBChatMessageHistory
def get_session_history(session_id: str) -> MongoDBChatMessageHistory:
    """Returns the chat history for a given session ID."""
    return MongoDBChatMessageHistory(
        session_id=session_id,
        connection_string=MONGODB_URL,
        database_name="agent_memory",
        collection_name="chat_histories"
    )


history = get_session_history(SESSION_ID)

print(history.messages)