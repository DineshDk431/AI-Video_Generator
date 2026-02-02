"""
Local storage utilities for video history.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


HISTORY_FILE = "outputs/history.json"


def ensure_storage():
    """Ensure storage directory and file exist."""
    Path("outputs").mkdir(exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)


def load_history() -> List[Dict]:
    """Load generation history."""
    ensure_storage()
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_to_history(
    prompt: str,
    model: str,
    video_path: str,
    settings: Optional[Dict] = None
) -> Dict:
    """
    Save generation to history.
    
    Args:
        prompt: The prompt used
        model: Model name used
        video_path: Path to generated video
        settings: Generation settings
    
    Returns:
        The saved history entry
    """
    history = load_history()
    
    entry = {
        "id": len(history) + 1,
        "prompt": prompt,
        "model": model,
        "video_path": video_path,
        "settings": settings or {},
        "created_at": datetime.now().isoformat()
    }
    
    history.insert(0, entry)  # Most recent first
    
    # Keep only last 50 entries
    history = history[:50]
    
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
    
    return entry


def delete_from_history(entry_id: int) -> bool:
    """Delete an entry from history."""
    history = load_history()
    
    for i, entry in enumerate(history):
        if entry.get("id") == entry_id:
            # Delete video file too
            video_path = entry.get("video_path")
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            
            history.pop(i)
            
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
            
            return True
    
    return False


def clear_history() -> None:
    """Clear all history and videos."""
    history = load_history()
    
    # Delete all video files
    for entry in history:
        video_path = entry.get("video_path")
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
    
    # Clear history file
    # Clear history file
    with open(HISTORY_FILE, "w") as f:
        json.dump([], f)


# ---------------- CLOUD QUEUE STORAGE ----------------

CLOUD_QUEUE_FILE = "outputs/cloud_queue.json"

def save_cloud_job_id(job_id: str, prompt: str) -> None:
    """Save a cloud job ID to persistent storage."""
    ensure_storage()
    queue = []
    
    if os.path.exists(CLOUD_QUEUE_FILE):
        try:
            with open(CLOUD_QUEUE_FILE, "r") as f:
                queue = json.load(f)
        except:
            queue = []
            
    # Add new job
    queue.insert(0, {
        "id": job_id,
        "prompt": prompt,
        "created_at": datetime.now().isoformat(),
        "status": "pending"
    })
    
    # Keep last 10
    queue = queue[:10]
    
    with open(CLOUD_QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)

def get_latest_cloud_job() -> Optional[Dict]:
    """Get the most recent cloud job."""
    if os.path.exists(CLOUD_QUEUE_FILE):
        try:
            with open(CLOUD_QUEUE_FILE, "r") as f:
                queue = json.load(f)
                if queue:
                    return queue[0]
        except:
            return None
    return None
