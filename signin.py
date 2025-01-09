import firebase_admin
from firebase_admin import credentials, auth, firestore

cred = credentials.Certificate("E:/Hackathons/DevRAG/devrag-e191a-firebase-adminsdk-dv2k5-d180030348.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def get_user_id (email, password):
    try:
        user = auth.get_user_by_email(email)
        return user.uid
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

def get_user_info_firestore(user_id):
    try:
        user_data = db.collection('user_data').document(user_id).get()
        return user_data.to_dict()
    except Exception as e:
        print(f"Error getting user data: {e}")
        return None
    
email = "babloo23@gmail.com"
password = "babloo123"
user_id = get_user_id(email, password)
if user_id:
    print(f"User Id: {get_user_id(email, password)}")
   