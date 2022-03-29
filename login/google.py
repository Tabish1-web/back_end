from google.auth.transport import requests
from google.oauth2 import id_token

class Google:
    @staticmethod
    def validate(auth_token):
        info = id_token.verify_oauth2_token(auth_token, requests.Request())
        return info if 'accounts.google.com' == info['iss'] else "invalid token!"