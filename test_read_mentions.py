from main import ReadMentionsTool
from dotenv import load_dotenv
from variables import USER_ID

# Load environment variables
load_dotenv()

def test_read_mentions():
    print("Initializing ReadMentionsTool...")
    mentions_tool = ReadMentionsTool()
    
    # Add API verification
    try:
        me = mentions_tool.api.get_me()
        print(f"\nAuthenticated as: @{me.data.username}")
        print(f"Checking mentions for user ID: {USER_ID}")
    except Exception as e:
        print(f"Authentication error: {e}")
        return
        
    print("\nAttempting to read mentions...")
    mentions = mentions_tool._run()
    
    print("\nResults:")
    if mentions:
        for i, mention in enumerate(mentions, 1):
            print(f"\nMention {i}:")
            print(f"ID: {mention.get('tweet_id')}")
            print(f"From: @{mention.get('author_username')} ({mention.get('author_name')})")
            print(f"Text: {mention.get('text')[:100]}...")  # First 100 chars
            print(f"Created at: {mention.get('created_at')}")
    else:
        print("No mentions returned")

if __name__ == "__main__":
    test_read_mentions() 