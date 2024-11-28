from requests_oauthlib import OAuth1Session
import json

class PostTweetTool:
    name: str = "Post tweet"
    description: str = "Post a tweet with the given message"

    def __init__(self, API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET):
        # Initialize OAuth1Session with credentials
        self.oauth = OAuth1Session(
            client_key=API_KEY,
            client_secret=API_SECRET_KEY,
            resource_owner_key=ACCESS_TOKEN,
            resource_owner_secret=ACCESS_TOKEN_SECRET
        )

    def post_tweet(self, message: str):
        try:
            # Prepare the payload
            payload = {"text": message}
            
            # Make the request to Twitter API v2
            response = self.oauth.post(
                "https://api.twitter.com/2/tweets",
                json=payload,
            )
            
            # Check response
            if response.status_code != 201:
                raise Exception(
                    "Request returned an error: {} {}".format(response.status_code, response.text)
                )
                
            print("Tweet posted successfully!")
            return response.json()
            
        except Exception as e:
            print(f"Error posting tweet: {str(e)}")
            return None

# Initialize the tool
tweet_tool = PostTweetTool(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# # Direct method
# test_message = "I love chilling in the sun, I am a bunny."
# tweet_tool.post_tweet(test_message)