import requests
import base64
from app.utils.db import get_db
from app.utils.encryption import encrypt_dict_values
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
    


def save_bearer_token(bearer_token, client_id):
    db = get_db()
    encrypted = encrypt_dict_values({"bearer_token": bearer_token}, ["bearer_token"])
    encrypted_bearer_token = encrypted["bearer_token"]
    db.twitter_auth.update_one(
        {"client_id": client_id},
        {"$set": {"bearer_token": encrypted_bearer_token}}
    )
    return encrypted_bearer_token