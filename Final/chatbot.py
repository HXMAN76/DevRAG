import streamlit as st

def load_custom_css():
    # Load custom CSS styles
    with open('static/chatbot.css', 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def main():
    load_custom_css()

    st.title("User",anchor=False)
    
    # Initialize chat history in session state if it doesn't exist
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    with st.container(key="chat_input"):
        # Chat input
        with st.form("User query",border=False,clear_on_submit=True):
            user_query, send_button = st.columns([0.9,0.1])
            prompt = user_query.text_input("Prompt",label_visibility="collapsed",placeholder="Ask your question...")
            submit_button = send_button.form_submit_button(label="ᯓ➤")

            if submit_button:
                st.success("Message sent!")


        col1, _ = st.columns([2,3])

        with col1:

            web,github,pdf = st.columns(3)
            if web.button("🌐",key="web"):
                url_input = st.text_input("Enter website URL")
                if url_input:
                    st.success("URL processed successfully!")
                    # Add your web scraping function here

            if github.button("🐈‍⬛",key="github"):
                github_input = st.text_input("Enter GitHub URL")
                if github_input:
                    st.success("URL processed successfully!")
                    # Add your github scraping function here

            if pdf.button("🔗",key="pdf"):
                uploaded_file = st.file_uploader("Upload PDF", type="pdf")
                if uploaded_file:
                    st.success("PDF uploaded successfully!")
                    # Add your PDF processing function here

    if prompt:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user",avatar="https://cdn-icons-png.flaticon.com/512/1144/1144760.png"):
            st.write(prompt)

        # Add assistant message to chat history
        response = f"Echo: {prompt}"
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant",avatar="https://cdn-icons-png.flaticon.com/512/4711/4711987.png"):
            st.write(response)

if __name__ == "__main__":
    main()