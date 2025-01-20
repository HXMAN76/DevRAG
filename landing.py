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
    with open('static/styles.css', 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def create_navbar():
    """Create the navigation bar"""
    st.markdown("""
    <div class="navbar">
        <a href="#home">Home</a>
        <a href="#features">Features</a>
        <a href="#contact-us">Team</a>
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
        pass

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


def create_tech_stack_section():
    st.header("Tech Stack", anchor=False)
    st.markdown("""
     <div class="tech-stack">
        <img src="https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png" alt="streamlilt_logo" style="width: 15%;height: 15%">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_Logo.svg/1280px-Snowflake_Logo.svg.png" alt="snowflake" id="snowflake" style="width: 20%;height: 20%;">
        <img src="https://static1.squarespace.com/static/65c726ca17f84d5307a0dda1/65da1a93a8e8634b664835c9/65f6a87476d8e45fc3010249/1711102391682/announcing-mistral.png?format=1500w" alt="mistral" style="width: 10%;height: 10%">
        <img src="https://ml.globenewswire.com/Resource/Download/3034f6cd-48c3-4b5e-bd7f-242dbaecaab4?size=2" alt="trulens" style="width: 8%;height: 8%">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1869px-Python-logo-notext.svg.png" alt="python" style="width: 8%;height: 8%">  
        <img src="https://www.ichdata.com/wp-content/uploads/2017/06/2024070803153850.png" alt="fireBase" style="width: 15%;height: 15%">
    </div>
    """,unsafe_allow_html=True)

def create_about_section():
    """Create the about section"""
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


def create_team_section():
    """Create the contact section with profile card"""
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
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
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
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
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
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
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
            <a href="#"><i class="fa-regular fa-envelope"></i></a>
        </div>
    </div>""" , unsafe_allow_html=True)

def create_footer_section():
    st.html("<br><hr id='hr-2'>")
    st.html("<span id='footer'>© 2025 DevRag. All rights reserved.</span>")

def main():
    """Main application function"""
    setup_page_config()
    hide_dev_options()
    set_background(BG_IMAGE)
    load_custom_css()

    create_navbar()    
    create_hero_section()
    create_about_section()
    create_features_section()
    create_tech_stack_section()
    create_team_section()
    create_footer_section()

if __name__ == '__main__':
    main()
