import streamlit as st
import os
import time
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# User authentication
from user_auth import (
    is_logged_in, get_current_user, render_login_page, 
    render_profile_sidebar, logout
)

# Load environment variables
load_dotenv()

# Video quality presets
VIDEO_QUALITY = {
    "240p": {"width": 426, "height": 240},
    "540p": {"width": 960, "height": 540},
    "720p": {"width": 1280, "height": 720},
    "1080p": {"width": 1920, "height": 1080},
    "1440p": {"width": 2560, "height": 1440}
}

# Page configuration - sidebar always visible
st.set_page_config(
    page_title="AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for sidebar styling and toggle button
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Force Sidebar Toggle Button Visibility */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        color: white !important;
        background-color: rgba(99, 102, 241, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        padding: 4px;
        z-index: 1000002 !important;
    }
    
    [data-testid="stSidebarCollapsedControl"]:hover {
        background-color: rgba(168, 85, 247, 0.6) !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stApp { font-family: 'Inter', sans-serif; }

    
    .main .block-container {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        padding: 2rem 3rem;
        border-radius: 20px;
    }
    
    .main-header {
        background: linear-gradient(90deg, #a855f7 0%, #6366f1 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        color: #94a3b8;
        text-align: center;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .model-card {
        background: linear-gradient(145deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.05));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .veo-card {
        background: linear-gradient(145deg, rgba(66, 133, 244, 0.15), rgba(52, 168, 83, 0.1));
        border: 1px solid rgba(66, 133, 244, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .time-warning {
        background: linear-gradient(145deg, rgba(245, 158, 11, 0.1), rgba(234, 179, 8, 0.05));
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #a855f7 0%, #6366f1 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        width: 100%;
    }
    
    .example-btn {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 0.5rem;
        border-radius: 8px;
        cursor: pointer;
        margin: 4px 0;
        transition: all 0.2s;
    }
    
    .example-btn:hover {
        background: rgba(168, 85, 247, 0.2);
        border-color: #a855f7;
    }
    
    .history-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
        gap: 10px;
        margin-top: 1rem;
    }
    
    .history-icon {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 10px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .history-icon:hover {
        background: rgba(168, 85, 247, 0.2);
        border-color: #a855f7;
        transform: translateY(-2px);
    }
    
    .history-icon .icon { font-size: 2rem; }
    .history-icon .label { font-size: 0.7rem; color: #94a3b8; margin-top: 5px; }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
    }
    
    .status-ready { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .status-generating { background: rgba(168, 85, 247, 0.2); color: #a855f7; }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "generated_video": None,
        "is_generating": False,
        "refined_prompt": None,
        "use_refined": False,
        "prompt_text": "",
        "regenerate_count": 0,
        "max_regenerate": 2,
        "last_prompt": None,
        "last_settings": None,
        # Error tracking for AI auto-fix
        "current_error": None,
        "error_analysis": None,
        "is_fixing_error": False,
        "error_fixed": False,
        # User authentication
        "session_token": None,
        "current_user": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    if "history" not in st.session_state:
        from utils.storage import load_history
        st.session_state.history = load_history()


def set_example_prompt(prompt: str):
    """Set the example prompt in session state."""
    st.session_state.prompt_text = prompt


def render_error_panel():
    """Display error panel with 'Auto fix with AI' button when errors occur."""
    if not st.session_state.get("current_error"):
        return
    
    error_msg = st.session_state.current_error
    analysis = st.session_state.get("error_analysis")
    
    # Error container with distinct styling
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.1));
        border: 1px solid rgba(239,68,68,0.4);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <span style="font-size: 1.5rem; margin-right: 0.5rem;">⚠️</span>
            <span style="font-size: 1.1rem; font-weight: 600; color: #ef4444;">Error Detected</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Show error message
    st.code(error_msg[:300] + "..." if len(error_msg) > 300 else error_msg, language="text")
    
    # Show analysis if available
    if analysis:
        st.markdown(f"""
        <div style="margin: 1rem 0; padding: 0.75rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
            <div style="font-size: 0.85rem; color: #94a3b8;">
                <strong>🔍 Root Cause:</strong> {analysis.get('root_cause', 'Unknown')}<br>
                <strong>💡 Suggested Fix:</strong> {analysis.get('fix_suggestion', 'Retry the operation')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🤖 Auto fix with AI", key="auto_fix_btn", use_container_width=True, type="primary"):
            st.session_state.is_fixing_error = True
            
            with st.spinner("🧠 Loading Qwen 3 Coder agent..."):
                try:
                    from models.error_fixing_agent import get_error_agent
                    agent = get_error_agent()
                    
                    # Try to load the model (downloads on first use)
                    st.info("📥 First time: Downloading Qwen 3 Coder model for offline use...")
                    model_loaded = agent.load_model(
                        progress_callback=lambda msg: st.info(f"🔄 {msg}")
                    )
                    
                    if not model_loaded:
                        st.warning("⚠️ Using rule-based fixes (model not available)")
                    
                    # Analyze and fix
                    if not analysis:
                        analysis = agent.analyze_error(error_msg, {"source": "ui"})
                    
                    fix_result = agent.attempt_auto_fix(analysis, {"source": "ui"})
                    
                    if fix_result.get("success"):
                        action = fix_result.get("action", "")
                        
                        if action == "switch_model":
                            st.success(f"✅ Fixed! Switched to: {fix_result.get('new_model', 'supported model')}")
                        elif action == "reduce_memory":
                            st.success("✅ Fixed! Reduced memory settings applied")
                        elif action == "retry":
                            st.success("✅ Ready to retry! Click Generate again.")
                        else:
                            st.success(f"✅ {fix_result.get('message', 'Fix applied!')}")
                        
                        # Clear error state
                        st.session_state.current_error = None
                        st.session_state.error_analysis = None
                        st.session_state.error_fixed = True
                        st.rerun()
                    else:
                        st.error(f"❌ {fix_result.get('message', 'Could not auto-fix')}")
                        
                except Exception as e:
                    st.error(f"❌ Auto-fix failed: {str(e)}")
            
            st.session_state.is_fixing_error = False
    
    with col2:
        if st.button("✖️ Dismiss", key="dismiss_error_btn", use_container_width=True):
            st.session_state.current_error = None
            st.session_state.error_analysis = None
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def capture_error(error_msg: str, context: dict = None):
    """Capture an error for display in the UI with auto-fix option."""
    from error_fixing_agent import get_error_agent
    
    st.session_state.current_error = str(error_msg)
    
    # Analyze error immediately
    agent = get_error_agent()
    analysis = agent.analyze_error(str(error_msg), context or {})
    st.session_state.error_analysis = analysis


def render_header():
    """Render the main header."""
    # Add a hidden-ish button that helps open sidebar if stuck
    if st.button("⚙️ Open Settings", key="open_settings_top", help="Click if sidebar is missing"):
        st.markdown(
            """
            <script>
                var iframe = window.parent.document;
                var buttons = iframe.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].getAttribute('data-testid') === 'stSidebarCollapsedControl' || 
                        buttons[i].getAttribute('kind') === 'header') {
                        buttons[i].click();
                        break;
                    }
                }
            </script>
            """,
            unsafe_allow_html=True
        )

    st.markdown('<h1 class="main-header">🎬 AI Video Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Transform your ideas into stunning videos with HuggingFace Local Models</p>', unsafe_allow_html=True)


def render_sidebar():
    """Render sidebar settings."""
    with st.sidebar:
        # Show profile section at top
        render_profile_sidebar()
        
        st.markdown("### ⚙️ Settings")

        try:
            import torch
            local_available = True
        except ImportError:
            local_available = False
        
        # Runtime Mode Selector
        if local_available:
            mode = st.radio(
                "🚀 Execution Mode",
                ["Local (Offline)", "Cloud (Faster)"],
                help="Local runs on your laptop (Slow/Private). Cloud runs on external servers (Fast)."
            )
        else:
            mode = "Cloud (Faster)"
            st.info("☁️ **Cloud Mode Only** - Local mode requires GPU/PyTorch which is not available on Streamlit Cloud.")
        
        st.markdown("---")
        
        if mode == "Local (Offline)":
            # Model Selection
            st.markdown("#### 🤖 AI Model")
            
            model_options = {
                "DAMO T2V (1.7B) - Offline": {
                    "id": "damo-vilab/text-to-video-ms-1.7b",
                    "vram": "~8GB",
                    "desc": "Alibaba DAMO model. Stable, well-tested. Works 100% offline.",
                    "icon": "📊"
                }
            }
            
            selected_model = st.selectbox(
                "Select Model",
                list(model_options.keys()),
                index=0,
                help="DAMO model - works offline"
            )
            
            model_info = model_options[selected_model]
            
            st.markdown(f"""
            <div class="model-card">
                <strong>{model_info['icon']} {selected_model}</strong><br>
                <span style="color:#94a3b8;font-size:0.8rem">Local • {model_info['vram']} VRAM • Offline</span><br>
                <span style="color:#64748b;font-size:0.75rem;margin-top:4px;display:block">{model_info['desc']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Offline Status Indicator
            st.info("💡 Model runs 100% locally. First run requires internet to download (~5GB). Afterwards works offline.")
            
        else:
            # Cloud Mode Info
            st.markdown("#### ☁️ Cloud Generator")
            st.markdown("""
            <div class="veo-card">
                <strong>⚡ HuggingFace Inference</strong><br>
                <span style="color:#1f2937;font-size:0.8rem">Remote • Fast Generation</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.warning("⚠️ Cloud mode requires a stable internet connection and valid API tokens.")

        st.markdown("---")
        
        st.markdown("---")
        
        # Aspect Ratio & Quality
        st.markdown("#### 📐 Format & Quality")
        
        # Aspect Ratio
        ratio_options = {
            "16:9 (Laptop/TV)": (16, 9),
            "9:16 (Mobile/Reels)": (9, 16),
            "1:1 (Square)": (1, 1),
            "4:3 (Classic)": (4, 3)
        }
        aspect_ratio = st.selectbox("Aspect Ratio", options=list(ratio_options.keys()), index=0)
        ar_val = ratio_options[aspect_ratio]
        
        # Quality (Resolution) - Dynamic based on AR
        quality_options = ["Low (Fast)", "Medium (Balanced)", "High (Slow)"]
        quality_setting = st.select_slider("Quality Preset", options=quality_options, value="Medium (Balanced)")
        
        # Base dimensions (approximate)
        if quality_setting == "Low (Fast)":
            base_dim = 384
        elif quality_setting == "Medium (Balanced)":
            base_dim = 512
        else:
            base_dim = 640
            
        # Calculate W/H maintaining AR
        if ar_val[0] > ar_val[1]: # Landscape
            width = base_dim
            height = int(base_dim * (ar_val[1] / ar_val[0]))
        elif ar_val[0] < ar_val[1]: # Portrait
            height = base_dim
            width = int(base_dim * (ar_val[0] / ar_val[1]))
        else: # Square
            width = base_dim
            height = base_dim
            
        # Ensure divisible by 16 (common ML requirement)
        width = (width // 16) * 16
        height = (height // 16) * 16
        
        st.caption(f"📏 Output Size: **{width}x{height}**")
        
        st.markdown("---")
        
        # Duration & FPS
        st.markdown("#### ⏱️ Duration & Motion")
        
        target_duration = st.select_slider(
            "Video Length (Seconds)", 
            options=[2, 3, 4, 5, 8], 
            value=4,
            help="Longer videos require more memory and time."
        )
        
        fps = st.slider("FPS (Smoothness)", 8, 24, 8) # Increased max FPS to 24 for smoother video
        
        # Calculate Frames
        # Frame limit for 8GB GPU to prevent OOM
        MAX_SAFE_FRAMES = 90
        num_frames = target_duration * fps
        
        if num_frames > MAX_SAFE_FRAMES:
            st.warning(f"⚠️ Limit: 90 frames (approx {MAX_SAFE_FRAMES/fps:.1f}s at {fps} FPS) to prevent crashing.")
            num_frames = MAX_SAFE_FRAMES
            real_duration = num_frames / fps
        else:
            real_duration = target_duration
            
        st.caption(f"🎞️ Generating **{num_frames} frames** (~{real_duration:.1f}s)")
        
        num_steps = st.slider("Quality Steps", 15, 50, 30)
        guidance = st.slider("Prompt Strength", 1.0, 15.0, 7.5, 0.5)
        
        st.markdown("---")
        
        # Video Style & Quality
        st.markdown("#### 🎨 Video Style & Quality")
        
        video_style = st.selectbox(
            "Video Style",
            ["🎬 Cinematic", "🎨 Anime", "📹 Normal"],
            index=0,
            help="Visual style to apply to your video"
        )
        
        # Extract style name
        style_name = video_style.split(" ")[1] if " " in video_style else video_style
        
        # Quality presets with resolution
        quality_presets = {
            "Normal": {"width": 256, "height": 256, "steps_boost": 0, "desc": "Fast preview", "vram": "4GB"},
            "Medium": {"width": 384, "height": 384, "steps_boost": 5, "desc": "Balanced", "vram": "6GB"},
            "Standard": {"width": 512, "height": 512, "steps_boost": 10, "desc": "Good quality", "vram": "8GB"},
            "HD 720p": {"width": 1280, "height": 720, "steps_boost": 15, "desc": "HD quality", "vram": "12GB"},
            "Full HD 1080p": {"width": 1920, "height": 1080, "steps_boost": 20, "desc": "Full HD", "vram": "16GB"},
            "QHD 1440p": {"width": 2560, "height": 1440, "steps_boost": 25, "desc": "Ultra HD", "vram": "24GB+"},
        }
        
        # HD options that require warning on local mode
        high_vram_options = ["HD 720p", "Full HD 1080p", "QHD 1440p"]
        
        # For cloud mode, show all options
        if mode == "Cloud (Faster)":
            quality = st.selectbox(
                "Quality Preset",
                list(quality_presets.keys()),
                index=4,  # Default to 1080p for cloud
                format_func=lambda x: f"{x} ({quality_presets[x]['width']}x{quality_presets[x]['height']})",
                help="☁️ Cloud supports all resolutions!"
            )
            selected_preset = quality_presets[quality]
            st.success(f"☁️ Cloud: {quality} - {selected_preset['desc']}")
        else:
            # Local mode - show warning for high resolution
            quality = st.selectbox(
                "Quality Preset",
                list(quality_presets.keys()),
                index=2,  # Default to Standard for local
                format_func=lambda x: f"{x} ({quality_presets[x]['width']}x{quality_presets[x]['height']})",
                help="Higher quality requires more VRAM"
            )
            selected_preset = quality_presets[quality]
            
            # Show crash warning for HD options on local
            if quality in high_vram_options:
                st.error(f"""
                ⚠️ **SYSTEM CRASH WARNING**
                
                **{quality}** requires **{selected_preset['vram']} VRAM**.
                
                Running this locally may cause:
                - 💥 Application crash
                - 🖥️ System freeze
                - ❌ Out of memory error
                
                **Recommendation:** Use **☁️ Cloud Mode** for HD/4K quality!
                """)
        
        # Apply quality preset to dimensions
        width = selected_preset["width"]
        height = selected_preset["height"]
        # Boost steps for higher quality
        num_steps = min(50, num_steps + selected_preset["steps_boost"])
        
        st.caption(f"🎯 Style: **{style_name}** | Resolution: **{width}x{height}** | Steps: **{num_steps}**")
        
        st.markdown("---")
        
        # Subtitle & Refinement
        st.markdown("#### 📝 Options")
        enable_subtitles = st.checkbox("🎯 Add Subtitles", value=True, help="Auto-generate subtitles on video")
        enable_refinement = st.checkbox("✨ Smart Prompt", value=False, help="Use AI to improve prompt")
        low_vram_mode = st.checkbox("🐢 Low VRAM Mode", value=True, help="Prevents crashing on 8GB GPUs")
        
        st.markdown("---")
        
        # Status Board
        st.markdown("#### ℹ️ Video Info")
        
        st.markdown(f"""
        <div style="font-size: 0.85rem; color: #94a3b8; background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px;">
            <div>📏 <strong>Resolution:</strong> {width}x{height}</div>
            <div>⏱️ <strong>Length:</strong> {real_duration:.1f}s</div>
            <div>🎞️ <strong>Frames:</strong> {num_frames}</div>
            <div>🚀 <strong>FPS:</strong> {fps}</div>
            <div style="margin-top:5px; border-top: 1px solid rgba(255,255,255,0.1); padding-top:5px;">
                <div>🔊 <strong>Audio:</strong> Silent (Model Restriction)</div>
                <div>📝 <strong>Subtitles:</strong> {"Enabled" if enable_subtitles else "Disabled"}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Device info
        try:
            import torch
            device = "🟢 CUDA (GPU)" if torch.cuda.is_available() else "🟡 CPU (Slow)"
        except ImportError:
            device = "☁️ Cloud Mode (No local GPU)"
        st.markdown(f"**Device:** {device}")
        
        # Cloud Status - Load persistence
        if not st.session_state.get("cloud_job_id"):
             from utils.storage import get_latest_cloud_job
             last_job = get_latest_cloud_job()
             if last_job:
                 st.session_state.cloud_job_id = last_job["id"]

        # Cloud Status Widget
        if st.session_state.get("cloud_job_id"):
            st.markdown("---")
            st.markdown("#### ☁️ Cloud Status")
            st.caption(f"Job: {st.session_state.cloud_job_id}")
            
            if st.button("🔄 Check Now"):
                with st.spinner("Checking cloud..."):
                    from utils.firebase_utils import get_job_status
                    data = get_job_status(st.session_state.cloud_job_id)
                    if data:
                        st.session_state.cloud_status = data
                    else:
                        st.error("Failed to fetch status")
            
            status = st.session_state.get("cloud_status", {}).get("status", "pending")
            st.markdown(f"**State:** `{status}`")
            
            if status == "completed":
                url = st.session_state.cloud_status.get("video_url")
                if url:
                    st.success("✨ Video Ready!")
                    st.video(url)
            elif status == "error":
                st.error(st.session_state.cloud_status.get("error", "Unknown Error"))
                
        return {
            "model": "modelscope" if mode == "Local (Offline)" else "cloud_v2",
            "model_id": model_info["id"] if mode == "Local (Offline)" else None,
            "quality": quality_setting,
            "quality_setting": quality_setting,
            "quality_preset": quality,  # Normal/Medium/Standard/Pro
            "video_style": style_name,  # Cinematic/Anime/Normal
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "num_steps": num_steps,
            "guidance": guidance,
            "fps": fps,
            "enable_subtitles": enable_subtitles,
            "enable_refinement": enable_refinement,
            "low_vram": low_vram_mode,
            "mode": mode,
        }


def generate_video(prompt: str, settings: dict, status_placeholder):
    """Generate video using selected engine."""
    
    # ----------------CLOUD MODE (HuggingFace Inference API)----------------
    if settings.get("mode") == "Cloud (Faster)":
        status_placeholder.markdown('<span class="status-badge status-generating">☁️ Connecting to HuggingFace Cloud...</span>', unsafe_allow_html=True)
        
        try:
            from hf_inference import generate_video_hf
            
            def hf_progress(msg):
                status_placeholder.markdown(f'<span class="status-badge status-generating">☁️ {msg}</span>', unsafe_allow_html=True)
            
            # Generate video using HuggingFace API (runs on their servers 24/7!)
            video_path = generate_video_hf(
                prompt=prompt,
                settings=settings,
                progress_callback=hf_progress
            )
            
            if video_path and os.path.exists(video_path):
                status_placeholder.markdown('<span class="status-badge status-ready">✅ Cloud Video Complete!</span>', unsafe_allow_html=True)
                
                # Save to history
                from utils.storage import save_to_history
                save_to_history(prompt, "huggingface_cloud", video_path, settings)
                
                return video_path
            else:
                status_placeholder.markdown('<span class="status-badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">❌ Cloud generation failed</span>', unsafe_allow_html=True)
                st.error("Cloud generation failed. The HuggingFace API may be busy or the model is loading.")
                st.info("💡 **Tip:** HuggingFace models may take 2-5 minutes to 'warm up' on first use. Try again in a few minutes!")
                return None
                
        except ImportError as e:
            st.error(f"⚠️ Missing dependency: {e}")
            st.info("Run: pip install requests")
            return None
        except Exception as e:
            st.error(f"❌ Cloud Error: {e}")
            return None
    
    # ----------------LOCAL MODE----------------
    try:
        # Get selected model name for display
        model_id = settings.get("model_id", "damo-vilab/text-to-video-ms-1.7b")
        model_name = model_id.split("/")[-1] if model_id else "text-to-video-ms-1.7b"
        status_placeholder.markdown(f'<span class="status-badge status-generating">⏳ Loading {model_name}...</span>', unsafe_allow_html=True)
        
        from modelscope import get_modelscope_generator
        generator = get_modelscope_generator()
        
        # Set the user-selected model
        if model_id:
            generator.set_model(model_id)
        
        def progress_callback(msg):
            status_placeholder.markdown(f'<span class="status-badge status-generating">⏳ {msg}</span>', unsafe_allow_html=True)
        
        frames = generator.generate(
            prompt=prompt,
            num_frames=settings["num_frames"],
            num_inference_steps=settings["num_steps"],
            guidance_scale=settings["guidance"],
            height=min(settings.get("height", 512), 512),  # ModelScope max 512
            width=min(settings.get("width", 512), 512),    # ModelScope max 512
            low_vram=settings.get("low_vram", True),
            enhance_prompt=True,  # Auto-enhance for quality
            progress_callback=progress_callback
        )

        # Resize frames to target resolution (Upscaling)
        target_w = settings.get("width", 256)
        target_h = settings.get("height", 256)
        # Only resize if meaningful difference to avoid blur on correct sizes
        if abs(target_w - 256) > 16 or abs(target_h - 256) > 16:
            status_placeholder.markdown(f'<span class="status-badge status-generating">🔍 Upscaling to {target_w}x{target_h}...</span>', unsafe_allow_html=True)
            import PIL.Image
            import numpy as np
            resized_frames = []
            for f in frames:
                # Convert to numpy array if needed
                if hasattr(f, 'numpy'):
                    f = f.numpy()
                elif not isinstance(f, np.ndarray):
                    f = np.array(f)
                
                # Handle float32 frames (0-1 or 0-255 range)
                if f.dtype in [np.float32, np.float64]:
                    if f.max() <= 1.0:
                        f = (f * 255).astype(np.uint8)
                    else:
                        f = f.clip(0, 255).astype(np.uint8)
                elif f.dtype != np.uint8:
                    f = f.astype(np.uint8)
                
                # Ensure 3D array (H, W, C)
                if f.ndim == 2:
                    f = np.stack([f, f, f], axis=-1)
                
                # Convert numpy -> PIL -> Resize -> numpy
                img = PIL.Image.fromarray(f)
                img = img.resize((target_w, target_h), PIL.Image.LANCZOS)
                resized_frames.append(np.array(img))
            frames = resized_frames

        # Add AI-generated subtitles
        if settings.get("enable_subtitles"):
            status_placeholder.markdown('<span class="status-badge status-generating">⏳ Generating subtitles...</span>', unsafe_allow_html=True)
            from subtitle_generator import generate_video_subtitles
            from subtitles import add_subtitles_to_frames
            
            # Generate contextual subtitles
            duration = settings["num_frames"] / settings["fps"]
            try:
                subtitles = generate_video_subtitles(
                    prompt=prompt,
                    duration_seconds=duration,
                    progress_callback=lambda msg: status_placeholder.markdown(f'<span class="status-badge status-generating">⏳ {msg}</span>', unsafe_allow_html=True)
                )
                
                # Apply subtitles to frames
                frames = add_subtitles_to_frames(frames, subtitles, settings["fps"])
            except Exception as sub_e:
                print(f"Subtitle Error: {sub_e}")
                st.warning(f"Subtitle generation failed, creating video without subtitles. Error: {sub_e}")
        
        # Save
        from video import ensure_output_dir, generate_filename, save_video_from_frames
        output_dir = ensure_output_dir()
        filename = generate_filename()
        output_path = str(output_dir / filename)
        save_video_from_frames(frames, output_path, fps=settings["fps"])
        
        # Save to history
       from storage import save_to_history
        save_to_history(prompt, "modelscope", output_path, settings)
        
        status_placeholder.markdown('<span class="status-badge status-ready">✅ Complete!</span>', unsafe_allow_html=True)
        return output_path
        
    except Exception as e:
        status_placeholder.markdown(f'<span class="status-badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">❌ {str(e)}</span>', unsafe_allow_html=True)
        st.error(f"Error: {str(e)}")
        return None


def render_prompt_section(settings):
    """Render the prompt input section."""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    # Examples row
    st.markdown("#### 💡 Quick Examples")
    example_prompts = [
        "A rocket launching into space with flames",
        "Ocean waves crashing on rocks at sunset",
        "A flower blooming in beautiful timelapse",
        "Northern lights dancing over snowy mountains",
        "A butterfly emerging from a cocoon",
        "Rain falling on a window at night"
    ]
    
    cols = st.columns(6)
    for i, ex in enumerate(example_prompts):
        with cols[i]:
            # Use simple text to avoid rendering issues
            if st.button(f"Ex {i+1}", key=f"ex_{i}", help=ex, use_container_width=True):
                st.session_state.prompt_text = ex
                st.rerun()
    
    st.markdown("---")
    
    # Main prompt input
    st.markdown("#### ✨ Enter Your Prompt")
    prompt = st.text_area(
        "Describe your video",
        value=st.session_state.prompt_text,
        placeholder="Describe the video you want to create...",
        height=100,
        label_visibility="collapsed"
    )
    
    # Update session state
    if prompt != st.session_state.prompt_text:
        st.session_state.prompt_text = prompt
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    time_msg = "⏱️ Local generation may take <strong>2-10 minutes</strong> depending on hardware"
    
    st.markdown(f"""
    <div class="time-warning">
        {time_msg}<br>
        <span style="font-size:0.8rem;color:#94a3b8">Quality: {settings['quality']} | Model: {settings['model'].upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    # Generate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_clicked = st.button(
            "🎬 Generate Video",
            use_container_width=True,
            disabled=not prompt or st.session_state.is_generating
        )
    
    status_placeholder = st.empty()
    
    # Handle regeneration trigger
    is_regenerating = st.session_state.is_generating and st.session_state.generated_video is None and st.session_state.get("last_prompt")
    
    if is_regenerating:
        # Use saved prompt and settings for regeneration
        prompt = st.session_state.last_prompt
        generate_clicked = True
        st.info(f"🔄 Regenerating video (attempt {st.session_state.regenerate_count}/{st.session_state.max_regenerate})...")
    
    if generate_clicked and prompt:
        st.session_state.is_generating = True
        
        # Save prompt for potential regeneration
        st.session_state.last_prompt = prompt
        
        # Initialize tracking variables
        original_prompt = prompt
        detected_lang = "en"
        translated_prompt = None
        analysis_data = None
        
        # Step 1: Multi-language Translation (TranslateGemma)
        try:
            status_placeholder.markdown('<span class="status-badge status-generating">🌐 Detecting language...</span>', unsafe_allow_html=True)
            from translator import get_translator
            translator = get_translator()
            
            translation_result = translator.translate_to_english(
                prompt,
                progress_callback=lambda msg: status_placeholder.markdown(f'<span class="status-badge status-generating">🌐 {msg}</span>', unsafe_allow_html=True)
            )
            
            detected_lang = translation_result.get("detected_language", "en")
            if translation_result.get("was_translated"):
                translated_prompt = translation_result.get("translated")
                prompt = translated_prompt  
                st.info(f"🌐 Detected: {detected_lang.upper()} → Translated to English")
        except Exception as e:
            error_msg = str(e)
            print(f"Translation skipped: {error_msg}")
            # Capture error for UI display if it's a model error
            if "model_not_supported" in error_msg or "not supported" in error_msg:
                capture_error(error_msg, {"function": "translate_to_english", "module": "translator"})
        
        # Step 2: LLAMA 4 Scout Analysis (Intent, Topic, Emotions)
        if settings.get("enable_refinement"):
            try:
                status_placeholder.markdown('<span class="status-badge status-generating">🧠 Analyzing with LLAMA 4 Scout...</span>', unsafe_allow_html=True)
                from llama_prompt_generator import get_llama_generator
                llama_gen = get_llama_generator()
                
                # Analyze prompt
                analysis_data = llama_gen.analyze_prompt(
                    prompt,
                    progress_callback=lambda msg: status_placeholder.markdown(f'<span class="status-badge status-generating">🧠 {msg}</span>', unsafe_allow_html=True)
                )
                
                # Generate enhanced video prompt
                enhanced_config = llama_gen.generate_video_prompt(
                    analysis_data,
                    prompt,
                    progress_callback=lambda msg: status_placeholder.markdown(f'<span class="status-badge status-generating">🧠 {msg}</span>', unsafe_allow_html=True)
                )
                
                # Apply LLAMA-generated settings
                if enhanced_config.get("prompt"):
                    prompt = enhanced_config["prompt"]
                if enhanced_config.get("fps"):
                    settings["fps"] = int(enhanced_config["fps"])
                if enhanced_config.get("duration_seconds"):
                    target_frames = int(enhanced_config["duration_seconds"] * settings["fps"])
                    settings["num_frames"] = min(target_frames, 90)  # Cap at max frames
                
                # Show analysis results
                st.markdown(f"""
                <div class="glass-card" style="padding: 1rem; margin-bottom: 1rem;">
                    <strong>🧠 LLAMA 4 Scout Analysis:</strong><br>
                    <span style="font-size:0.85rem;">
                        📌 <strong>Topic:</strong> {analysis_data.get('topic', 'N/A')} | 
                        💭 <strong>Emotions:</strong> {', '.join(analysis_data.get('emotions', ['N/A']))} | 
                        🎨 <strong>Style:</strong> {enhanced_config.get('style', 'Cinematic')}
                    </span><br>
                    <span style="font-size:0.8rem;color:#94a3b8;">Enhanced: "{prompt[:80]}..."</span>
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                print(f"LLAMA analysis skipped: {e}")
                # Fallback to legacy refiner
                from models.prompt_refiner import get_prompt_refiner
                refiner = get_prompt_refiner()
                refined_data = refiner.refine_to_json(
                    prompt, 
                    progress_callback=lambda msg: status_placeholder.markdown(f'<span class="status-badge status-generating">🧠 {msg}</span>', unsafe_allow_html=True)
                )
                if isinstance(refined_data, dict):
                    prompt = refined_data.get("prompt", prompt)
                    settings["num_steps"] = refined_data.get("num_inference_steps", settings["num_steps"])
        
        # Step 3: Save to Search History
        try:
            from search_history import save_search
            save_search(
                prompt=original_prompt,
                language_detected=detected_lang,
                translated_prompt=translated_prompt,
                intent=analysis_data.get("intent") if analysis_data else None,
                topic=analysis_data.get("topic") if analysis_data else None,
                emotions=analysis_data.get("emotions") if analysis_data else None
            )
        except Exception as e:
            print(f"Search history save skipped: {e}")
        
        # Step 4: Generate Video
        video_path = generate_video(prompt, settings, status_placeholder)
        
        if video_path:
            st.session_state.generated_video = video_path
            
            # Save to JSON history
            from storage import load_history
            st.session_state.history = load_history()
            
            # Step 5: Save to CSV Storage
            try:
                from csv_storage import save_video_to_csv
                source = "cloud" if settings.get("mode") == "Cloud (Faster)" else "local"
                save_video_to_csv(
                    prompt=original_prompt,
                    model=settings.get("model", "unknown"),
                    video_path=video_path,
                    settings=settings,
                    source=source
                )
            except Exception as e:
                print(f"CSV storage save skipped: {e}")
            st.session_state.is_generating = False
            st.rerun()
            
        st.session_state.is_generating = False
    
    return prompt


def render_video_player():
    """Render the video player with regenerate option."""
    if st.session_state.generated_video and os.path.exists(st.session_state.generated_video):
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### 🎥 Generated Video")
        
        video_file = open(st.session_state.generated_video, "rb")
        video_bytes = video_file.read()
        st.video(video_bytes)
        
        # Action buttons row
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.download_button(
                label="⬇️ Download",
                data=video_bytes,
                file_name=os.path.basename(st.session_state.generated_video),
                mime="video/mp4",
                use_container_width=True
            )
        
        with col2:
            # Regenerate button - only show if under max attempts
            regen_count = st.session_state.get("regenerate_count", 0)
            max_regen = st.session_state.get("max_regenerate", 2)
            remaining = max_regen - regen_count
            
            if remaining > 0:
                if st.button(
                    f"🔄 Regenerate ({remaining} left)",
                    key="regenerate_btn",
                    use_container_width=True,
                    help="Generate a new video with the same prompt"
                ):
                    st.session_state.regenerate_count += 1
                    st.session_state.is_generating = True
                    st.session_state.generated_video = None
                    st.rerun()
            else:
                st.button(
                    "🔄 No Regenerates Left",
                    key="regenerate_btn_disabled",
                    use_container_width=True,
                    disabled=True
                )
        
        with col3:
            if st.button("🆕 New Video", key="new_video_btn", use_container_width=True):
                # Reset regenerate count for new prompt
                st.session_state.regenerate_count = 0
                st.session_state.generated_video = None
                st.session_state.prompt_text = ""
                st.session_state.last_prompt = None
                st.session_state.last_settings = None
                st.rerun()
        
        # Show regenerate info
        if regen_count > 0:
            st.caption(f"🔄 Regeneration {regen_count}/{max_regen} complete")
        
        st.markdown('</div>', unsafe_allow_html=True)


def render_cloud_videos():
    """Render cloud-generated videos from cloud_outputs folder."""
    cloud_dir = "cloud_outputs"
    
    if not os.path.exists(cloud_dir):
        return
    
    # Get all mp4 files in cloud_outputs
    cloud_videos = [f for f in os.listdir(cloud_dir) if f.endswith('.mp4')]
    
    if not cloud_videos:
        return
    
    st.markdown("---")
    st.markdown("### ☁️ Cloud Generated Videos")
    
    # Sort by modification time (newest first)
    cloud_videos.sort(key=lambda x: os.path.getmtime(os.path.join(cloud_dir, x)), reverse=True)
    
    # Display in grid
    cols = st.columns(min(len(cloud_videos), 4))
    
    for i, video_file in enumerate(cloud_videos[:8]):  # Show max 8
        video_path = os.path.join(cloud_dir, video_file)
        
        with cols[i % 4]:
            # Show video ID (truncated)
            video_id = video_file.replace('.mp4', '')[:8]
            
            st.markdown(f"""
            <div class="glass-card" style="padding: 0.5rem; margin-bottom: 0.5rem; text-align: center;">
                <div style="font-size: 1.5rem;">☁️</div>
                <div style="font-size: 0.7rem; color: #94a3b8;">{video_id}...</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("▶️ Play", key=f"cloud_play_{video_id}", use_container_width=True):
                st.session_state.generated_video = os.path.abspath(video_path)
                st.rerun()
            
            # Add download button
            with open(video_path, "rb") as f:
                st.download_button(
                    "⬇️",
                    data=f.read(),
                    file_name=video_file,
                    mime="video/mp4",
                    key=f"cloud_dl_{video_id}",
                    use_container_width=True
                )


def render_history_icons():
    """Render history as icon grid - always visible."""
    st.markdown("---")
    st.markdown("### 📚 Video History")
    
    history = st.session_state.history
    
    if not history:
        # Empty state
        st.markdown("""
        <div style="
            background: rgba(255,255,255,0.03);
            border: 1px dashed rgba(255,255,255,0.15);
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            margin: 1rem 0;
        ">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎬</div>
            <div style="color: #94a3b8; font-size: 1rem;">No video generating history</div>
            <div style="color: #64748b; font-size: 0.8rem; margin-top: 0.5rem;">
                Your generated videos will appear here
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Icon grid
        cols = st.columns(min(len(history), 6))
        
        for i, entry in enumerate(history[:6]):
            with cols[i]:
                model_icon = {
                    "veo": "🌟",
                    "modelscope": "🎬",
                    "cogvideox": "🎥"
                }.get(entry.get('model', ''), "📹")
                
                # Create timestamp
                created = entry.get('created_at', '')
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = "..."
                else:
                    time_str = "..."
                
                st.markdown(f"""
                <div class="history-icon">
                    <div class="icon">{model_icon}</div>
                    <div class="label">{time_str}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if os.path.exists(entry.get('video_path', '')):
                    if st.button("▶️", key=f"play_{entry['id']}", use_container_width=True):
                        st.session_state.generated_video = entry['video_path']
                        st.rerun()


def main():
    """Main application."""
    init_session_state()
    
    # Check if user is logged in
    if not is_logged_in():
        render_login_page()
        return
    
    render_header()
    
    # Show error panel if there's an error
    render_error_panel()
    
    settings = render_sidebar()
    
    render_prompt_section(settings)
    render_video_player()
    render_cloud_videos()  # Show cloud-generated videos
    render_history_icons()
    
    st.markdown("---")
    
    # Show logged-in user info in footer
    user = get_current_user()
    user_name = user['name'] if user else 'Guest'
    st.markdown(
        f'<p style="text-align: center; color: #64748b; font-size: 0.85rem;">'
        f'👤 Logged in as <strong>{user_name}</strong> | '
        f'Powered by Alibaba DAMO (Local) | Built with Streamlit'
        f'</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

