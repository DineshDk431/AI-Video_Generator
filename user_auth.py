"""
User Authentication & Session Management.
Handles user registration, login, profile management, and 48-hour session timeout.
"""
import json
import os
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import streamlit as st


# Storage paths
USERS_FILE = "outputs/users.json"
SESSIONS_FILE = "outputs/sessions.json"
OTP_FILE = "outputs/otp_store.json"

# Session timeout in hours
SESSION_TIMEOUT_HOURS = 48

# OTP expiry in minutes
OTP_EXPIRY_MINUTES = 5


def ensure_user_storage():
    """Ensure user storage files exist."""
    Path("outputs").mkdir(exist_ok=True)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(OTP_FILE):
        with open(OTP_FILE, "w") as f:
            json.dump({}, f)


def _load_users() -> Dict:
    """Load all users from storage."""
    ensure_user_storage()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_users(users: Dict):
    """Save users to storage."""
    ensure_user_storage()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _load_sessions() -> Dict:
    """Load all sessions from storage."""
    ensure_user_storage()
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_sessions(sessions: Dict):
    """Save sessions to storage."""
    ensure_user_storage()
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


# ==================== OTP FUNCTIONS ====================

import random

def generate_otp() -> str:
    """Generate a 4-digit OTP."""
    return str(random.randint(1000, 9999))


