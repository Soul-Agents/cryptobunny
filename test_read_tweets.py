from main import ReadTweetsTool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_read_tweets():
    print("Initializing ReadTweetsTool...")
    read_tool = ReadTweetsTool()
    
    print("\nAttempting to read tweets...")
    tweets = read_tool._run()
    
    print("\nResults:")
    if tweets:
        for i, tweet in enumerate(tweets, 1):
            print(f"\nTweet {i}:")
            print(f"ID: {tweet.get('tweet_id')}")
            print(f"Text: {tweet.get('text')[:100]}...")  # First 100 chars
            print(f"Author ID: {tweet.get('author_id')}")
            print(f"Created at: {tweet.get('created_at')}")
    else:
        print("No tweets returned")

if __name__ == "__main__":
    test_read_tweets()
