from google.cloud import firestore
from datetime import datetime
from mistral import Mistral
import os
import json

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
            'response': response,
            'timestamp': datetime.now()
        }
        
        # Get current conversations
        conversations = user_data.get('past_conversations', [])
        conversations.append(conversation)
        
        # Check if we've reached 5 conversations
        if len(conversations) >= 5:
            # Create summary of conversations
            summary = {
                'summary_text': self._create_summary(conversations),
                'timestamp': datetime.now(),
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
        
def _create_summary(self, conversations):
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