import firebase_admin
from firebase_admin import credentials, auth, firestore
import snowflake.connector
import os
from dotenv import load_dotenv
import re

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
        try:
            cred = credentials.Certificate(self.firebase_credentials)
            firebase_admin.initialize_app(cred)
        except ValueError:
            # App already exists
            pass
        self.db = firestore.client()
        self.setup_snowflake_connection()

    def setup_snowflake_connection(self):
        self.conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE")
        )
        self.cursor = self.conn.cursor()

    def validate_email(self, email):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))

    def validate_password(self, password):
        return len(password) >= 6

    def login_user(self, email, password):
        try:
            user = auth.sign_in_email_and_password(email=email,password=password)
            # Note: Firebase Admin SDK doesn't verify passwords
            # In a production environment, you'd use Firebase Auth REST API
            return user.uid
        except Exception as e:
            raise Exception(f"Login failed: {str(e)}")

    def register_user(self, email, password, additional_data):
        try:
            user = auth.create_user(email=email, password=password)
            self.create_tables(user.uid)
            self.create_cortexsearch(user.uid)
            self.db.collection('User_info').document(user.uid).set(additional_data)
            return user.uid
        except Exception as e:
            raise Exception(f"Registration failed: {str(e)}")

    def reset_password(self, email):
        try:
            user = auth.get_user_by_email(email)
            # In production, use Firebase Auth REST API to send reset email
            return True
        except Exception as e:
            raise Exception(f"Password reset failed: {str(e)}")

    def create_tables(self, user_id):
        tables = ['pdf', 'github', 'rag']
        for table in tables:
            create_table_query = f"""
                CREATE TABLE IF NOT EXISTS {user_id}_{table} (
                id INT PRIMARY KEY,
                content STRING
                );"""
            self.cursor.execute(create_table_query)

    def create_cortexsearch(self, user_id):
        services = ['pdf', 'github', 'rag']
        for service in services:
            create_table_query = f"""
                CREATE OR REPLACE CORTEX SEARCH SERVICE {user_id}_{service}search
                ON content
                WAREHOUSE = '{os.getenv("SNOWFLAKE_WAREHOUSE")}'
                TARGET_LAG = '10 minutes'
                EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
                AS (
                    SELECT content
                    FROM {user_id}_{service}
                    );"""
            self.cursor.execute(create_table_query)

    def __del__(self):
        if hasattr(self, 'cursor'):
            self.cursor.close()
        if hasattr(self, 'conn'):
            self.conn.close()