import pyrebase
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from dotenv import load_dotenv
import re
from datetime import datetime

class FirebaseAuth:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
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
        
        # Initialize Pyrebase
        self.firebase_config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "appId": os.getenv("FIREBASE_APP_ID"),
        }
        self.firebase = pyrebase.initialize_app(self.firebase_config)
        self.auth = self.firebase.auth()
        self.db = firestore.client()

    def validate_email(self, email):
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))

    def validate_password(self, password):
        """Validate password requirements"""
        return len(password) >= 6

    def login_user(self, email, password):
        """Login user with email and password"""
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            account_info = self.auth.get_account_info(user['idToken'])
            uid = account_info['users'][0]['localId']
            return uid
        except Exception as e:
            if 'INVALID_LOGIN_CREDENTIALS' in str(e):
                raise Exception("Invalid email or password")
            raise Exception("Login failed. Please try again.")

    def register_user(self, email, password, additional_data=None):
        """Register new user with email and password"""
        try:
            # Create user with email and password
            user = self.auth.create_user_with_email_and_password(email, password)
            
            # Store additional user information in Firestore
            if additional_data:
                user_data = {
                    'email': email,
                    'created_at': datetime.now(),
                    **additional_data
                }
                self.db.collection('user_data').document(user['localId']).set(user_data)
            
            return user['localId']
        except Exception as e:
            if 'EMAIL_EXISTS' in str(e):
                raise Exception("Email already registered")
            raise Exception("Registration failed. Please try again.")

    def reset_password(self, email):
        """Send password reset email"""
        try:
            self.auth.send_password_reset_email(email)
        except Exception as e:
            raise Exception("Failed to send reset email. Please check your email address.")

    def get_user_info(self, user_id):
        """Get user information from Firestore"""
        try:
            user_data = self.db.collection('user_data').document(user_id).get()
            return user_data.to_dict()
        except Exception as e:
            return None