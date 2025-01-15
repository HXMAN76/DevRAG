import pyrebase
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import snowflake.connector
import threading

class FirebaseSnowflakeAuth:
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

    def _get_snowflake_connection(self):
        """Create and return a Snowflake connection"""
        return snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE")
        )

    def _setup_snowflake_resources(self, user_id):
        """Set up Snowflake tables and search services for a user"""
        try:
            conn = self._get_snowflake_connection()
            cursor = conn.cursor()

            # Create tables
            tables = ['pdf', 'github', 'rag']
            for table in tables:
                create_table_query = f"""
                    CREATE TABLE IF NOT EXISTS {user_id}_{table} (
                    id INT PRIMARY KEY,
                    content STRING
                    );"""
                cursor.execute(create_table_query)

            # Create search services
            for service in tables:
                create_search_query = f"""
                    CREATE OR REPLACE CORTEX SEARCH SERVICE {user_id}_{service}search
                    ON content
                    WAREHOUSE = '{os.getenv("SNOWFLAKE_WAREHOUSE")}'
                    TARGET_LAG = '10 minutes'
                    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
                    AS (
                        SELECT content
                        FROM {user_id}_{service}
                    );"""
                cursor.execute(create_search_query)

            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error setting up Snowflake resources: {e}")

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
            
            # Start Snowflake setup in background thread
            threading.Thread(
                target=self._setup_snowflake_resources,
                args=(user['localId'],),
                daemon=True
            ).start()
            
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