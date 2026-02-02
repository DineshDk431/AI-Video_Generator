"""
HuggingFace Inference API for Video Generation.
This runs on HuggingFace's servers - no local GPU needed!
Works 24/7 even when your laptop is off.
"""
import os
import requests
import time
import base64
import tempfile
from typing import Optional, Callable

# HuggingFace API configuration
HF_API_URL = "https://api-inference.huggingface.co/models/"
HF_VIDEO_MODELS = {
    "damo-text-to-video": "damo-vilab/text-to-video-ms-1.7b",
    "zeroscope": "cerspense/zeroscope_v2_576w",  # Better quality, slower
}


class HuggingFaceVideoGenerator:
    """Generate videos using HuggingFace's Inference API (runs on their servers)."""
    
    def __init__(self, model_key: str = "damo-text-to-video"):
        """Initialize the generator with a specific model."""
        self.model_id = HF_VIDEO_MODELS.get(model_key, HF_VIDEO_MODELS["damo-text-to-video"])
        self.api_url = f"{HF_API_URL}{self.model_id}"
        self.hf_token = self._get_token()
        
    def _get_token(self) -> Optional[str]:
        """Get HuggingFace token from various sources."""
        # Try Streamlit secrets first
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'HF_TOKEN' in st.secrets:
                return st.secrets['HF_TOKEN']
        except:
            pass
        
        # Try environment variable
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if token:
            return token
            
        # Try .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv("HF_TOKEN")
            if token:
                return token
        except:
            pass
            
        return None
    
    def _get_headers(self) -> dict:
        """Get API headers with authorization."""
        headers = {"Content-Type": "application/json"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        return headers
    
    def generate(
        self,
        prompt: str,
        num_frames: int = 24,
        num_inference_steps: int = 25,
        height: int = 256,
        width: int = 256,
        negative_prompt: str = "",
        progress_callback: Optional[Callable] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Generate a video using HuggingFace Inference API.
        
        Returns:
            Path to saved video file, or None if failed.
        """
        if progress_callback:
            progress_callback("Connecting to HuggingFace servers...")
        
        # Prepare payload
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_frames": min(num_frames, 48),  # API limit
                "num_inference_steps": min(num_inference_steps, 50),
                "height": height,
                "width": width,
            }
        }
        
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt
        
        try:
            if progress_callback:
                progress_callback("Sending request to HuggingFace API...")
            
            # Make API request
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=300  # 5 minute timeout for video generation
            )
            
            # Handle model loading (503 = model is cold starting)
            retry_count = 0
            max_retries = 30  # 30 * 10s = 5 minutes max wait
            
            while response.status_code == 503 and retry_count < max_retries:
                retry_count += 1
                wait_time = 10
                
                try:
                    error_data = response.json()
                    if "estimated_time" in error_data:
                        wait_time = min(error_data["estimated_time"], 30)
                except:
                    pass
                
                if progress_callback:
                    progress_callback(f"Model loading on HuggingFace servers... (retry {retry_count}/{max_retries})")
                
                time.sleep(wait_time)
                response = requests.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=300
                )
            
            # Check for errors
            if response.status_code != 200:
                error_msg = f"HuggingFace API Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = f"HuggingFace API Error: {error_data['error']}"
                except:
                    error_msg = f"HuggingFace API Error: {response.text[:200]}"
                
                print(f"❌ {error_msg}")
                return None
            
            if progress_callback:
                progress_callback("Video generated! Saving...")
            
            # Save the video
            video_data = response.content
            
            # Create output directory
            output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"hf_video_{timestamp}.mp4"
            output_path = os.path.join(output_dir, filename)
            
            with open(output_path, "wb") as f:
                f.write(video_data)
            
            if progress_callback:
                progress_callback("Video saved successfully!")
            
            return output_path
            
        except requests.exceptions.Timeout:
            print("❌ HuggingFace API timeout - video generation took too long")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ HuggingFace API connection error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if the API is available and model is loaded."""
        try:
            response = requests.get(
                f"https://api-inference.huggingface.co/status/{self.model_id}",
                headers=self._get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except:
            return False


# Singleton instance
_hf_generator = None


def get_hf_generator(model_key: str = "damo-text-to-video") -> HuggingFaceVideoGenerator:
    """Get or create the HuggingFace video generator singleton."""
    global _hf_generator
    if _hf_generator is None:
        _hf_generator = HuggingFaceVideoGenerator(model_key)
    return _hf_generator


def generate_video_hf(
    prompt: str,
    settings: dict,
    progress_callback: Optional[Callable] = None
) -> Optional[str]:
    """
    High-level function to generate video via HuggingFace API.
    
    Args:
        prompt: Text description of the video
        settings: Dictionary with generation settings
        progress_callback: Optional callback for progress updates
        
    Returns:
        Path to generated video file, or None if failed
    """
    generator = get_hf_generator()
    
    # Apply video style to prompt
    video_style = settings.get("video_style", "Cinematic")
    style_prompts = {
        "Cinematic": "cinematic, film quality, dramatic lighting, professional, ",
        "Anime": "anime style, vibrant colors, japanese animation, detailed, ",
        "Normal": ""
    }
    enhanced_prompt = style_prompts.get(video_style, "") + prompt
    
    # Add quality terms
    if "quality" not in enhanced_prompt.lower():
        enhanced_prompt = f"high quality, detailed, {enhanced_prompt}"
    
    # Common negative prompt
    negative_prompt = "blurry, low quality, distorted, pixelated, ugly, bad anatomy, deformed, noisy, grainy, watermark, text"
    
    return generator.generate(
        prompt=enhanced_prompt,
        num_frames=settings.get("num_frames", 24),
        num_inference_steps=settings.get("num_steps", 25),
        height=min(settings.get("height", 256), 512),  # API limit
        width=min(settings.get("width", 256), 512),    # API limit
        negative_prompt=negative_prompt,
        progress_callback=progress_callback
    )
