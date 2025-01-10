import pyrebase
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FirebaseAuth:
    def __init__(self):
        # Firebase configuration
        self.firebase_config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "appId": os.getenv("FIREBASE_APP_ID"),
        }

        # Initialize Firebase app
        self.firebase = pyrebase.initialize_app(self.firebase_config)
        self.auth = self.firebase.auth()

    def sign_in_user(self, email, password):
        try:
            # Sign in with email and password
            user = self.auth.sign_in_with_email_and_password(email, password)
            # Get user ID (UID)
            account_info = self.auth.get_account_info(user['idToken'])
            uid = account_info['users'][0]['localId']
            print(f"Successfully authenticated. User UID: {uid}")
            return uid
        except Exception as e:
            print(f"Authentication error: {e}")
            if 'INVALID_LOGIN_CREDENTIALS' in str(e):
                print("Invalid email or password. Please check your credentials.")
            return None

    def register_user(self, email, password):
        try:
            # Register a new user
            user = self.auth.create_user_with_email_and_password(email, password)
            print(f"User registered successfully with email: {email}")
            return user
        except Exception as e:
            print(f"Error during registration: {e}")
            return None


if __name__ == "__main__":
    firebase_auth = FirebaseAuth()

    # Register a new user (Optional: Uncomment to test user registration)
    # email = "newuser@example.com"
    # password = "securepassword123"
    # firebase_auth.register_user(email, password)

    # Sign in existing user
    email = "dbs@gmail.com"  # Replace with your test email
    password = "1234556"        # Replace with your test password
    user_id = firebase_auth.sign_in_user(email, password)
    if user_id:
        print(f"Authenticated User ID: {user_id}")
    else:
        print("Failed to authenticate user.")
