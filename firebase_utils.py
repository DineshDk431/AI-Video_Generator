import os
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import json

# Singleton database instance
_db = None

def init_firebase():
    """Initialize Firebase Admin SDK.
    
    Supports two modes:
    1. Local: Uses serviceAccountKey.json file
    2. Streamlit Cloud: Uses st.secrets["firebase"] configuration
    """
    global _db
    if _db:
        return _db
    
    try:
        # Check if already initialized
        if firebase_admin._apps:
            print("DEBUG: Firebase App already initialized.")
            _db = firestore.client()
            return _db
        
        # Try Streamlit secrets first (for cloud deployment)
        if hasattr(st, 'secrets') and 'firebase' in st.secrets:
            print("DEBUG: Using Streamlit secrets for Firebase...")
            firebase_config = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            print("DEBUG: Firebase initialized from Streamlit secrets!")
            return _db
        
        # Fallback to local JSON file
        key_path = "serviceAccountKey.json"
        if os.getenv("FIREBASE_KEY_PATH"):
            key_path = os.getenv("FIREBASE_KEY_PATH")

        print(f"DEBUG: init_firebase called. Key path: {os.path.abspath(key_path)}")
        if not os.path.exists(key_path):
            print("DEBUG: Key file not found!")
            return None

        print("DEBUG: Initializing new Firebase App...")
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
            
        _db = firestore.client()
        print("DEBUG: Firestore Client created.")
        return _db
    except Exception as e:
        print(f"DEBUG: Firebase Init Error: {e}")
        return None

def submit_job_to_cloud(prompt: str, settings: dict):
    """
    Submit a video generation job to the Cloud Queue (Firestore).
    """
    print("DEBUG: submit_job_to_cloud called.")
    db = init_firebase()
    if not db:
        print("DEBUG: No DB client.")
        return {
            "success": False, 
            "message": "Firebase not configured. Missing 'serviceAccountKey.json'."
        }
    
    try:
        # Create a document in 'video_jobs'
        # We store all settings so the worker knows what to do
        job_data = {
            "prompt": prompt,
            "settings": settings,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
            "user_id": "generic_user" # Placeholder
        }
        
        update_time, doc_ref = db.collection("video_queue").add(job_data)
        return {
            "success": True, 
            "job_id": doc_ref.id,
            "message": "Job queued successfully!"
        }
        
    except Exception as e:
        # Fallback to REST API if gRPC fails (Firewall issues)
        print(f"SDK Failed ({e}), attempting REST Fallback...")
        return submit_job_via_rest(prompt, settings)

def submit_job_via_rest(prompt, settings):
    """Fallback method using HTTP requests to bypass gRPC blocking."""
    import json
    import requests
    import google.auth.transport.requests
    import google.oauth2.service_account
    
    try:
        key_path = "serviceAccountKey.json"
        
        # 1. Get Project ID
        with open(key_path) as f:
            key_data = json.load(f)
            project_id = key_data["project_id"]
            
        # 2. Get Access Token
        creds = google.oauth2.service_account.Credentials.from_service_account_file(
            key_path, 
            scopes=["https://www.googleapis.com/auth/datastore"]
        )
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        token = creds.token
        
        # 3. Helper to format for Firestore REST API
        def to_fs(v):
            if isinstance(v, str): return {"stringValue": v}
            if isinstance(v, bool): return {"booleanValue": v}
            if isinstance(v, int): return {"integerValue": str(v)}
            if isinstance(v, float): return {"doubleValue": v}
            if isinstance(v, dict): 
                return {"mapValue": {"fields": {k: to_fs(val) for k, val in v.items()}}}
            return {"stringValue": str(v)}

        # 4. Construct Payload
        # Use simple timestamp string instead of server timestamp for REST
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        
        payload = {
            "fields": {
                "prompt": to_fs(prompt),
                "settings": to_fs(settings),
                "status": to_fs("pending"),
                "created_at": {"timestampValue": timestamp + "Z"},
                "user_id": to_fs("generic_user")
            }
        }
        
        # 5. Send Request
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/video_queue"
        headers = {
            "Authorization": f"Bearer {token}", 
            "Content-Type": "application/json"
        }
        
        resp = requests.post(url, headers=headers, json=payload)
        
        if resp.status_code == 200:
            doc_id = resp.json()["name"].split("/")[-1]
            return {"success": True, "job_id": doc_id, "message": "Job queued via HTTP (Firewall Bypass)!"}
        else:
            return {"success": False, "message": f"REST Error {resp.status_code}: {resp.text}"}
            
    except Exception as e:
        return {"success": False, "message": f"REST Connection Failed: {str(e)}"}

def get_job_status(job_id):
    """Check status of a cloud job."""
    print(f"DEBUG: Checking status for {job_id}")
    try:
        # Try SDK first
        db = init_firebase()
        if db:
            doc = db.collection("video_queue").document(job_id).get()
            if doc.exists:
                return doc.to_dict()
    except Exception as e:
        print(f"DEBUG: SDK Status Check Failed ({e})")
    
    # Fallback to REST
    return get_job_status_via_rest(job_id)

def get_job_status_via_rest(job_id):
    """Retrieve job via REST API."""
    import json
    import requests
    import google.auth.transport.requests
    import google.oauth2.service_account
    
    try:
        key_path = "serviceAccountKey.json"
        
        # 1. Credentials
        with open(key_path) as f:
            key_data = json.load(f)
            project_id = key_data["project_id"]
            
        creds = google.oauth2.service_account.Credentials.from_service_account_file(
            key_path, 
            scopes=["https://www.googleapis.com/auth/datastore"]
        )
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        token = creds.token
        
        # 2. GET Request
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/video_queue/{job_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = requests.get(url, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            fields = data.get("fields", {})
            
            # Helper to unwrap Firestore types
            def from_fs(v):
                if not v: return None
                if "stringValue" in v: return v["stringValue"]
                if "booleanValue" in v: return v["booleanValue"]
                if "integerValue" in v: return int(v["integerValue"])
                if "mapValue" in v:
                    return {k: from_fs(val) for k, val in v["mapValue"]["fields"].items()}
                return str(v)

            result = {
                "status": from_fs(fields.get("status")),
                "video_url": from_fs(fields.get("video_url")),
                "error": from_fs(fields.get("error"))
            }
            return result
        else:
            print(f"DEBUG: REST Status Error: {resp.text}")
            return None
            
    except Exception as e:
        print(f"DEBUG: REST Check Failed: {e}")
        return None
