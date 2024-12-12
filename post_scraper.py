from twikit import Client
import asyncio


async def authenticate_twitter():
    """Authenticate with Twitter using credentials."""
    try:
        # Create client instance
        client = Client()

        # Login using credentials
        await client.login(
            auth_info_1="username",
            auth_info_2="email",
            password="password",
        )
        print("Authentication successful!")
        await client.save_cookies()
        return client
    except Exception as e:
        print(f"Authentication Error: {str(e)}")
        return None


async def post_tweet(client, message):
    """Post a tweet with the given message"""
    try:

        # Create tweet
        tweet = await client.create_tweet(text=message)

        print(f"Tweet posted successfully! Tweet ID: {tweet.id}")
        return tweet
    except Exception as e:
        print(f"Error posting tweet: {str(e)}")
        return None


async def main():
    # Authenticate
    client = await authenticate_twitter()
    if not client:
        return

    # Example tweet
    tweet_message = "Wake up "

    # Post tweet
    await post_tweet(client, tweet_message)


if __name__ == "__main__":
    asyncio.run(main())
