import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from dotenv import load_dotenv
load_dotenv()

firebase_credentials = {
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

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)

db = firestore.client()

def get_user_id (email, password):
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def get_user_info_firestore(user_id):
    try:
        user_data = db.collection('user_data').document(user_id).get()
        return user_data.to_dict()
    except Exception as e:
        print(f"Error getting user data: {e}")
        return None
    
email = "babloo23@gmail.com"
password = "babloo123"
user_id = get_user_id(email, password)
if user_id:
    print(f"User Id: {get_user_id(email, password)}")
   