def _load_otp_store() -> Dict:
    """Load OTP store."""
    ensure_user_storage()
    try:
        with open(OTP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_otp_store(otp_store: Dict):
    """Save OTP store."""
    ensure_user_storage()
    with open(OTP_FILE, "w", encoding="utf-8") as f:
        json.dump(otp_store, f, indent=2)


def send_otp(mobile: str) -> tuple[str, bool]:
    """
    Generate and send OTP via Fast2SMS.
    Falls back to demo mode if API key not configured.
    
    Args:
        mobile: Mobile number to send OTP to (Indian numbers only)
    
    Returns:
        Tuple of (otp: str, sms_sent: bool)
    """
    import requests
    
    otp = generate_otp()
    expiry_time = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Store OTP
    otp_store = _load_otp_store()
    otp_store[mobile] = {
        "otp": otp,
        "expires_at": expiry_time.isoformat(),
        "attempts": 0
    }
    _save_otp_store(otp_store)
    
    # Try to send via Fast2SMS
    api_key = os.getenv("FAST2SMS_API_KEY", "")
    
    if api_key and api_key != "your_api_key_here":
        try:
            # Clean mobile number (remove +91, spaces, etc.)
            clean_mobile = mobile.replace("+91", "").replace(" ", "").replace("-", "")
            if len(clean_mobile) > 10:
                clean_mobile = clean_mobile[-10:]  # Take last 10 digits
            
            # Fast2SMS API endpoint for OTP
            url = "https://www.fast2sms.com/dev/bulkV2"
            
            payload = {
                "route": "otp",
                "variables_values": otp,
                "numbers": clean_mobile
            }
            
            headers = {
                "authorization": api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("return") == True:
                print(f"SMS sent successfully to {clean_mobile}")
                return otp, True
            else:
                print(f"Fast2SMS Error: {result.get('message', 'Unknown error')}")
                return otp, False
                
        except Exception as e:
            print(f"Fast2SMS Exception: {e}")
            return otp, False
    else:
        # Demo mode - no API key configured
        print(f"Demo mode: OTP {otp} for {mobile}")
        return otp, False


def verify_otp(mobile: str, entered_otp: str) -> tuple[bool, str]:
    """
    Verify the entered OTP against stored OTP.
    
    Args:
        mobile: Mobile number
        entered_otp: OTP entered by user
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    otp_store = _load_otp_store()
    stored = otp_store.get(mobile)
    
    if not stored:
        return False, "OTP not found. Please request a new OTP."
    
    # Check expiry
    expiry_time = datetime.fromisoformat(stored["expires_at"])
    if datetime.now() > expiry_time:
        # Clean up expired OTP
        del otp_store[mobile]
        _save_otp_store(otp_store)
        return False, "OTP expired. Please request a new OTP."
    
    # Check attempts (max 3)
    if stored["attempts"] >= 3:
        del otp_store[mobile]
        _save_otp_store(otp_store)
        return False, "Too many attempts. Please request a new OTP."
    
    # Verify OTP
    if stored["otp"] == entered_otp:
        # OTP verified - clean up
        del otp_store[mobile]
        _save_otp_store(otp_store)
        return True, "OTP verified successfully!"
    else:
        # Wrong OTP - increment attempts
        stored["attempts"] += 1
        otp_store[mobile] = stored
        _save_otp_store(otp_store)
        remaining = 3 - stored["attempts"]
        return False, f"Incorrect OTP. {remaining} attempts remaining."


def generate_user_id(mobile: str) -> str:
    """Generate unique user ID from mobile number."""
    return hashlib.md5(mobile.encode()).hexdigest()[:12]


def register_user(name: str, location: str, mobile: str) -> Dict:
    """
    Register a new user.
    
    Args:
        name: User's full name
        location: User's location
        mobile: User's mobile number (unique identifier)
    
    Returns:
        User data dict with id, name, location, mobile, created_at
    """
    users = _load_users()
    user_id = generate_user_id(mobile)
    
    # Check if user already exists
    if user_id in users:
        return users[user_id]
    
    user_data = {
        "id": user_id,
        "name": name.strip(),
        "location": location.strip(),
        "mobile": mobile.strip(),
        "created_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat()
    }
    
    users[user_id] = user_data
    _save_users(users)
    
    return user_data


def get_user_by_mobile(mobile: str) -> Optional[Dict]:
    """Get user by mobile number."""
    users = _load_users()
    user_id = generate_user_id(mobile)
    return users.get(user_id)


def update_last_login(user_id: str):
    """Update user's last login time."""
    users = _load_users()
    if user_id in users:
        users[user_id]["last_login"] = datetime.now().isoformat()
        _save_users(users)


def create_session(user_id: str) -> str:
    """
    Create a new session for user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        Session token string
    """
    sessions = _load_sessions()
    
    # Generate unique session token
    session_token = str(uuid.uuid4())
    
    # Create session with expiry
    expiry_time = datetime.now() + timedelta(hours=SESSION_TIMEOUT_HOURS)
    
    sessions[session_token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": expiry_time.isoformat()
    }
    
    _save_sessions(sessions)
    
    # Update last login
    update_last_login(user_id)
    
    return session_token


def validate_session(session_token: str) -> bool:
    """
    Check if session is valid (exists and not expired).
    
    Args:
        session_token: The session token to validate
    
    Returns:
        True if session is valid, False otherwise
    """
    if not session_token:
        return False
    
    sessions = _load_sessions()
    session = sessions.get(session_token)
    
    if not session:
        return False
    
    # Check expiry
    expiry_time = datetime.fromisoformat(session["expires_at"])
    if datetime.now() > expiry_time:
        # Session expired - remove it
        del sessions[session_token]
        _save_sessions(sessions)
        return False
    
    return True


def get_user_from_session(session_token: str) -> Optional[Dict]:
    """Get user data from session token."""
    if not validate_session(session_token):
        return None
    
    sessions = _load_sessions()
    session = sessions.get(session_token)
    
    if not session:
        return None
    
    users = _load_users()
    return users.get(session["user_id"])


def destroy_session(session_token: str):
    """Logout - destroy session."""
    sessions = _load_sessions()
    if session_token in sessions:
        del sessions[session_token]
        _save_sessions(sessions)


def get_current_user() -> Optional[Dict]:
    """Get currently logged-in user from Streamlit session state."""
    session_token = st.session_state.get("session_token")
    if not session_token:
        return None
    
    return get_user_from_session(session_token)


def is_logged_in() -> bool:
    """Check if current user is logged in with valid session."""
    session_token = st.session_state.get("session_token")
    return validate_session(session_token)


def logout():
    """Logout current user."""
    session_token = st.session_state.get("session_token")
    if session_token:
        destroy_session(session_token)
    
    # Clear session state
    if "session_token" in st.session_state:
        del st.session_state["session_token"]
    if "current_user" in st.session_state:
        del st.session_state["current_user"]


def generate_profile_logo(name: str, size: int = 50) -> str:
    """
    Generate HTML for profile logo with user's initial.
    
    Args:
        name: User's name
        size: Size of the logo in pixels
    
    Returns:
        HTML string for the profile logo
    """
    initial = name[0].upper() if name else "?"
    
    # Generate a consistent color based on name
    color_hash = hash(name) % 360
    bg_color = f"hsl({color_hash}, 70%, 50%)"
    
    return f"""
    <div style="
        width: {size}px;
        height: {size}px;
        border-radius: 50%;
        background: linear-gradient(135deg, {bg_color}, hsl({(color_hash + 40) % 360}, 70%, 40%));
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: {size // 2}px;
        font-weight: 700;
        color: white;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        border: 2px solid rgba(255,255,255,0.2);
    ">{initial}</div>
    """


def render_login_page():
    """Render the login/registration page with OTP verification."""
    st.markdown("""
    <style>
        .auth-container {
            max-width: 450px;
            margin: 2rem auto;
            padding: 2.5rem;
            background: linear-gradient(145deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.05));
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-header h1 {
            background: linear-gradient(90deg, #a855f7 0%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .auth-header p {
            color: #94a3b8;
            font-size: 0.95rem;
        }
        .profile-preview {
            display: flex;
            justify-content: center;
            margin: 1.5rem 0;
        }
        .otp-display {
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(16, 185, 129, 0.1));
            border: 1px solid rgba(34, 197, 94, 0.4);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            margin: 1rem 0;
        }
        .otp-code {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 8px;
            color: #22c55e;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize OTP state
    if "otp_step" not in st.session_state:
        st.session_state.otp_step = "mobile"  # mobile -> otp -> done
    if "pending_mobile" not in st.session_state:
        st.session_state.pending_mobile = None
    if "pending_otp" not in st.session_state:
        st.session_state.pending_otp = None
    if "is_new_user" not in st.session_state:
        st.session_state.is_new_user = False
    if "sms_sent" not in st.session_state:
        st.session_state.sms_sent = False
    
    # Center container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="auth-header">
            <h1>🎬 AI Video Generator</h1>
            <p>Create stunning videos with AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        # STEP 1: Enter Mobile Number
        if st.session_state.otp_step == "mobile":
            st.markdown("##### 📱 Enter Your Mobile Number")
            st.caption("We'll send you a 4-digit OTP to verify")
            
            mobile = st.text_input("Mobile Number", placeholder="+91 9876543210", key="mobile_input", label_visibility="collapsed")
            
            if st.button("� Send OTP", type="primary", use_container_width=True):
                if not mobile or len(mobile) < 10:
                    st.error("⚠️ Please enter a valid mobile number")
                else:
                    # Check if user exists
                    existing_user = get_user_by_mobile(mobile)
                    st.session_state.is_new_user = existing_user is None
                    st.session_state.pending_mobile = mobile
                    
                    # Generate and send OTP
                    otp, sms_sent = send_otp(mobile)
                    st.session_state.pending_otp = otp
                    st.session_state.sms_sent = sms_sent
                    st.session_state.otp_step = "otp"
                    st.rerun()
        
        # STEP 2: Verify OTP
        elif st.session_state.otp_step == "otp":
            mobile = st.session_state.pending_mobile
            
            st.markdown(f"##### 🔐 Verify OTP")
            st.caption(f"OTP sent to **{mobile}**")
            
            # Show different UI based on whether SMS was actually sent
            if st.session_state.sms_sent:
                # Real SMS sent - don't show OTP
                st.success("✅ OTP sent to your mobile! Check your SMS.")
            else:
                # Demo mode - show OTP on screen
                st.markdown(f"""
                <div class="otp-display">
                    <div style="font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.5rem;">📱 Your OTP (Demo Mode)</div>
                    <div class="otp-code">{st.session_state.pending_otp}</div>
                    <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.5rem;">Valid for 5 minutes</div>
                </div>
                """, unsafe_allow_html=True)
                st.info("💡 Add your Fast2SMS API key in .env to send real SMS")
            
            entered_otp = st.text_input("Enter 4-digit OTP", max_chars=4, key="otp_input", placeholder="• • • •")
            
            col_verify, col_resend = st.columns(2)
            
            with col_verify:
                if st.button("✅ Verify", type="primary", use_container_width=True):
                    if not entered_otp or len(entered_otp) != 4:
                        st.error("⚠️ Please enter 4-digit OTP")
                    else:
                        success, message = verify_otp(mobile, entered_otp)
                        if success:
                            if st.session_state.is_new_user:
                                # New user - go to registration form
                                st.session_state.otp_step = "register"
                                st.rerun()
                            else:
                                # Existing user - login directly
                                user = get_user_by_mobile(mobile)
                                session_token = create_session(user["id"])
                                st.session_state["session_token"] = session_token
                                st.session_state["current_user"] = user
                                # Reset OTP state
                                st.session_state.otp_step = "mobile"
                                st.session_state.pending_mobile = None
                                st.session_state.pending_otp = None
                                st.success(f"✅ Welcome back, {user['name']}!")
                                st.rerun()
                        else:
                            st.error(f"❌ {message}")
            
            with col_resend:
                if st.button("🔄 Resend OTP", use_container_width=True):
                    otp, sms_sent = send_otp(mobile)
                    st.session_state.pending_otp = otp
                    st.session_state.sms_sent = sms_sent
                    st.rerun()
            
            if st.button("← Change Number", use_container_width=True):
                st.session_state.otp_step = "mobile"
                st.session_state.pending_mobile = None
                st.session_state.pending_otp = None
                st.rerun()
        
        # STEP 3: New User Registration (after OTP verified)
        elif st.session_state.otp_step == "register":
            mobile = st.session_state.pending_mobile
            
            st.markdown("##### 👤 Complete Your Profile")
            st.success("✅ Mobile verified! Now create your account.")
            
            name = st.text_input("👤 Full Name", placeholder="Enter your name", key="reg_name")
            location = st.text_input("📍 Location", placeholder="City, Country", key="reg_location")
            
            # Live profile preview
            if name:
                st.markdown("**Profile Preview:**")
                st.markdown(f"""
                <div class="profile-preview">
                    {generate_profile_logo(name, 60)}
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; color: #94a3b8;'>{name}</p>", unsafe_allow_html=True)
            
            if st.button("� Create Account", type="primary", use_container_width=True):
                if not name or not location:
                    st.error("⚠️ Please fill in all fields")
                else:
                    # Register new user
                    user = register_user(name, location, mobile)
                    session_token = create_session(user["id"])
                    
                    # Store in session state
                    st.session_state["session_token"] = session_token
                    st.session_state["current_user"] = user
                    
                    # Reset OTP state
                    st.session_state.otp_step = "mobile"
                    st.session_state.pending_mobile = None
                    st.session_state.pending_otp = None
                    st.session_state.is_new_user = False
                    
                    st.success(f"✅ Welcome, {user['name']}!")
                    st.rerun()
            
            if st.button("← Back", use_container_width=True):
                st.session_state.otp_step = "mobile"
                st.session_state.pending_mobile = None
                st.rerun()
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <p style="text-align: center; color: #64748b; font-size: 0.8rem;">
            🔒 Your data is stored locally and never shared<br>
            Session expires after 48 hours of inactivity
        </p>
        """, unsafe_allow_html=True)


def render_profile_sidebar():
    """Render profile section in sidebar - just logo that expands to show details."""
    user = get_current_user()
    if not user:
        return
    
    initial = user['name'][0].upper() if user['name'] else "?"
    color_hash = hash(user['name']) % 360
    
    # Use Streamlit's popover for Google-style click behavior
    with st.popover(f"👤 {initial}", use_container_width=False):
        # User details card inside popover
        st.markdown(f"""
        <div style="text-align: center; padding: 0.5rem;">
            <div style="
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, hsl({color_hash}, 70%, 50%), hsl({(color_hash + 40) % 360}, 70%, 40%));
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-size: 28px;
                font-weight: 700;
                color: white;
                margin-bottom: 0.75rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            ">{initial}</div>
            <div style="font-weight: 600; font-size: 1.1rem; color: white; margin-bottom: 0.25rem;">{user['name']}</div>
            <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.25rem;">📍 {user['location']}</div>
            <div style="font-size: 0.8rem; color: #64748b;">📱 {user['mobile']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Logout button inside popover
        if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
            logout()
            st.rerun()
    
    st.markdown("---")

