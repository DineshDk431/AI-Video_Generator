"""
Subtitle generation and overlay utilities for video generation.
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np


def get_font(size: int = 32):
    """Get a suitable font for subtitles."""
    # Try common fonts
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Fallback to default
    return ImageFont.load_default()


def add_subtitle_to_frame(
    frame: Image.Image,
    text: str,
    position: str = "bottom",
    font_size: int = 24,
    text_color: tuple = (255, 255, 255),
    bg_color: tuple = (0, 0, 0, 180),
    padding: int = 10
) -> Image.Image:
    """
    Add subtitle text to a single frame.
    
    Args:
        frame: PIL Image frame
        text: Subtitle text
        position: "bottom", "top", or "center"
        font_size: Font size in pixels
        text_color: RGB tuple for text color
        bg_color: RGBA tuple for background
        padding: Padding around text
    
    Returns:
        Frame with subtitle overlay
    """
    # Convert to RGBA for transparency
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    
    # Create overlay
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = get_font(font_size)
    
    # Calculate text size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position
    x = (frame.width - text_width) // 2
    
    if position == "bottom":
        y = frame.height - text_height - padding * 3
    elif position == "top":
        y = padding * 2
    else:  # center
        y = (frame.height - text_height) // 2
    
    # Draw background rectangle
    bg_rect = [
        x - padding,
        y - padding,
        x + text_width + padding,
        y + text_height + padding
    ]
    draw.rectangle(bg_rect, fill=bg_color)
    
    # Draw text
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Composite
    result = Image.alpha_composite(frame, overlay)
    return result.convert("RGB")


def add_subtitles_to_video(
    frames: list,
    subtitle_text: str,
    start_frame: int = 0,
    end_frame: int = None,
    **kwargs
) -> list:
    """
    Add subtitles to video frames.
    
    Args:
        frames: List of PIL Image frames
        subtitle_text: Text to display
        start_frame: Frame to start subtitle
        end_frame: Frame to end subtitle (None = all frames)
        **kwargs: Additional args for add_subtitle_to_frame
    
    Returns:
        List of frames with subtitles
    """
    if end_frame is None:
        end_frame = len(frames)
    
    result_frames = []
    for i, frame in enumerate(frames):
        if isinstance(frame, np.ndarray):
            frame = Image.fromarray(frame)
        
        if start_frame <= i < end_frame:
            frame = add_subtitle_to_frame(frame, subtitle_text, **kwargs)
        
        result_frames.append(frame)
    
    return result_frames


def generate_timed_subtitles(
    frames: list,
    subtitles: list,
    fps: int = 8
) -> list:
    """
    Add multiple timed subtitles to video.
    
    Args:
        frames: List of PIL Image frames
        subtitles: List of dicts with 'text', 'start_time', 'end_time' (in seconds)
        fps: Frames per second
    
    Returns:
        Frames with subtitles
    """
    result_frames = []
    
    for i, frame in enumerate(frames):
        if isinstance(frame, np.ndarray):
            frame = Image.fromarray(frame)
        
        current_time = i / fps
        
        # Find active subtitle
        active_subtitle = None
        for sub in subtitles:
            if sub['start_time'] <= current_time < sub['end_time']:
                active_subtitle = sub['text']
                break
        
        if active_subtitle:
            frame = add_subtitle_to_frame(frame, active_subtitle)
        
        result_frames.append(frame)
    
    return result_frames


def parse_subtitle_from_prompt(prompt: str) -> list:
    """
    Generate simple subtitles from prompt for display.
    Splits long prompts into multiple subtitle segments.
    
    Args:
        prompt: The video prompt text
    
    Returns:
        List of subtitle dicts with timing
    """
    # Split into chunks of ~50 chars
    words = prompt.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) > 50:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += len(word) + 1
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    subtitles = []
    time_per_chunk = 2.0  # 2 seconds per chunk
    for i, chunk in enumerate(chunks):
        subtitles.append({
            "text": chunk,
            "start_time": i * time_per_chunk,
            "end_time": (i + 1) * time_per_chunk
        })
    return subtitles


def add_subtitles_to_frames(
    frames: list,
    subtitles: list,
    fps: int = 8,
    position: str = "bottom",
    font_size: int = 20
) -> list:
    """
    Add AI-generated subtitles to video frames.
    Works with subtitle format from TranslateGemma: [{"start": 0.0, "end": 2.0, "text": "..."}]
    
    Args:
        frames: List of frames (PIL Image or numpy array)
        subtitles: List of subtitle dicts with 'start', 'end', 'text' keys
        fps: Frames per second
        position: Subtitle position ("bottom", "top", "center")
        font_size: Font size for subtitles
    
    Returns:
        List of frames with subtitles overlay
    """
    result_frames = []
    
    for i, frame in enumerate(frames):
        # Convert numpy to PIL if needed
        if isinstance(frame, np.ndarray):
            frame = Image.fromarray(frame)
        
        current_time = i / fps
        
        # Find active subtitle for this frame
        active_text = None
        for sub in subtitles:
            start = sub.get('start', sub.get('start_time', 0))
            end = sub.get('end', sub.get('end_time', 0))
            
            if start <= current_time < end:
                active_text = sub.get('text', '')
                break
        
        # Add subtitle if active
        if active_text:
            frame = add_subtitle_to_frame(
                frame, 
                active_text, 
                position=position,
                font_size=font_size
            )
        
        result_frames.append(frame)
    
    return result_frames

