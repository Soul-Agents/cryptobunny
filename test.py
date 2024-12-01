from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get credentials from environment variables
API_KEY = os.getenv("API_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

# Print credentials (with partial masking for security)
print("Credentials loaded:")
print(f"API_KEY: {API_KEY[:4]}...{API_KEY[-4:] if API_KEY else 'None'}")
print(f"API_SECRET_KEY: {API_SECRET_KEY[:4]}...{API_SECRET_KEY[-4:] if API_SECRET_KEY else 'None'}")
print(f"ACCESS_TOKEN: {ACCESS_TOKEN[:4]}...{ACCESS_TOKEN[-4:] if ACCESS_TOKEN else 'None'}")
print(f"ACCESS_TOKEN_SECRET: {ACCESS_TOKEN_SECRET[:4]}...{ACCESS_TOKEN_SECRET[-4:] if ACCESS_TOKEN_SECRET else 'None'}")

oauth = OAuth1Session(
    client_key=API_KEY,
    client_secret=API_SECRET_KEY,
    resource_owner_key=ACCESS_TOKEN,
    resource_owner_secret=ACCESS_TOKEN_SECRET,
)

print("\nOAuth session created:", oauth is not None)