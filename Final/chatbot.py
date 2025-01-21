import streamlit as st

def load_custom_css():
    # Load custom CSS styles
    with open('static/chatbot.css', 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def handle_sidebar_input(input_type):
    with st.sidebar:
        st.title(f"Process {input_type}")
        if input_type == "PDF":
            uploaded_file = st.file_uploader("Upload PDF", type="pdf")
            if uploaded_file:
                st.success("PDF uploaded successfully!")
                return uploaded_file
        elif input_type == "GitHub":
            github_input = st.text_input(f"Enter {input_type} URL")
            if github_input:
                st.success(f"{input_type} Repository processed successfully!")
                return github_input
        elif input_type == "Website":
            url_input = st.text_input(f"Enter {input_type} URL")
            if url_input:
                st.success(f"{input_type} URL processed successfully!")
                return url_input
    return None

def main():
    load_custom_css()

    st.title("User", anchor=False)
    
    # Initialize session states
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "show_sidebar" not in st.session_state:
        st.session_state.show_sidebar = False
    if "sidebar_type" not in st.session_state:
        st.session_state.sidebar_type = None

    # Display chat history with avatars
    for message in st.session_state.messages:
        avatar_url = "https://cdn-icons-png.flaticon.com/512/1144/1144760.png" if message["role"] == "user" else "https://cdn-icons-png.flaticon.com/512/4711/4711987.png"
        with st.chat_message(message["role"], avatar=avatar_url):
            st.write(message["content"])

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
        result = handle_sidebar_input(st.session_state.sidebar_type)
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
        response = f"Echo: {prompt}"
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response,
            "avatar": "https://cdn-icons-png.flaticon.com/512/4711/4711987.png"
        })
        with st.chat_message("assistant", avatar="https://cdn-icons-png.flaticon.com/512/4711/4711987.png"):
            st.write(response)

if __name__ == "__main__":
    main()