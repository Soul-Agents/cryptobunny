from app.utils.db import get_db
from app.utils.encryption import decrypt_dict_values,SENSITIVE_FIELDS
import tweepy
def get_auth_data():
    db = get_db()
    auth_data = db.twitter_auth.find_one({"client_id": "did:privy:cmbv3ojvh01cil20ljffo1den"})
    # auth_data = db.twitter_auth.find_one({"client_id": "did:privy:cmacpwovo001vl50nwiqufsh3"})

    decrypted_auth_data = decrypt_dict_values(auth_data, SENSITIVE_FIELDS)
    print(decrypted_auth_data, "AUTH DATA")

    client = tweepy.Client(
        bearer_token=decrypted_auth_data["bearer_token"],
        consumer_key=decrypted_auth_data["api_key"],
        consumer_secret=decrypted_auth_data["api_secret_key"],
        access_token=decrypted_auth_data["access_token"],
        access_token_secret=decrypted_auth_data["access_token_secret"]
    )

    p = client.get_me()
    print(p, "P")
    return p

get_auth_data()




