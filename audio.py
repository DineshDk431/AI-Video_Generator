import os
import subprocess
import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio(video_path: str, output_path: str = None, format: str = "wav") -> str:
    """
    Extract audio from a video file.
    
    Args:
        video_path: Path to input video
        output_path: Path for output audio (auto-generated if None)
        format: Audio format (wav, mp3, aac)
    
    Returns:
        Path to extracted audio file
    """
    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_audio.{format}"
    
    cmd = [
        FFMPEG_EXE,
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "pcm_s16le" if format == "wav" else format,
        "-ar", "16000",  # 16kHz sample rate (good for speech)
        "-ac", "1",  # Mono
        "-y",  # Overwrite
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def add_audio_to_video(video_path: str, audio_path: str, output_path: str = None) -> str:

    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_with_audio.mp4"
    
    cmd = [
        FFMPEG_EXE,
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",  # Copy video stream
        "-c:a", "aac",   # Encode audio as AAC
        "-shortest",     # End when shortest stream ends
        "-y",
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def add_subtitles_to_video(video_path: str, subtitle_path: str, output_path: str = None, burn: bool = True) -> str:

    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_subtitled.mp4"
    
    if burn:
        # Burn subtitles into video frames
        # Need to escape special chars in path for ffmpeg filter
        escaped_path = subtitle_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            FFMPEG_EXE,
            "-i", video_path,
            "-vf", f"subtitles='{escaped_path}'",
            "-c:a", "copy",
            "-y",
            output_path
        ]
    else:
        # Add subtitle as separate track
        cmd = [
            FFMPEG_EXE,
            "-i", video_path,
            "-i", subtitle_path,
            "-c:v", "copy",
            "-c:a", "copy",
            "-c:s", "mov_text",
            "-y",
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def create_srt_file(subtitles: list, output_path: str) -> str:
    """
    Create an SRT subtitle file from subtitle segments.
    
    Args:
        subtitles: List of dicts with 'start', 'end', 'text' keys
        output_path: Path to save SRT file
    
    Returns:
        Path to created SRT file
    """
    def format_time(seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i, sub in enumerate(subtitles, 1):
            start = format_time(sub["start"])
            end = format_time(sub["end"])
            text = sub["text"]
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
    
    return output_path


def get_video_duration(video_path: str) -> float:
    """Get duration of a video in seconds."""
    cmd = [
        FFMPEG_EXE,
        "-i", video_path,
        "-f", "null",
        "-"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    # Parse duration from stderr
    import re
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
    if match:
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return 0.0


def process_video_with_subtitles(video_path: str, subtitles: list, output_path: str = None) -> str:
    """
    Complete workflow: add subtitles to video and burn them in.
    
    Args:
        video_path: Path to input video
        subtitles: List of subtitle segments
        output_path: Path for final output
    
    Returns:
        Path to processed video
    """
    import tempfile
    
    # Create temporary SRT file
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w") as f:
        srt_path = f.name
    
    try:
        # Create SRT from subtitles
        create_srt_file(subtitles, srt_path)
        
        # Burn subtitles into video
        result = add_subtitles_to_video(video_path, srt_path, output_path, burn=True)
        return result
    finally:
        # Cleanup temp file
        if os.path.exists(srt_path):
            os.remove(srt_path)
