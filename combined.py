import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from dotenv import load_dotenv
import re
from datetime import datetime
import snowflake.connector
import threading
import requests
import json

# Configure Streamlit page
st.set_page_config(page_title="ChatBot Login", layout="centered")

# Custom CSS for styling
st.markdown("""
    <style>
    /* Main colors */
    :root {
        --primary-orange: #FF6B35;
        --secondary-orange: #FF8C61;
        --black: #2F2F2F;
    }
    
    /* Custom button styles */
    .st-key-login button,
    .st-key-signup button,
    .st-key-forgot-password button,
    .st-key-reset-password button,
    .st-key-back-to-login button {
        background-color: var(--primary-orange);
        color: white;
        border: none;
        width: 100%;
        padding: 8px 16px;
        border-radius: 5px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    
    .st-key-login button:hover,
    .st-key-signup button:hover,
    .st-key-forgot-password button:hover,
    .st-key-reset-password button:hover,
    .st-key-back-to-login button:hover {
        background-color: var(--secondary-orange);
    }
    
    .title {
        color: var(--black);
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .error-msg {
        color: red;
        font-size: 0.9em;
        margin-top: 0.5em;
    }
    
    .stTextInput > div > div > input {
        border-radius: 5px;
        border: 1px solid #ccc;
    }

    /* Loading spinner for background processes */
    .stSpinner {
        text-align: center;
        margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

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
        
        self.db = firestore.client()
        self.api_key = os.getenv("FIREBASE_API_KEY")
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
                    TARGET_LAG = '1 minutes'
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
        """Login user with email and password using Firebase Auth REST API"""
        try:
            # Firebase Auth REST API endpoint for email/password sign-in
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
            
            # Request payload
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            # Make the authentication request
            response = requests.post(auth_url, json=payload)
            data = response.json()
            
            # Check for errors
            if response.status_code != 200:
                error_message = data.get('error', {}).get('message', 'Authentication failed')
                if error_message == 'INVALID_PASSWORD':
                    raise Exception("Invalid password")
                elif error_message == 'EMAIL_NOT_FOUND':
                    raise Exception("Email not found")
                else:
                    raise Exception("Login failed. Please try again.")
            
            # Get the user ID from the response
            user_id = data.get('localId')
            if not user_id:
                raise Exception("Failed to get user information")
                
            return user_id
            
        except requests.exceptions.RequestException as e:
            raise Exception("Network error. Please check your connection.")
        except Exception as e:
            raise e

    def register_user(self, email, password, additional_data=None):
        """Register new user with email and password"""
        try:
            user = auth.create_user(
                email=email,
                password=password
            )
            
            # Store additional user information in Firestore
            if additional_data:
                user_data = {
                    'email': email,
                    'created_at': datetime.now(),
                    **additional_data
                }
                self.db.collection('user_data').document(user.uid).set(user_data)
            
            # Start Snowflake setup in background thread
            threading.Thread(
                target=self._setup_snowflake_resources,
                args=(user.uid,),
                daemon=True
            ).start()
            
            return user.uid
        except Exception as e:
            if 'EMAIL_EXISTS' in str(e):
                raise Exception("Email already registered")
            raise Exception("Registration failed. Please try again.")

    def reset_password(self, email):
        """Send password reset email"""
        try:
            # Generate password reset link
            link = auth.generate_password_reset_link(email)
            # In production, you'd send this link via email
            print(f"Password reset link: {link}")
        except Exception as e:
            raise Exception("Failed to send reset email. Please check your email address.")

    def get_user_info(self, user_id):
        """Get user information from Firestore"""
        try:
            user_data = self.db.collection('user_data').document(user_id).get()
            return user_data.to_dict()
        except Exception as e:
            return None

def initialize_session_state():
    if 'current_form' not in st.session_state:
        st.session_state.current_form = 'login'
    if 'auth' not in st.session_state:
        st.session_state.auth = FirebaseAuth()
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

def validate_input(email, password=None):
    errors = []
    if not email:
        errors.append("Email is required")
    elif not st.session_state.auth.validate_email(email):
        errors.append("Invalid email format")
    
    if password is not None:
        if not password:
            errors.append("Password is required")
        elif not st.session_state.auth.validate_password(password):
            errors.append("Password must be at least 6 characters")
    
    return errors

def main():
    initialize_session_state()
    
    if st.session_state.user_id is None:
        st.markdown("<h1 class='title'>ChatBot Assistant</h1>", unsafe_allow_html=True)
        
        # Login Form
        if st.session_state.current_form == 'login':
            st.subheader("Login", anchor=False)
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    errors = validate_input(email, password)
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        try:
                            user_id = st.session_state.auth.login_user(email, password)
                            st.session_state.user_id = user_id
                            st.success("Login successful!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Forgot Password?", key="forgot-password"):
                    st.session_state.current_form = 'forgot_password'
                    st.rerun()
            with col2:
                if st.button("New User? Sign Up", key="new-user"):
                    st.session_state.current_form = 'signup'
                    st.rerun()
        
        # Signup Form
        elif st.session_state.current_form == 'signup':
            st.subheader("Sign Up", anchor=False)
            with st.form("signup_form"):
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                occupation = st.text_input("Occupation")
                purpose = st.selectbox("Purpose of Use", 
                                     ["Personal", "Business", "Education", "Research", "Other"])
                description = st.text_area("Description")
                submit = st.form_submit_button("Sign Up")
                
                if submit:
                    errors = validate_input(email, password)
                    if not name:
                        errors.append("Name is required")
                    
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        try:
                            additional_data = {
                                "name": name,
                                "occupation": occupation,
                                "purpose": purpose,
                                "description": description
                            }
                            user_id = st.session_state.auth.register_user(email, password, additional_data)
                            st.success("Registration successful! Snowflake resources are being set up in the background.")
                            st.info("You can proceed to login while we complete the setup.")
                            st.session_state.current_form = 'login'
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            
            if st.button("Already Registered? Login Now", key="back-to-login"):
                st.session_state.current_form = 'login'
                st.rerun()
        
        # Forgot Password Form
        elif st.session_state.current_form == 'forgot_password':
            st.subheader("Reset Password", anchor=False)
            with st.form("forgot_password_form"):
                email = st.text_input("Email")
                submit = st.form_submit_button("Send Reset Link")
                
                if submit:
                    errors = validate_input(email)
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        try:
                            st.session_state.auth.reset_password(email)
                            st.success("Password reset link sent to your email!")
                            st.session_state.current_form = 'login'
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            
            if st.button("Back to Login", key="back-to-login"):
                st.session_state.current_form = 'login'
                st.rerun()
    
    else:
        # User is logged in
        st.title("Welcome!")
        user_info = st.session_state.auth.get_user_info(st.session_state.user_id)
        if user_info:
            st.write(f"Name: {user_info.get('name', 'N/A')}")
            st.write(f"Email: {user_info.get('email', 'N/A')}")
            st.write(f"Occupation: {user_info.get('occupation', 'N/A')}")
            st.write(f"Purpose: {user_info.get('purpose', 'N/A')}")
        
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.current_form = 'login'
            st.rerun()

if __name__ == "__main__":
    main()