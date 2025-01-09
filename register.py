import firebase_admin
from firebase_admin import credentials, auth, firestore
import snowflake.connector
import os
from dotenv import load_dotenv
import json
load_dotenv()

class UserRegistration:
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
        self.cred = credentials.Certificate(self.firebase_credentials)
        firebase_admin.initialize_app(self.cred)
        self.db = firestore.client()
        self.conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE")
        )
        self.cursor = self.conn.cursor()

    def register_user(self, email, password, additional_data):
        try:
            user = auth.create_user(email=email, password=password)
            print(f"User created successfully: {user.uid}")

            self.create_tables(user.uid)
            self.create_cortexsearch(user.uid)

            self.db.collection('User_info').document(user.uid).set(additional_data)
            print("Additional user data stored in Firestore.")
        except Exception as e:
            print(f"Error creating user: {e}")

    def create_tables(self, user_id):
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {user_id}_pdf (
            id INT PRIMARY KEY,
            content STRING
            );"""
        self.cursor.execute(create_table_query)
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {user_id}_github (
            id INT PRIMARY KEY,
            content STRING
            );"""
        self.cursor.execute(create_table_query)
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {user_id}_rag (
            id INT PRIMARY KEY,
            content STRING
            );"""
        self.cursor.execute(create_table_query)

    def create_cortexsearch(self, user_id):
        create_table_query = f"""
            CREATE OR REPLACE CORTEX SEARCH SERVICE {user_id}_pdfsearch
            ON content
            WAREHOUSE = '{os.getenv("SNOWFLAKE_WAREHOUSE")}'
            TARGET_LAG = '10 minutes'
            EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
            AS (
                SELECT
                content
                FROM {user_id}_pdf
                );"""
        self.cursor.execute(create_table_query)

        create_table_query = f"""
            CREATE OR REPLACE CORTEX SEARCH SERVICE {user_id}_githubsearch
            ON content
            WAREHOUSE = '{os.getenv("SNOWFLAKE_WAREHOUSE")}'
            TARGET_LAG = '10 minutes'
            EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
            AS (
                SELECT
                content
                FROM {user_id}_github
                );"""
        self.cursor.execute(create_table_query)

        create_table_query = f"""
            CREATE OR REPLACE CORTEX SEARCH SERVICE {user_id}_ragsearch
            ON content
            WAREHOUSE = '{os.getenv("SNOWFLAKE_WAREHOUSE")}'
            TARGET_LAG = '10 minutes'
            EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
            AS (
                SELECT
                content
                FROM {user_id}_pdf
                );"""
        self.cursor.execute(create_table_query)
        self.cursor.close()
        self.conn.close()

if __name__ == "__main__":
    email = "babloo23@gmail.com"
    password = "babloo123"
    additional_data = {
        "name": "babloo",
        "age": 10000,
        "weight": 10,
        "gender": "TransMale"
    }

    user_registration = UserRegistration()
    user_registration.register_user(email, password, additional_data)

