import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import pyrebase
from dotenv import load_dotenv
load_dotenv()

class FirebaseAuth:
    def __init__(self):
        self.firebase_credentials = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
            "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
        }
        cred = credentials.Certificate(self.firebase_credentials)
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def get_user_id(self, email, password):
            try:
                user = auth.sign_in_email_and_password(email=email, password=password)
                return user.uid
            except Exception as e:
                print(f"Error creating user: {e}")
                return None

    def get_user_info_firestore(self, user_id):
        try:
            user_data = self.db.collection('user_data').document(user_id).get()
            return user_data.to_dict()
        except Exception as e:
            print(f"Error getting user data: {e}")
            return None

if __name__ == "__main__":
    email = "babloo23@gmail.com"
    password = "babloo123"
    firebase_auth = FirebaseAuth()
    user_id = firebase_auth.get_user_id(email, password)
    if user_id:
        print(f"User Id: {user_id}")
