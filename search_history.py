"""
User Search History Module.
Tracks all user input prompts with timestamps and language information.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


SEARCH_HISTORY_FILE = "outputs/search_history.json"


def ensure_search_storage():
    """Ensure the search history file exists."""
    Path("outputs").mkdir(exist_ok=True)
    if not os.path.exists(SEARCH_HISTORY_FILE):
        with open(SEARCH_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def save_search(
    prompt: str,
    language_detected: str = "en",
    translated_prompt: Optional[str] = None,
    intent: Optional[str] = None,
    topic: Optional[str] = None,
    emotions: Optional[List[str]] = None
) -> Dict:
    """
    Save a user search to history.
    
    Args:
        prompt: Original user input
        language_detected: Detected language code
        translated_prompt: English translation (if translated)
        intent: Detected intent from LLAMA analysis
        topic: Detected topic from LLAMA analysis
        emotions: List of detected emotions
    
    Returns:
        The saved search entry
    """
    ensure_search_storage()
    
    history = []
    try:
        with open(SEARCH_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        history = []
    
    entry = {
        "id": len(history) + 1,
        "original_prompt": prompt,
        "language_detected": language_detected,
        "translated_prompt": translated_prompt,
        "intent": intent,
        "topic": topic,
        "emotions": emotions or [],
        "created_at": datetime.now().isoformat()
    }
    
    # Add to beginning (most recent first)
    history.insert(0, entry)
    
    # Keep last 100 searches
    history = history[:100]
    
    with open(SEARCH_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    return entry


def get_search_history(limit: int = 50) -> List[Dict]:
    """
    Get recent search history.
    
    Args:
        limit: Maximum number of entries to return
    
    Returns:
        List of search history entries
    """
    ensure_search_storage()
    
    try:
        with open(SEARCH_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            return history[:limit]
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def clear_search_history():
    """Clear all search history."""
    ensure_search_storage()
    with open(SEARCH_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
