import streamlit as st
import base64
import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
import re
from datetime import datetime
import snowflake.connector
import threading
import requests
import time
import json
import toml

class FirebaseAuth:
    def __init__(self):
        with open('secrets.toml', 'r') as file:
            self.secret = toml.load(file)
        if not firebase_admin._apps:
            cred = credentials.Certificate({
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
            })
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
        self.api_key = self.secret["FIREBASE"]["API_KEY"]

    # Methods for Snowflake connections, login, registration, password reset, etc., as defined earlier
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
        
class BasePage:
    def __init__(self):
        self.load_styles()

    def load_styles(self):
        with open('static/login.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


class LoginPage(BasePage):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def validate_input(self, email, password=None):
        errors = []
        if not email:
            errors.append("Email is required")
        elif not self.auth.validate_email(email):
            errors.append("Invalid email format")

        if password is not None:
            if not password:
                errors.append("Password is required")
            elif not self.auth.validate_password(password):
                errors.append("Password must be at least 6 characters")

        return errors

    def show(self):
        st.subheader("Login", anchor=False)
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

            if submit:
                errors = self.validate_input(email, password)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        user_id = self.auth.login_user(email, password)
                        st.session_state.user_id = user_id
                        st.success("Login successful!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forgot Password?", key="forgot-password"):
                st.session_state.current_page = 'forgot_password'
                st.rerun()
        with col2:
            if st.button("New User? Sign Up", key="new-user"):
                st.session_state.current_page = 'signup'
                st.rerun()


class SignupPage(BasePage):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def validate_input(self, email, password=None):
        errors = []
        if not email:
            errors.append("Email is required")
        elif not self.auth.validate_email(email):
            errors.append("Invalid email format")

        if password is not None:
            if not password:
                errors.append("Password is required")
            elif not self.auth.validate_password(password):
                errors.append("Password must be at least 6 characters")

        return errors

    def show(self):
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
                errors = self.validate_input(email, password)
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
                            "description": description
                        }
                        user_id = self.auth.register_user(email, password, additional_data)
                        st.success("Registration successful! Snowflake resources are being set up in the background.")
                        st.info("You can proceed to login while we complete the setup.")
                        time.sleep(2)
                        st.session_state.current_page = 'login'
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if st.button("Already Registered? Login Now", key="back-to-login"):
            st.session_state.current_page = 'login'
            st.rerun()


class ForgotPasswordPage(BasePage):
    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def validate_input(self, email):
        errors = []
        if not email:
            errors.append("Email is required")
        elif not self.auth.validate_email(email):
            errors.append("Invalid email format")

        return errors

    def show(self):
        st.subheader("Reset Password", anchor=False)
        with st.form("forgot_password_form"):
            email = st.text_input("Email")
            submit = st.form_submit_button("Send Reset Link")

            if submit:
                errors = self.validate_input(email)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        self.auth.reset_password(email)
                        st.success("Password reset link sent to your email!")
                        time.sleep(2)
                        st.session_state.current_page = 'login'
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if st.button("Back to Login", key="back-to-login"):
            st.session_state.current_page = 'login'
            st.rerun()

