# import os
# from dotenv import load_dotenv

from app.utils.db import get_db
# load_dotenv(override=True)


# SESSION_ID = "crypto-agent-permanent-session"
# MONGODB_URL = os.getenv("MONGODB_URL")
# from langchain_community.chat_message_histories import MongoDBChatMessageHistory
# def get_session_history(session_id: str) -> MongoDBChatMessageHistory:
#     """Returns the chat history for a given session ID."""
#     return MongoDBChatMessageHistory(
#         session_id=session_id,
#         connection_string=MONGODB_URL,
#         database_name="agent_memory",
#         collection_name="chat_histories"
#     )


# history = get_session_history(SESSION_ID)

# print(history.messages)



from datetime import datetime, timezone

def delete_fields_from_all_configs() -> dict:
    """Delete specified fields from all agent configurations"""
    
    try:
        db = get_db()
        # Get all configs
        all_configs = list(db.agent_config.find({}))
        
        if not all_configs:
            return {
                "status": "error",
                "message": "No agent configurations found"
            }
        
        fields_to_remove = ["web3_builders", "traders_and_analysts", "defi_experts"]
        results = []
        
        for config in all_configs:
            client_id = config["client_id"]
            print(f"\nProcessing client: {client_id}")
            
            # Store initial state for verification
            initial_fields = {field: config.get(field) for field in fields_to_remove if field in config}
            if initial_fields:
                print("Initial values:")
                for field, value in initial_fields.items():
                    print(f"{field}: {value}")
            
            # Update the document to remove specified fields
            result = db.agent_config.update_one(
                {"client_id": client_id},
                {
                    "$unset": {field: "" for field in fields_to_remove},
                    "$set": {"updated_at": datetime.now(timezone.utc)}
                }
            )
            
            # Verify the fields were removed
            updated_config = db.get_agent_config(client_id)
            fields_removed = all(field not in updated_config for field in fields_to_remove)
            
            results.append({
                "client_id": client_id,
                "fields_existed_before": list(initial_fields.keys()),
                "fields_removed": fields_removed,
                "result": result.modified_count > 0
            })
        
        return {
            "status": "success",
            "message": f"Processed {len(all_configs)} configurations",
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting fields: {str(e)}"
        }

# Example usage
if __name__ == "__main__":
    result = delete_fields_from_all_configs()
    print("\nOperation Result:")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result['status'] == 'success':
        print("\nDetailed Results:")
        for client_result in result['results']:
            print(f"\nClient ID: {client_result['client_id']}")
            print(f"Fields that existed before: {client_result['fields_existed_before']}")
            print(f"All fields were removed: {client_result['fields_removed']}")
            print(f"Update was successful: {client_result['result']}")