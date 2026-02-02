"""
Video processing utilities.
"""
import os
import imageio
from datetime import datetime
from pathlib import Path


def ensure_output_dir():
    """Ensure outputs directory exists."""
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    return output_dir


def generate_filename(prefix: str = "video") -> str:
    """Generate unique filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.mp4"


def save_video_from_frames(frames, output_path: str, fps: int = 8):
    """
    Save video frames to MP4 file.
    
    Args:
        frames: List of PIL Images or numpy arrays
        output_path: Path to save the video
        fps: Frames per second
    
    Returns:
        Path to saved video
    """
    import numpy as np
    from PIL import Image
    
    # Convert frames to numpy arrays if needed
    numpy_frames = []
    for frame in frames:
        if isinstance(frame, Image.Image):
            frame = np.array(frame)
        elif hasattr(frame, 'numpy'):
            # Handle torch tensors
            frame = frame.numpy()
        elif not isinstance(frame, np.ndarray):
            frame = np.array(frame)
        
        # Handle float32/float64 frames from diffusion models
        if frame.dtype in [np.float32, np.float64]:
            # Check if range is 0-1 or 0-255
            if frame.max() <= 1.0:
                frame = (frame * 255).astype(np.uint8)
            else:
                frame = frame.clip(0, 255).astype(np.uint8)
        elif frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        
        # Ensure 3D array (H, W, C)
        if frame.ndim == 2:
            frame = np.stack([frame, frame, frame], axis=-1)
        
        numpy_frames.append(frame)
    
    # Write video
    writer = imageio.get_writer(output_path, fps=fps, codec='libx264')
    for frame in numpy_frames:
        writer.append_data(frame)
    writer.close()
    
    return output_path


def get_video_thumbnail(video_path: str) -> bytes:
    """Extract first frame as thumbnail."""
    import numpy as np
    from PIL import Image
    import io
    
    reader = imageio.get_reader(video_path)
    first_frame = reader.get_data(0)
    reader.close()
    
    # Convert to PIL and resize
    img = Image.fromarray(first_frame)
    img.thumbnail((200, 200))
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
