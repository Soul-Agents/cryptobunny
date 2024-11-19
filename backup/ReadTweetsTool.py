import tweepy

class ReadTweetsTool:
    def __init__(self, API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET):
        # Initialize the Twitter API client
        self.api = tweepy.Client(
            consumer_key=API_KEY,
            consumer_secret=API_SECRET_KEY,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )

    def _run(self) -> list:
        try:
            # Fetch the home timeline tweets
            response = self.api.get_home_timeline(tweet_fields=['text'])
            if hasattr(response, 'data'):
                # Extract the text of each tweet
                return [tweet.text for tweet in response.data]
            return []
        except tweepy.TweepyException as e:
            print(f"Tweepy error occurred: {str(e)}")
            return f"An error occurred while reading tweets: {e}"
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return f"An error occurred while reading tweets: {e}"
     
read_tweets_tool = ReadTweetsTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# tweets = read_tweets_tool._run()
# for tweet in tweets:
#     print(tweet)