# Import all required libraries
import streamlit as st
import base64
import firebase_admin
from firebase_admin import credentials, auth, firestore
import snowflake.connector
import threading
import requests
import time
import toml
from datetime import datetime
import re

class FirebaseAuth:
    def __init__(self):
        # Load environment variables from secrets.toml
        with open('secrets.toml') as f:
            self.secret = toml.load(f)
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            self.firebase_credentials = {
                "type": self.secret["FIREBASE"]["TYPE"],
                "project_id": self.secret["FIREBASE"]["PROJECT_ID"],
                "private_key_id": self.secret["FIREBASE"]["PRIVATE_KEY_ID"],
                "private_key": self.secret["FIREBASE"]["PRIVATE_KEY"].replace('\\n', '\n'),
                "client_email": self.secret["FIREBASE"]["CLIENT_EMAIL"],
                "client_id": self.secret["FIREBASE"]["CLIENT_ID"],
                "auth_uri": self.secret["FIREBASE"]["AUTH_URI"],
                "token_uri": self.secret["FIREBASE"]["TOKEN_URI"],
                "auth_provider_x509_cert_url": self.secret["FIREBASE"]["AUTH_PROVIDER_X509_CERT_URL"],
                "client_x509_cert_url": self.secret["FIREBASE"]["CLIENT_X509_CERT_URL"],
                "universe_domain": self.secret["FIREBASE"]["UNIVERSE_DOMAIN"]
            }
            cred = credentials.Certificate(self.firebase_credentials)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        self.api_key = self.secret["FIREBASE"]["API_KEY"]

    def _get_snowflake_connection(self):
        """Create and return a Snowflake connection"""
        return snowflake.connector.connect(
            user=self.secret["SNOWFLAKE"]["USER"],
            password=self.secret["SNOWFLAKE"]["PASSWORD"],
            account=self.secret['SNOWFLAKE']['ACCOUNT'],
            database=self.secret["SNOWFLAKE"]["DATABASE"],
            schema=self.secret["SNOWFLAKE"]["SCHEMA"],
            warehouse=self.secret["SNOWFLAKE"]["WAREHOUSE"]
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
                    WAREHOUSE = '{self.secret["SNOWFLAKE"]["WAREHOUSE"]}'
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
                if error_message:
                    raise Exception("Login Failed. Check the Credential")

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
                    **additional_data,
                    "past_converations": [],
                    "conversation_summary":[]
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

        """Send password reset email using Firebase Authentication REST API"""
        try:
            # Firebase Auth REST API endpoint for password reset
            reset_password_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={self.api_key}"
            
            # Request payload
            payload = {
                "requestType": "PASSWORD_RESET",
                "email": email
            }
            
            # Send the request to Firebase
            response = requests.post(reset_password_url, json=payload)
            data = response.json()
            
            # Check if the request was successful
            if response.status_code == 200:
                print(f"Password reset email sent to {email}")
            else:
                error_message = data.get('error', {}).get('message', 'Failed to send reset email')
                raise Exception(error_message)
        except requests.exceptions.RequestException:
            raise Exception("Network error. Please check your connection.")
        except Exception as e:
            raise Exception(f"Failed to send reset email. {str(e)}")

    def get_user_info(self, user_id):
        """Get user information from Firestore"""
        try:
            user_data = self.db.collection('user_data').document(user_id).get()
            return user_data.to_dict()
        except Exception as e:
            return None

class App:
    def __init__(self):
        # Set page config once at the app level
        st.set_page_config(
            page_title="DevRag",
            page_icon="static/favicon-32.png",
            layout="wide"
        )
        
        # Initialize session state
        self.initialize_session_state()
        
        # Initialize Firebase Auth
        self.auth = FirebaseAuth()
        
        # Initialize all components
        self.landing = Landing(skip_page_config=True)
        self.login = Login(self.auth, skip_page_config=True)
        self.signup = Signup(self.auth, skip_page_config=True)
        self.forgot_password = ForgotPassword(self.auth, skip_page_config=True)
        self.chatbot = Chatbot(skip_page_config=True)

    def initialize_session_state(self):
        """Initialize all required session state variables"""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'landing'
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = None

    def handle_navigation(self):
        """Handle navigation between pages based on session state"""
        # Reset page if user logs out
        if st.session_state.user_id is None and st.session_state.current_page not in ['landing', 'login', 'signup', 'forgot_password']:
            st.session_state.current_page = 'landing'
            st.rerun()

        # Redirect to chatbot if user is authenticated but on auth pages
        if (st.session_state.user_id is not None and 
            st.session_state.current_page in ['login', 'signup', 'forgot_password']):
            st.session_state.current_page = 'chatbot'
            st.rerun()

    def run(self):
        """Main application loop"""
        # Handle navigation first
        self.handle_navigation()
        
        # Route to appropriate page
        if st.session_state.current_page == 'landing':
            self.landing.run()
        elif st.session_state.current_page == 'login':
            self.login.run()
        elif st.session_state.current_page == 'signup':
            self.signup.run()
        elif st.session_state.current_page == 'forgot_password':
            self.forgot_password.run()
        elif st.session_state.current_page == 'chatbot':
            self.chatbot.run()

class Landing:
    def __init__(self, skip_page_config=False):
        self.load_styles()
        
    def load_styles(self):
        # Load custom CSS and set background
        with open('static/styles.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        self.set_background('static/bg.jpg')

    def set_background(self, image_path):
        with open(image_path, "rb") as f:
            encoded_img = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            [data-testid="stMain"] {{
                background: url(data:image/jpg;base64,{encoded_img});
                background-size: cover;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

    def run(self):
        # Your existing Landing page code here
        self.create_navbar()
        self.create_hero_section()
        self.create_features_section()
        self.create_tech_stack_section()
        self.create_team_section()
        self.create_footer_section()

class Login:
    def __init__(self, auth, skip_page_config=False):
        self.auth = auth
        self.load_styles()
        
    def load_styles(self):
        with open('static/login.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def run(self):
        st.subheader("Login", anchor=False)
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                try:
                    user_id = self.auth.login_user(email, password)
                    st.session_state.user_id = user_id
                    st.success("Login successful!")
                    time.sleep(1)
                    st.session_state.current_page = 'chatbot'
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forgot Password?"):
                st.session_state.current_page = 'forgot_password'
                st.rerun()
        with col2:
            if st.button("New User? Sign Up"):
                st.session_state.current_page = 'signup'
                st.rerun()

class Signup:
    def __init__(self, auth, skip_page_config=False):
        self.auth = auth
        self.load_styles()
        
    def load_styles(self):
        with open('static/login.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def run(self):
        st.subheader("\U0001F31F Ready to supercharge your development?", anchor=False)
        st.markdown("Sign up now to get full access to DevRag and boost your coding productivity!")
        
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            occupation = st.selectbox("Occupation", 
                ["Student", "Software Developer", "Data Scientist", "Researcher", 
                 "Teacher/Professor", "Business Professional", "Other"])
            description = st.text_area("Description")
            submit = st.form_submit_button("Sign Up")
            
            if submit:
                try:
                    additional_data = {
                        "name": name,
                        "occupation": occupation,
                        "description": description
                    }
                    user_id = self.auth.register_user(email, password, additional_data)
                    st.success("Registration successful!")
                    time.sleep(1)
                    st.session_state.current_page = 'login'
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

class ForgotPassword:
    def __init__(self, auth, skip_page_config=False):
        self.auth = auth
        self.load_styles()
        
    def load_styles(self):
        with open('static/login.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def run(self):
        st.subheader("Reset Password", anchor=False)
        with st.form("forgot_password_form"):
            email = st.text_input("Email")
            submit = st.form_submit_button("Send Reset Link")
            
            if submit:
                try:
                    self.auth.reset_password(email)
                    st.success("Password reset link sent to your email!")
                    time.sleep(1)
                    st.session_state.current_page = 'login'
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if st.button("Back to Login"):
            st.session_state.current_page = 'login'
            st.rerun()

class Chatbot:
    def __init__(self, skip_page_config=False):
        self.load_styles()
        
    def load_styles(self):
        # Add any specific styles for the chatbot interface
        st.markdown("""
            <style>
            /* Add your chatbot-specific styles here */
            </style>
        """, unsafe_allow_html=True)

    def run(self):
        st.title("DevRag Chatbot")
        # Add logout button in sidebar
        if st.sidebar.button("Logout"):
            st.session_state.user_id = None
            st.session_state.current_page = 'landing'
            st.rerun()
        
        # Your chatbot implementation here
        st.write("Chatbot interface will be implemented here")

if __name__ == '__main__':
    app = App()
    app.run()