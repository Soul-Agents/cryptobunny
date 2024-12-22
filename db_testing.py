from db import TweetDB
from datetime import datetime, timezone
import json
from typing import Dict, List


def generate_test_tweet(tweet_id: str, user_id: str) -> Dict:
    """Generate a test tweet with required fields"""
    return {
        "tweet_id": tweet_id,
        "user_id": user_id,
        "text": f"Test tweet {tweet_id}",
        "created_at": datetime.now(timezone.utc),
        "author_id": user_id,
        "public_metrics": {
            "retweet_count": 0,
            "reply_count": 0,
            "like_count": 0,
            "quote_count": 0,
        },
        "conversation_id": f"conv_{tweet_id}",
        "in_reply_to_user_id": None,
        "in_reply_to_tweet_id": None,
        "replied_to": False,
    }


def test_db_functions(user_id: str):
    """Test all database functions for a specific user ID"""
    results = {}

    try:
        with TweetDB() as db:
            print("\n=== Starting Database Function Tests ===\n")

            # Test 1: Add regular tweets
            print("Testing add_tweets...")
            test_tweets = [generate_test_tweet(f"test_{i}", user_id) for i in range(3)]
            add_result = db.add_tweets(user_id, test_tweets)
            results["add_tweets"] = add_result
            print(f"Add tweets result: {add_result}")

            # Test 2: Get all tweets
            print("\nTesting get_all_tweets...")
            all_tweets = db.get_all_tweets(user_id, limit=10)
            results["get_all_tweets"] = len(all_tweets)
            print(f"Retrieved {len(all_tweets)} tweets")

            # Test 3: Add and get AI mention tweets
            print("\nTesting AI mention tweets...")
            test_mentions = [
                generate_test_tweet(f"mention_{i}", user_id) for i in range(2)
            ]
            mention_result = db.add_ai_mention_tweets(user_id, test_mentions)
            results["add_ai_mention_tweets"] = mention_result

            mentions = db.get_ai_mention_tweets(user_id)
            results["get_ai_mention_tweets"] = len(mentions)
            print(
                f"AI mentions results: Added={mention_result}, Retrieved={len(mentions)}"
            )

            # Test 4: Test unreplied/replied tweets
            print("\nTesting unreplied/replied tweets...")
            unreplied = db.get_unreplied_tweets(user_id)
            results["unreplied_tweets"] = len(unreplied)

            # Mark one tweet as replied
            if unreplied:
                db.add_replied_tweet(user_id, unreplied[0]["tweet_id"])

            replied = db.get_replied_tweets(user_id)
            results["replied_tweets"] = len(replied)
            print(f"Unreplied tweets: {len(unreplied)}, Replied tweets: {len(replied)}")

            # Test 5: Written AI tweets
            print("\nTesting written AI tweets...")
            test_ai_tweet = {
                "tweet_id": "ai_test_1",
                "text": "AI generated test tweet",
                "created_at": datetime.now(timezone.utc),
                "public_metrics": {
                    "retweet_count": 0,
                    "reply_count": 0,
                    "like_count": 0,
                    "quote_count": 0,
                },
                "saved_at": datetime.now(timezone.utc),
            }
            ai_tweet_result = db.add_written_ai_tweet(user_id, test_ai_tweet)
            results["add_written_ai_tweet"] = ai_tweet_result

            last_ai_tweets = db.get_last_written_ai_tweets(limit=5)
            results["get_last_written_ai_tweets"] = len(last_ai_tweets)
            print(f"Written AI tweets results: {ai_tweet_result}")

            # Test 6: Database status
            print("\nTesting database status...")
            needs_update, current_tweets = db.check_database_status(user_id)
            results["database_status"] = {
                "needs_update": needs_update,
                "current_tweets": len(current_tweets),
            }
            print(
                f"Database status: Needs update={needs_update}, Current tweets={len(current_tweets)}"
            )

            # Test 7: Most recent tweet/mention IDs
            print("\nTesting most recent IDs...")
            recent_tweet_id = db.get_most_recent_tweet_id(user_id)
            recent_mention_id = db.get_most_recent_mention_id(user_id)
            results["most_recent_ids"] = {
                "tweet": recent_tweet_id,
                "mention": recent_mention_id,
            }
            print(f"Most recent tweet ID: {recent_tweet_id}")
            print(f"Most recent mention ID: {recent_mention_id}")

            print("\n=== Database Function Tests Completed ===\n")

            return results

    except Exception as e:
        print(f"Error during database testing: {e}")
        return {"error": str(e)}


if __name__ == "__main__":

    #  trinity id 1869824037465051137
    # Replace with actual user ID for testing
    TEST_USER_ID = "1869824037465051137"
    results = test_db_functions(TEST_USER_ID)
    print("\nTest Results Summary:")
    print(json.dumps(results, indent=2, default=str))
