import streamlit as st
from firebase_auth import FirebaseAuth
import re

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
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    if 'current_form' not in st.session_state:
        st.session_state.current_form = 'login'
    if 'auth' not in st.session_state:
        st.session_state.auth = FirebaseAuth()

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
                        st.success("Login successful!")
                        # TODO: Redirect to main application
                    except Exception as e:
                        st.error(str(e))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forgot Password?", key="forgot-password"):
                st.session_state.current_form = 'forgot_password'
        with col2:
            if st.button("New User? Sign Up", key="new-user"):
                st.session_state.current_form = 'signup'
    
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
                        st.success("Registration successful! Please login.")
                        st.session_state.current_form = 'login'
                    except Exception as e:
                        st.error(str(e))
        
        if st.button("Already Registered? Login Now", key="back-to-login"):
            st.session_state.current_form = 'login'
    
    # Forgot Password Form
    elif st.session_state.current_form == 'forgot_password':
        st.subheader("Reset Password", anchor=False)
        with st.form("forgot_password_form"):
            email = st.text_input("Email")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submit = st.form_submit_button("Reset Password")
            
            if submit:
                errors = validate_input(email, new_password)
                if new_password != confirm_password:
                    errors.append("Passwords do not match")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    try:
                        st.session_state.auth.reset_password(email)
                        st.success("Password reset successful! Please login with your new password.")
                        st.session_state.current_form = 'login'
                    except Exception as e:
                        st.error(str(e))
        
        if st.button("Back to Login", key="back-to-login"):
            st.session_state.current_form = 'login'

if __name__ == "__main__":
    main()