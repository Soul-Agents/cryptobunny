
import os
import base64
import jwt
from functools import wraps
from flask import request, jsonify

VERIFICATION_KEY = os.getenv('VERIFICATION_KEY')
PRIVY_APP_ID = os.getenv('PRIVY_APP_ID')



def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            decodedKey = base64.b64decode(VERIFICATION_KEY).decode("utf-8")

            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({
                    "status": "error",
                    "message": "No authorization token provided"
                }), 401

            token = auth_header.replace("Bearer ", "")
            decoded = jwt.decode(
                token,
                decodedKey,
                issuer='privy.io',
                audience=PRIVY_APP_ID,
                algorithms=['ES256']
            )
            
            # Add the decoded token to the request context
            request.user = decoded
            
            # Check if the client_id in the URL matches the authenticated user
            client_id = kwargs.get('client_id')
            if client_id and client_id != decoded['sub']:
                return jsonify({
                    "status": "error",
                    "message": "Unauthorized: Token does not match requested client_id"
                }), 403
            
            return f(*args, **kwargs)
            
        except jwt.InvalidTokenError as e:
            return jsonify({
                "status": "error",
                "message": f"Invalid token: {str(e)}"
            }), 401
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Authentication error: {str(e)}"
            }), 500
    
    return decorated_function