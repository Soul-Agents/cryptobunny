import tweepy.client
from app.utils.db import get_db
from main import set_global_agent_variables, run_crypto_agent
from app.utils.encryption import  decrypt_dict_values
import tweepy
import requests
SENSITIVE_FIELDS = ["api_key", "api_secret_key", "access_token", "access_token_secret"]
import base64

def generate_bearer_token(api_key, api_secret):
    # 1. Encode credentials
    key_secret = f"{api_key}:{api_secret}".encode('ascii')
    b64_encoded_key = base64.b64encode(key_secret).decode('ascii')

    # 2. Set headers
    headers = {
        "Authorization": f"Basic {b64_encoded_key}",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }

    # 3. Set body
    data = {
        "grant_type": "client_credentials"
    }

    # 4. Send request
    response = requests.post(
        "https://api.twitter.com/oauth2/token",  # or api.x.com if you're using a proxy
        headers=headers,
        data=data
    )

    # 5. Parse response
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("Error:", response.status_code, response.text)
        return None
def run_agent():


   
    db = get_db()
        
    # Get all active and paid agents
    active_agents = db.get_all_active_paid_agents()
    # print(active_agents, "active_agents")

    agent = active_agents[0]
    # print(agent, "agent")
    twitter_auth = db.get_twitter_auth(agent["client_id"])
    # print(twitter_auth, "twitter_auth")
    auth = db.get_twitter_auth(agent["client_id"])
    decrypted_auth = decrypt_dict_values(auth, SENSITIVE_FIELDS)
    API_KEY = decrypted_auth["api_key"]
    API_SECRET = decrypted_auth["api_secret_key"]
    ACCESS_TOKEN = decrypted_auth["access_token"]
    ACCESS_TOKEN_SECRET = decrypted_auth["access_token_secret"]
    # bearer_token = generate_bearer_token(api_key=API_KEY, api_secret=API_SECRET)
    # print("Bearer Token:", bearer_token)

    # print(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, "decrypted_auth")

    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
        # wait_on_rate_limit=True
    )

    # auth = tweepy.OAuth1UserHandler(
    #     API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
    # )
    # api = tweepy.API(auth)
    # rate_limit_status = api.rate_limit_status()

  

    # rate_limit_status = api.rate_limit_status()
    
    # print(rate_limit_status, "rate_limit_status")
    # search_limit = rate_limit_status['resources']['search']['/search/tweets']['limit']
    # user_lookup_limit = rate_limit_status['resources']['users']['/users/lookup']['limit']
    # user_lookup_limit = rate_limit_status['resources']['']['']
    
    # print(f"Search tweets limit: {search_limit}")
    # print(f"User lookup limit: {user_lookup_limit}")

   
    headers = {
    "Authorization": f"Bearer AAAAAAAAAAAAAAAAAAAAADqNbwEAAAAA80xdu8Vnki0t4Sb9d4XaGVvTEf4%3DAGodwVlu34XoVsIOWe88WcaAGodhcry2o3FbbVOrDmrJxK72RC"
    }
    res = requests.get("https://api.twitter.com/2/usage/tweets", headers=headers)
    print(res.json())
    # print(res.headers, "res")
    # print(res, "res")
    # print("Remaining requests:", res.headers.get("x-rate-limit-remaining"))
    # print("Limit:", res.headers.get("x-rate-limit-limit"))
    # print("Reset time:", res.headers.get("x-rate-limit-reset"))
    return "HEllo"
    # user = client.get_me(user_fields=["subscription_type", "subscription","location", "description", "created_at"])
    # print(user, "user")
    # print(user.data, "user data")
    # print(user.data.subscription_type, "user subscription type")
    # print(user.data.subscription, "user subscription")
    # print(user.data.location, "user location")
    # print(user.data.description, "user description")
    # print(user.data.created_at, "user created at")
    # auth = tweepy.OAuth1UserHandler(
    #     API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
    # )
    # print(api.get_settings(), "settings")
    # print(api.get_user(screen_name="sebastian_oldak"))

   
   



    # set_global_agent_variables(agent)
    # run_crypto_agent(agent)
    # agent_config = db.get_agent_config(agent["client_id"])
    # print(agent_config, "agent_config")
    
    
run_agent()