class Landing:
    PAGE_TITLE = "DevRag"
    PAGE_ICON = "static/favicon-32.png"
    BG_IMAGE = "static/bg.jpg"

    def __init__(self):
        self.hide_dev_options()
        self.set_background(self.BG_IMAGE)
        self.load_custom_css()

    def hide_dev_options(self):
        st.markdown(
            """
            <style>
                header{
                    visibility: hidden;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

    def set_background(self, image_path):
        image_ext = "bg.jpg"
        st.markdown(
            f"""
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            <style>
            [data-testid="stMain"]{{
                background: url(data:image/{image_ext};base64,{base64.b64encode(open(image_path, "rb").read()).decode()});
                background-size: cover;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

    def load_custom_css(self):
        with open('static/styles.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def create_navbar(self):
        st.markdown("""
        <div class="navbar">
            <a href="#home">Home</a>
            <a href="#features">Features</a>
            <a href="#contact-us">Team</a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div id='home'></div>", unsafe_allow_html=True)

    def create_hero_section(self):
        st.title("Welcome to Dev", anchor=False)
        st.subheader(
            "Empowering developers with instant, AI-driven insights by combining "
            "Retrieval-Augmented Generation and dynamic web-scraped knowledge.",
            anchor=False
        )

        if st.button("Get Started ↗", key="get-started", type="primary"):
            st.session_state.current_page = "login"
            st.rerun()

    def create_features_section(self):
        st.markdown("<div id='features'></div>", unsafe_allow_html=True)
        st.header("Features", anchor=False)
        st.markdown("""
        <ul class="features-list">
            <li><strong>Accurate Insights</strong>: Get precise answers from a vast database of developer documentation.</li>
            <li><strong>Customizable Knowledge Base</strong>: Add your own links to keep the knowledge base up-to-date.</li>
            <li><strong>Instant Responses</strong>: Chatbot interface provides quick and contextual answers.</li>
            <li><strong>Comprehensive Solutions</strong>: Solve coding challenges, understand frameworks, and stay updated with the latest tools.</li>
        </ul>
        """, unsafe_allow_html=True)

    def create_tech_stack_section(self):
        st.header("Tech Stack", anchor=False)
        st.markdown("""
        <div class="tech-stack">
            <img src="https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png" alt="streamlit_logo" style="width: 15%;height: 15%">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_Logo.svg/1280px-Snowflake_Logo.svg.png" alt="snowflake" id="snowflake" style="width: 20%;height: 20%;">
            <img src="https://static1.squarespace.com/static/65c726ca17f84d5307a0dda1/65da1a93a8e8634b664835c9/65f6a87476d8e45fc3010249/1711102391682/announcing-mistral.png?format=1500w" alt="mistral" style="width: 10%;height: 10%">
            <img src="https://ml.globenewswire.com/Resource/Download/3034f6cd-48c3-4b5e-bd7f-242dbaecaab4?size=2" alt="trulens" style="width: 8%;height: 8%">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1869px-Python-logo-notext.svg.png" alt="python" style="width: 8%;height: 8%">
            <img src="https://www.ichdata.com/wp-content/uploads/2017/06/2024070803153850.png" alt="fireBase" style="width: 15%;height: 15%">
        </div>
        """, unsafe_allow_html=True)

    def create_about_section(self):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("📚 Vast Knowledge Base", anchor=False)
            st.write("Access information from various programming languages, frameworks, and libraries.")

        with col2:
            st.subheader("🔍 Smart Code Search", anchor=False)
            st.write("Find relevant code snippets and examples quickly and efficiently.")

        with col3:
            st.subheader("💡 Intelligent Suggestions", anchor=False)
            st.write("Get context-aware recommendations and best practices for your code.")

        st.markdown("<br><hr id='hr-1'>", unsafe_allow_html=True)

    def create_team_section(self):
        st.markdown("<div id='contact-us'></div>", unsafe_allow_html=True)
        st.header("Team", anchor=False)

        profiles = [
            {"name": "Raghav", "role": "Frontend Developer", "image": "Raghav_profile.jpg", "linkedin": "https://www.linkedin.com/in/raghav--n/", "github": "https://github.com/Rag-795", "email": "balaji.saragesh@gmail.com"},
            {"name": "Dev Bala Saragesh", "role": "Backend Developer", "image": "saragesh.jpg", "linkedin": "https://www.linkedin.com/in/devbalasarageshbs/", "github": "https://github.com/dbsaragesh-bs", "email": "balaji.saragesh@gmail.com"},
            {"name": "Hari Heman", "role": "Backend Developer", "image": "Hari_Profile_Pic.jpg", "linkedin": "https://www.linkedin.com/in/hari-heman/", "github": "https://github.com/HXMAN76", "email": "hariheman76@gmail.com"},
            {"name": "SriRanjana", "role": "Backend Developer", "image": "Ranjana_Profile_Pic.jpg", "linkedin": "https://www.linkedin.com/in/sriranjana-chitraboopathy-50b88828a/", "github": "https://github.com/sriranjanac", "email": "sriranjanac@gmail.com"}
        ]

        for profile in profiles:
            self._create_profile_card(**profile)

    def _create_profile_card(self, name, role, image, linkedin, github, email):
        st.markdown(
            f"""<div class="card">
            <img class="profile-pic" src="https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/{image}" alt="placeholder">
            <p class="name">{name}</p>
            <p class="role">{role}</p>
            <div class="social-media-handles">
                <a href="{linkedin}"><i class="fa-brands fa-linkedin"></i></a>
                <a href="{github}"><i class="fa-brands fa-github"></i></a>
                <a href="mailto:{email}"><i class="fa-regular fa-envelope"></i></a>
            </div>
            </div>""",
            unsafe_allow_html=True
        )

    def create_footer_section(self):
        st.markdown("<br><hr id='hr-2'>", unsafe_allow_html=True)
        st.markdown("<span id='footer'>© 2025 DevRag. All rights reserved.</span>", unsafe_allow_html=True)

    def run(self):
        self.create_navbar()
        self.create_hero_section()
        self.create_about_section()
        self.create_features_section()
        self.create_tech_stack_section()
        self.create_team_section()
        self.create_footer_section()

class App:
    def __init__(self):
            
        # Initialize session state
        self.initialize_session_state()
        self.title = "DevRag"
        self.layout = "wide"
        self.handle_page_config()
        # Set page config once at the app level
        st.set_page_config(
            page_title=self.title,
            page_icon="static/favicon-32.png",
            layout=self.layout
        )
        # Initialize Authorization 
        self.auth = FirebaseAuth()
        # Initialize components without page config
        self.landing = Landing()
        self.login = LoginPage(self.auth)
        self.signup = SignupPage(self.auth)
        self.forgot_password = ForgotPasswordPage(self.auth)

    def handle_page_config(self):
        if st.session_state.current_page == 'landing':
            self.title = "DevRag"
            self.layout = "wide"
        elif st.session_state.current_page in ['login', 'signup', 'forgot_password']:
            self.title = "DevRag - Authentication"
            self.layout = "centered"
        elif st.session_state.current_page == 'chatbot':
            self.title = "DevRag - Chatbot"
            self.layout = "wide"

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

        # Redirect to DevRAG - chatbot if user is authenticated but on auth pages
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
            self.login.show()
        elif st.session_state.current_page == 'signup':
            self.signup.show()
        elif st.session_state.current_page == 'forgot_password':
            self.forgot_password.show()
        elif st.session_state.current_page == 'chatbot':
            self.chatbot.run()

        # Debug information (remove in production)
        # st.sidebar.write("Debug Info:")
        # st.sidebar.write(f"Current Page: {st.session_state.current_page}")
        # st.sidebar.write(f"User ID: {st.session_state.user_id}")
        # st.sidebar.write(f"Auth Status: {st.session_state.authentication_status}")

if __name__ == '__main__':
    app = App()
    app.run()