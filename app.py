import streamlit as st

# Add FontAwesome for icons
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {
            background-color: #464646;
        }
        .sidebar {
            background-color: black;
            color: white;
        }
        .sidebar-btn {
            color: white;
            border: none;
            background: none;
            text-align: left;
            padding: 10px;
            font-size: 14px;
            width: 100%;
            cursor: pointer;
        }
        .sidebar-btn:hover {
            color: #1db954;
        }
        .custom-input input {
            width: 60%;
            padding: 8px;
            margin-left: 120px;
            margin-right: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        .send-btn {
            background-color: #1db954;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .send-btn:hover {
            background-color: #18a349;
        }
        .profile-container {
            display: flex;
            align-items: center;
            padding: 10px;
            margin-bottom: 10px;
        }
        .profile-pic {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background-color: #ccc;
            margin-right: 10px;
        }
        .profile-details {
            font-size: 12px;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        /* Set background color for the whole page */
        body {
            background-color: #464646 !important;
        }
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(360deg, #121212, #1db954);
        }
        [data-testid="stSidebar"] {
            background-color: #181818;
        }
        [data-testid="stHeader"] {
            background-color: #1db954;
        }
        .hero-section {
            display: flex;
            flex-direction: column;
            background-color: hsl(140, 34%, 22%);
            color: white;
            padding: 20px;
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar layout
with st.sidebar:
    # Profile container
    st.markdown("""
        <div class="profile-container">
            <div class="profile-pic"></div>
            <div class="profile-details">
                <strong>USER-ID</strong><br>
                user-name
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # "Start a new chat" button
    st.markdown("""
        <button class="sidebar-btn" style="background-color: #1db954; color: white; border-radius: 5px;">
            <i class="fa fa-plus"></i> Start a new chat
        </button>
    """, unsafe_allow_html=True)
    
    # Sidebar options
    st.markdown("""
        <button class="sidebar-btn"><i class="fa fa-trash"></i> Clear all conversations</button>
        <button class="sidebar-btn"><i class="fa fa-sun"></i> Switch Light Mode</button>
        <button class="sidebar-btn"><i class="fa fa-info-circle"></i> About Us</button>
        <button class="sidebar-btn" style = "color: red;"><i class="fa fa-power-off"></i> Log out</button>
    """, unsafe_allow_html=True)

# Main content
st.markdown("""
    <div class="hero-section">
        <h1 style="text-align: center;">Welcome to <span style="color: #1db954;">DevRAG</span></h1>
        <p style="text-align: center; font-size: 14px;">
            Empowering developers with instant, AI-driven insights by combining Retrieval-Augmented Generation and dynamic web-scraped knowledge.
        </p>
        <div class="custom-input">
            <input type="text" placeholder="Example: Explain quantum computing in simple terms"/>
            <button class="send-btn"><i class="fa fa-paper-plane"></i></button>
        </div>
    </div>
""", unsafe_allow_html=True)

# Three features section
st.markdown("""
    <div style="display: flex; justify-content: space-around; margin-top: 30px; color: white;">
        <div style="text-align: center;">
            <i class="fa fa-magic" style="font-size: 30px; color: #1db954;"></i>
            <h4>Clear and Precise</h4>
            <p style="font-size: 12px;">Accurate insights for your queries.</p>
        </div>
        <div style="text-align: center;">
            <i class="fa fa-user" style="font-size: 30px; color: #1db954;"></i>
            <h4>Personalized Answers</h4>
            <p style="font-size: 12px;">Tailored responses for better efficiency.</p>
        </div>
        <div style="text-align: center;">
            <i class="fa fa-line-chart" style="font-size: 30px; color: #1db954;"></i>
            <h4>Increased Efficiency</h4>
            <p style="font-size: 12px;">Streamline your development process.</p>
        </div>
    </div>
""", unsafe_allow_html=True)
