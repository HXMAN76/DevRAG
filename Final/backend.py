# Authentication
# CHATBOT
# WEBSCRAPING
# DATABASE
# Github_Scraper
# Memory
import firebase_admin
from firebase_admin import credentials, auth, firestore
import os
from dotenv import load_dotenv
from mistral import Mistral
import json

class Github_Scraper:
    def __init__(self):
        pass
    
    def url_changer(self, url):
        pass
    
    def scrape_content(self, url):
        pass
    
    def get_data(self, url):
        url = self.url_changer(url)
        data = self.scrape_content(url)
        return data
        
class Web_Scraper:
    def __init__(self):
        pass
        
    def recursive_scraper(self, links):
        pass
        
    def get_data(self, url):
        pass
    
    def scrape_content(self, url):
        data , struc = self.get_data(url)
        data += self.recursive_scraper(struc.links)
        return data
    
class PDFScraper:
    def __init__(self):
        pass
    def extract_data(pdf_path):
        pass
    
class TextProcessor:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        return text_splitter.split_text(text)

class SnowflakeManager:
    def __init__(self):
        self.uid = None
    
    def get_uid(self):
        # returns data from auth page
        pass
    def set_uid(self, uid):
        self.uid = uid
        
    def connect(self):
        # returns connection object
        pass       
    def disconnect(self):
        # disconnects the connection
        pass
    def insert_data(self,data,source):
        # inserts data into the database
        if source.casefold() == 'Github':
            # insert into github table
            pass
        elif source.casefold() == 'Web':
            # insert into web table
            pass
        elif source.casefold() == 'PDF':
            # insert into pdf table
            pass
    def search(self, query):
        # both common and user data
        pass
    
    def generate(self, query):
        response = self.search(query)
        INSTRUCTION = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                $$You are an intelligent assistant who can answer the user query based on the provided document content and can also provide the relevant information.
                Document: {response}
                Query: {query}$$
            );
        """
        generation = None # fill up
        return generation

class Memory:
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
    
    def create_summary(conversations):
        """
        Creates a summary of conversations using Mistral AI
        """
        try:
            api = os.getenv('SUMMARIZER')
            if not api:
                raise ValueError("SUMMARIZER API key not found in environment variables")
                
            # Format conversations for Mistral
            formatted_conversations = []
            for conv in conversations:
                formatted_conversations.append(f"User: {conv['query']}\nAssistant: {conv['response']}")
            
            conversation_text = "\n\n".join(formatted_conversations)
            
            client = Mistral(api_key=api)  # Corrected parameter name
            
            chat = client.chat.completions.create(  # Corrected method name
                model="mistral-large-v2",  # Corrected model name
                messages=[
                    {
                        "role": "system",
                        "content": "Please summarize the following conversations into a concise paragraph that captures the main topics discussed and key points from both the user's queries and the assistant's responses."
                    },
                    {
                        "role": "user",
                        "content": conversation_text
                    }
                ],
                temperature=0.5
            )
            
            return chat.choices[0].message.content
            
        except Exception as e:
            # Fallback to basic summary if Mistral API fails
            return f"Error creating summary with Mistral: {str(e)}"
    
    def manage_conversations(self, user_id, query, response):
        """
        Manages conversations by:
        1. Adding new conversation
        2. Checking if there are 5 conversations
        3. If yes, summarizes them using Mistral AI
        4. Clears the conversations list
        """
        try:
            # Get user document reference
            user_ref = self.db.collection('user_data').document(user_id)
            user_doc = user_ref.get()
            user_data = user_doc.to_dict()
            
            # Add new conversation
            conversation = {
                'query': query,
                'response': response
            }
            
            # Get current conversations
            conversations = user_data.get('past_conversations', [])
            conversations.append(conversation)
            
            # Check if we've reached 5 conversations
            if len(conversations) >= 5:
                # Create summary of conversations
                summary = {
                    'summary_text':self.create_summary(conversations),
                    'original_conversations': conversations
                }
                
                # Update document with summary and clear conversations
                user_ref.update({
                    'conversation_summary': firestore.ArrayUnion([summary]),
                    'past_conversations': [] # Clear the conversations list
                })
            else:
                # Just update with new conversation
                user_ref.update({
                    'past_conversations': conversations
                })
                
            return True
            
        except Exception as e:
            raise Exception(f"Failed to manage conversations: {str(e)}")
        
    def retrieve_memory(self,user_id):
        user_ref = self.db.collection('user_data').document(user_id)
        user_doc = user_ref.get()
        user_data = user_doc.to_dict()
        conversations = user_data.get('past_conversations', [])
        summary_conversations = user_data.get('conversation_summary', [])
        if summary_conversations:
            conversations.append(summary_conversations[0])
        return conversations
        
class LLMcalls:
    def __init__(self):
        pass
    
class Backend:
    def __init__(self):
        pass
        # intisiali