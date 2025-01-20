import streamlit as st
import base64

# Constants
PAGE_TITLE = "DevRag"
PAGE_ICON = "static/favicon-32.png"
BG_IMAGE = "static/bg.jpg"

def setup_page_config():
    # Configure basic page settings
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide"
    )

def hide_dev_options():
    # Hide developer options from the UI
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

def set_background(image_path):
    # Set the background image for the page
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

def load_custom_css():
    # Load custom CSS styles
    with open('static/styles.css', 'r') as f:  # Move CSS to separate file
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def create_navbar():
    """Create the navigation bar"""
    st.markdown("""
    <div class="navbar">
        <a href="#home">Home</a>
        <a href="#about">About</a>
        <a href="#features">Features</a>
        <a href="#contact-us">Contact Us</a>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div id='home'></div>", unsafe_allow_html=True)

def create_hero_section():
    """Create the hero section with title and subtitle"""
    st.title("Welcome to Dev", anchor=False)
    st.subheader(
        "Empowering developers with instant, AI-driven insights by combining "
        "Retrieval-Augmented Generation and dynamic web-scraped knowledge.",
        anchor=False
    )
    if st.button("Get Started ↗", key="get-started", type="primary"):
        # st.session_state.current_page = 'chatbot'
        # st.rerun()
        st.html('<script>window.location.href = "http://localhost:8501/chatbot";</script>')

def create_features_section():
    """Create the features section"""
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

    st.markdown("""
     <marquee behavior="scroll" direction="left" scrollamount="6" loop="infinite" class="tech-stack">
        <img src="https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png" alt="streamlilt_logo" width="100%" style="width: 20%;height: 20%">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_Logo.svg/1280px-Snowflake_Logo.svg.png" alt="snowflake" style="width: 20%;height: 20%">
        <img src="https://upload.wikimedia.org/wikipedia/de/1/1c/Mistral_AI_logo.svg" alt="mistral" style="width: 10%;height: 10%">
        <img src="https://ml.globenewswire.com/Resource/Download/3034f6cd-48c3-4b5e-bd7f-242dbaecaab4?size=2" alt="trulens" style="width: 10%;height: 10%">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png" alt="python" style="width: 10%;height: 10%">  
    </marquee>
    """,unsafe_allow_html=True)

def create_about_section():
    """Create the about section"""
    st.markdown("<div id='about'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📚 Vast Knowledge Base",anchor=False)
        st.write("Access information from various programming languages, frameworks, and libraries.")

    with col2:
        st.subheader("🔍 Smart Code Search",anchor = False)
        st.write("Find relevant code snippets and examples quickly and efficiently.")

    with col3:
        st.subheader("💡 Intelligent Suggestions", anchor=False)
        st.write("Get context-aware recommendations and best practices for your code.")

    st.html("<br><hr id='hr-1'>")


def create_contact_section():
    """Create the contact section with profile card"""
    st.markdown("<div id='contact-us'></div>", unsafe_allow_html=True)
    st.header("Contact Us", anchor=False)
    
    # Profile card HTML
    # profile_card_html = """
    # <div class="card">
    #     <img class="profile-pic" src="https://placehold.co/200" alt="placeholder">
    #     <p class="name">Raghav</p>
    #     <p class="role">Frontend Developer</p>
    #     <div class="social-media-handles">
    #         <a href="#"><img src="static/icons8-linkedin-50.png" alt="linkedin"/></a>
    #         <a href="#"><img src="static/icons8-github-90.png" alt="github"/></a>
    #         <a href="#"><img src="static/icons8-gmail-50.png" alt="gmail"/></a>
    #     </div>
    # </div>
    # """

    rag, dev, hari, ranjana = st.columns(4)

    rag.markdown(
        """<div class="card">
        <img class="profile-pic" src="https://avatars.githubusercontent.com/u/161674308?v=4" alt="placeholder">
        <p class="name">Raghav</p>
        <p class="role">Frontend Developer</p>
        <div class="social-media-handles">
            <a href="#"><i class="fa-brands fa-linkedin"></i></a>
            <a href="#"><i class="fa-brands fa-github"></i></a>
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
        </div>
    </div>""" , unsafe_allow_html=True)

    dev.markdown(
        """<div class="card">
        <img class="profile-pic" src="https://placehold.co/200" alt="placeholder">
        <p class="name">Dev Bala Saragesh</p>
        <p class="role">Backend Developer</p>
        <div class="social-media-handles">
            <a href="#"><i class="fa-brands fa-linkedin"></i></a>
            <a href="#"><i class="fa-brands fa-github"></i></a>
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
        </div>
    </div>""" , unsafe_allow_html=True)

    hari.markdown(
        """<div class="card">
        <img class="profile-pic" src="https://placehold.co/200" alt="placeholder">
        <p class="name">Hari Heman</p>
        <p class="role">Backend Developer</p>
        <div class="social-media-handles">
            <a href="#"><i class="fa-brands fa-linkedin"></i></a>
            <a href="#"><i class="fa-brands fa-github"></i></a>
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
        </div>
    </div>""" , unsafe_allow_html=True)

    ranjana.markdown(
        """<div class="card">
        <img class="profile-pic" src="https://placehold.co/200" alt="placeholder">
        <p class="name">SriRanjana</p>
        <p class="role">Backend Developer</p>
        <div class="social-media-handles">
            <a href="#"><i class="fa-brands fa-linkedin"></i></a>
            <a href="#"><i class="fa-brands fa-github"></i></a>
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
        </div>
    </div>""" , unsafe_allow_html=True)

def create_footer_section():
    st.markdown("---")
    st.header("© 2025 DevRag. All rights reserved.", anchor=False)


def handle_navigation():
    """Handle page navigation"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'landing'
    if st.session_state.current_page == 'chatbot':
        import chatbot

def main():
    """Main application function"""
    setup_page_config()
    hide_dev_options()
    set_background(BG_IMAGE)
    load_custom_css()
    handle_navigation()
    
    create_navbar()
    
    if st.session_state.get('current_page') == 'landing':
        create_hero_section()
        create_about_section()
        create_features_section()
        create_contact_section()
        create_footer_section()

if __name__ == '__main__':
    main()