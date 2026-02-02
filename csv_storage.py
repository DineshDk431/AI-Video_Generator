"""
CSV Storage Utility for Video Metadata.
Stores all generated videos (cloud and local) with JSON metadata in CSV format.
"""
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


VIDEOS_CSV = "outputs/videos.csv"
CSV_HEADERS = ["id", "prompt", "model", "settings_json", "video_path", "source", "created_at"]


def ensure_csv_storage():
    """Ensure the CSV file exists with headers."""
    Path("outputs").mkdir(exist_ok=True)
    if not os.path.exists(VIDEOS_CSV):
        with open(VIDEOS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


def get_next_id() -> int:
    """Get the next ID for a new entry."""
    ensure_csv_storage()
    try:
        with open(VIDEOS_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ids = [int(row.get("id", 0)) for row in reader if row.get("id", "").isdigit()]
            return max(ids) + 1 if ids else 1
    except Exception:
        return 1


def save_video_to_csv(
    prompt: str,
    model: str,
    video_path: str,
    settings: Optional[Dict] = None,
    source: str = "local"
) -> Dict:
    """
    Save video metadata to CSV file with JSON settings.
    
    Args:
        prompt: The prompt used for generation
        model: Model name (e.g., 'modelscope', 'cloud')
        video_path: Path to the generated video
        settings: Generation settings dictionary
        source: Source of generation ('local' or 'cloud')
    
    Returns:
        The saved entry as a dictionary
    """
    ensure_csv_storage()
    
    entry = {
        "id": get_next_id(),
        "prompt": prompt,
        "model": model,
        "settings_json": json.dumps(settings or {}),
        "video_path": video_path,
        "source": source,
        "created_at": datetime.now().isoformat()
    }
    
    with open(VIDEOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(entry)
    
    return entry


def load_videos_from_csv(limit: int = 50) -> List[Dict]:
    """
    Load all videos from CSV file.
    
    Args:
        limit: Maximum number of entries to return
    
    Returns:
        List of video entries with parsed settings
    """
    ensure_csv_storage()
    
    try:
        with open(VIDEOS_CSV, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            entries = []
            for row in reader:
                # Parse JSON settings
                try:
                    row["settings"] = json.loads(row.get("settings_json", "{}"))
                except json.JSONDecodeError:
                    row["settings"] = {}
                entries.append(row)
            
            # Return most recent first
            entries.reverse()
            return entries[:limit]
    except Exception:
        return []


def export_videos_csv_path() -> str:
    """Return the path to the videos CSV file for download."""
    ensure_csv_storage()
    return os.path.abspath(VIDEOS_CSV)
