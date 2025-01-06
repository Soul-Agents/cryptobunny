from requests_oauthlib import OAuth1Session
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get API credentials from environment variables
consumer_key = os.getenv("API_KEY")
consumer_secret = os.getenv("API_SECRET_KEY")

# Verify we have the required credentials
if not consumer_key or not consumer_secret:
    raise ValueError("Missing API_KEY or API_SECRET_KEY in environment variables")

print(f"Using API key: {consumer_key[:8]}...")  # Show first 8 chars for verification

# Get request token
request_token_url = "https://api.twitter.com/oauth/request_token?oauth_callback=oob&x_auth_access_type=write"
oauth = OAuth1Session(consumer_key, client_secret=consumer_secret)

try:
    fetch_response = oauth.fetch_request_token(request_token_url)
except ValueError as e:
    print(f"Error with credentials: {str(e)}")
    print("Please verify your API_KEY and API_SECRET_KEY are correct")
    raise

resource_owner_key = fetch_response.get("oauth_token")
resource_owner_secret = fetch_response.get("oauth_token_secret")
print("Got OAuth token: %s" % resource_owner_key)

# Get authorization
base_authorization_url = "https://api.twitter.com/oauth/authorize"
authorization_url = oauth.authorization_url(base_authorization_url)
print("\nPlease go here and authorize: %s" % authorization_url)
verifier = input("\nPaste the PIN here: ")

# Get the access token
access_token_url = "https://api.twitter.com/oauth/access_token"
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=resource_owner_key,
    resource_owner_secret=resource_owner_secret,
    verifier=verifier,
)

try:
    oauth_tokens = oauth.fetch_access_token(access_token_url)

    # Print the new tokens (to be added to .env)
    print("\nAdd these tokens to your .env file:")
    print(f"ACCESS_TOKEN={oauth_tokens['oauth_token']}")
    print(f"ACCESS_TOKEN_SECRET={oauth_tokens['oauth_token_secret']}")

    print(
        "\nAuthorization successful! You can now use these tokens in your application."
    )

except Exception as e:
    print(f"Error getting access token: {str(e)}")
    raise
