import streamlit as st
import base64
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
import asyncio
import nest_asyncio
from backend import Backend
from concurrent.futures import ThreadPoolExecutor as ThreadpoolExecutor

class FirebaseAuth:
    def __init__(self):
        # with open('secrets.toml', 'r') as file:
        #     self.secret = toml.load(file)
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
                    "past_conversations": [],
                    "conversation_summary": []
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
        self.user_id = None

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
                        self.user_id = self.auth.login_user(email, password)
                        st.session_state.user_id = self.user_id
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
    def __init__(self):
        self.hide_dev_options()
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

    def load_custom_css(self):
        with open('static/styles.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def create_navbar(self):
        st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
        [data-testid="stMain"]{
            background: url(https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/bg.jpg);
            background-size: cover;
        }
        </style>
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
        st.markdown("""
        <div class="about-section">
            <div class="col1">
                <span class="title">📚 Vast Knowledge Base</span>
                <p>Access information from various programming languages, frameworks, and libraries.</p>
            </div>
            <div class="col2">
                <span class="title">🔍 Smart Code Search</span>
                <p>Find relevant code snippets and examples quickly and efficiently.</p>
            </div>
            <div class="col3">
                <span class="title">💡 Intelligent Suggestions</span>
                <p>Get context-aware recommendations and best practices for your code.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
        # col1, col2, col3 = st.columns(3)

        # with col1:
        #     st.subheader("📚 Vast Knowledge Base", anchor=False)
        #     st.write("Access information from various programming languages, frameworks, and libraries.")

        # with col2:
        #     st.subheader("🔍 Smart Code Search", anchor=False)
        #     st.write("Find relevant code snippets and examples quickly and efficiently.")

        # with col3:
        #     st.subheader("💡 Intelligent Suggestions", anchor=False)
        #     st.write("Get context-aware recommendations and best practices for your code.")

        st.html("<br><hr id='hr-1'>")

    def create_team_section(self):
        st.markdown("<div id='contact-us'></div>", unsafe_allow_html=True)
        st.header("Team", anchor=False)

        rag, dev, hari, ranjana = st.columns(4)

        rag.markdown(
            """<div class="card">
            <img class="profile-pic" src="https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/Raghav_profile.jpg" alt="placeholder">
            <p class="name">Raghav</p>
            <p class="role">Frontend Developer</p>
            <div class="social-media-handles">
                <a href="https://www.linkedin.com/in/raghav--n/"><i class="fa-brands fa-linkedin"></i></a>
                <a href="https://github.com/Rag-795"><i class="fa-brands fa-github"></i></a>
                <a href="mailto:raghavnagarjan23@gmail.com"><i class="fa-regular fa-envelope"></i></a>
            </div>
        </div>""" , unsafe_allow_html=True)

        dev.markdown(
            """<div class="card">
            <img class="profile-pic" src="https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/saragesh.jpg" alt="placeholder" style="width:150px">
            <p class="name">Dev Bala Saragesh</p>
            <p class="role">Backend Developer</p>
            <div class="social-media-handles">
                <a href="https://www.linkedin.com/in/devbalasarageshbs/"><i class="fa-brands fa-linkedin"></i></a>
                <a href="https://github.com/dbsaragesh-bs"><i class="fa-brands fa-github"></i></a>
                <a href="mailto:balaji.saragesh@gmail.com"><i class="fa-regular fa-envelope"></i></a>
            </div>
        </div>""" , unsafe_allow_html=True)

        hari.markdown(
            """<div class="card">
            <img class="profile-pic" src="https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/Hari_Profile_Pic.jpg" alt="placeholder">
            <p class="name">Hari Heman</p>
            <p class="role">Backend Developer</p>
            <div class="social-media-handles">
                <a href="https://www.linkedin.com/in/hari-heman/"><i class="fa-brands fa-linkedin"></i></a>
                <a href="https://github.com/HXMAN76"><i class="fa-brands fa-github"></i></a>
                <a href="mailto:hariheman76@gmail.com"><i class="fa-regular fa-envelope"></i></a>
            </div>
        </div>""" , unsafe_allow_html=True)

        ranjana.markdown(
            """<div class="card">
            <img class="profile-pic" src="https://raw.githubusercontent.com/HXMAN76/DevRAG/refs/heads/main/static/Ranjana_Profile_Pic.jpg" alt="placeholder">
            <p class="name">SriRanjana</p>
            <p class="role">Backend Developer</p>
            <div class="social-media-handles">
                <a href="https://www.linkedin.com/in/sriranjana-chitraboopathy-50b88828a/"><i class="fa-brands fa-linkedin"></i></a>
                <a href="https://github.com/sriranjanac"><i class="fa-brands fa-github"></i></a>
                <a href="mailto:sriranjanac@gmail.com"><i class="fa-regular fa-envelope"></i></a>
            </div>
        </div>""" , unsafe_allow_html=True)

    def create_footer_section(self):
        st.html("<br><hr id='hr-2'>")
        st.markdown("<span id='footer'>© 2025 DevRag. All rights reserved.</span>", unsafe_allow_html=True)

    def run(self):
        self.create_navbar()
        self.create_hero_section()
        self.create_about_section()
        self.create_features_section()
        self.create_tech_stack_section()
        self.create_team_section()
        self.create_footer_section()

class Chatbot:
    def __init__(self):
        self.load_custom_css()
        self.initialize_session_state()
        self.backend = Backend(st.session_state.user_id)
        nest_asyncio.apply()

    async def process_github_async(self, url: str):
        """Async function to process GitHub URL"""
        try:
            await self.backend.github_scraper(url)
            return True, None
        except Exception as e:
            return False, str(e)

    def run_async_in_thread(self, url: str):
        """Run async code in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success, error = loop.run_until_complete(self.process_github_async(url))
            return success, error
        finally:
            loop.close()

    def connect_to_snowflake(self):
        self.backend.snowflake_manager.connect() 

    def load_custom_css(self):
        # Load custom CSS styles
        with open('static/chatbot.css', 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def initialize_session_state(self):
        # Initialize session states
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "show_sidebar" not in st.session_state:
            st.session_state.show_sidebar = False
        if "sidebar_type" not in st.session_state:
            st.session_state.sidebar_type = None

    def handle_sidebar_input(self, input_type):
        with st.sidebar:
            st.title(f"Process {input_type}")
            if input_type == "PDF":
                uploaded_file = st.file_uploader("Upload PDF", type="pdf")
                if uploaded_file:
                    self.backend.pdf_scraper(uploaded_file)
                    st.success("PDF uploaded successfully!")
            elif input_type == "GitHub":
                github_input = st.text_input(f"Enter {input_type} URL")
                if github_input:
                    try:
                        with ThreadpoolExecutor() as executor:
                            future = executor.submit(self.run_async_in_thread, github_input)
                            success, error = future.result()
                        if success:
                            st.success(f"{input_type} Repository processed successfully!")
                        else:
                            st.error(f"Error processing {input_type} Repository: {error}")
                    except Exception as e:
                        st.error(f"Error processing {input_type} Repository: {str(e)}")
                    
            elif input_type == "Website":
                url_input = st.text_input(f"Enter {input_type} URL")
                if url_input:
                    st.success(f"{input_type} URL processed successfully!")
                    self.backend.web_crawler(url_input)
        return None

    def display_chat_history(self):
        # Display chat history with avatars
        for message in st.session_state.messages:
            avatar_url = "https://cdn-icons-png.flaticon.com/512/1144/1144760.png" if message["role"] == "user" else "https://cdn-icons-png.flaticon.com/512/4711/4711987.png"
            with st.chat_message(message["role"], avatar=avatar_url):
                st.write(message["content"])

    def handle_chat_input(self):
        with st.container(key="chat_input"):
            # Chat input
            with st.form("User query", border=False, clear_on_submit=True):
                user_query, send_button = st.columns([0.9, 0.1])
                prompt = user_query.text_input("Prompt", label_visibility="collapsed", placeholder="Ask your question...")
                submit_button = send_button.form_submit_button(label="ᯓ➤")

            col1, _ = st.columns([2, 3])
            with col1:
                web, github, pdf = st.columns(3)

                # Website button
                if web.button("🌐", key="web"):
                    st.session_state.show_sidebar = True
                    st.session_state.sidebar_type = "Website"
                    st.rerun()

                # GitHub button
                if github.button("Git", key="github"):
                    st.session_state.show_sidebar = True
                    st.session_state.sidebar_type = "GitHub"
                    st.rerun()

                # PDF button
                if pdf.button("🔗", key="pdf"):
                    st.session_state.show_sidebar = True
                    st.session_state.sidebar_type = "PDF"
                    st.rerun()

        # Handle sidebar display
        if st.session_state.show_sidebar:
            result = self.handle_sidebar_input(st.session_state.sidebar_type)
            # We'll handle the result processing later

        if prompt and submit_button:
            # Add user message to chat history with avatar
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "avatar": "https://cdn-icons-png.flaticon.com/512/1144/1144760.png"
            })
            with st.chat_message("user", avatar="https://cdn-icons-png.flaticon.com/512/1144/1144760.png"):
                st.write(prompt)

            # Add assistant message to chat history with avatar
            response = self.backend.query(prompt)
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "avatar": "https://cdn-icons-png.flaticon.com/512/4711/4711987.png"
            })
            with st.chat_message("assistant", avatar="https://cdn-icons-png.flaticon.com/512/4711/4711987.png"):
                st.write(response)

    def run(self):
        if st.session_state.snowflake_manager is None:
            from backend import SnowflakeManager
            print("Initializing SnowflakeManager...")
            st.session_state.snowflake_manager = SnowflakeManager(user_id=st.session_state.user_id)
            st.session_state.snowflake_manager.connect()

        st.title("User", anchor=False)
        self.display_chat_history()
        self.handle_chat_input()

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
        self.chatbot = Chatbot()
        self.snowflake_manager = None

    def handle_page_config(self):
        if st.session_state.current_page == 'landing':
            self.title = "DevRag"
            self.layout = "wide"
        elif st.session_state.current_page in ['login', 'signup', 'forgot_password']:
            self.title = "DevRag - Authentication"
            self.layout = "centered"
        elif st.session_state.current_page == 'chatbot':
            self.title = "DevRag - Chatbot"
            self.layout = "centered"

    def initialize_session_state(self):
        """Initialize all required session state variables"""
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'landing'
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None
        if 'authentication_status' not in st.session_state:
            st.session_state.authentication_status = None
        if 'snowflake_manager' not in st.session_state:
            st.session_state.snowflake_manager = None

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
