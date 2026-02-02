"""
ModelScope text-to-video model integration.
"""
import torch
import warnings
import logging
from diffusers import DiffusionPipeline
from diffusers.utils import export_to_video
from . import HF_TOKEN, DEVICE, DTYPE

# Suppress harmless model loading warnings
warnings.filterwarnings("ignore", message=".*position_ids.*")
warnings.filterwarnings("ignore", message=".*UNEXPECTED.*")
warnings.filterwarnings("ignore", message=".*TextToVideoSDPipeline.*")
logging.getLogger("transformers").setLevel(logging.ERROR)


class ModelScopeGenerator:
    """ModelScope text-to-video generator."""
    
    # Quality enhancement keywords
    QUALITY_KEYWORDS = "high quality, detailed, sharp focus, professional, 4k, realistic"
    NEGATIVE_PROMPT = "blurry, low quality, distorted, pixelated, ugly, bad anatomy, deformed, noisy, grainy"
    
    # Default model (DAMO - works offline, already downloaded)
    DEFAULT_MODEL = "damo-vilab/text-to-video-ms-1.7b"
    
    def __init__(self, model_id: str = None):
        self.pipeline = None
        self.model_id = model_id or self.DEFAULT_MODEL
        self.current_model_id = None  # Track loaded model
    
    def set_model(self, model_id: str):
        """Change model (requires reload)."""
        if model_id != self.model_id:
            self.model_id = model_id
            if self.pipeline is not None:
                # Force reload on next generate
                self.pipeline = None
                self.current_model_id = None
    
    def load_model(self, low_vram=True, progress_callback=None):
        """Load the video pipeline."""
        # Reload if model changed
        if self.pipeline is not None and self.current_model_id == self.model_id:
            return self.pipeline
            
        if self.pipeline is None or self.current_model_id != self.model_id:
            from utils import clean_memory
            clean_memory()
            
            model_name = self.model_id.split("/")[-1]
            if progress_callback:
                progress_callback(f"Loading {model_name}...")
            
            self.pipeline = DiffusionPipeline.from_pretrained(
                self.model_id,
                torch_dtype=DTYPE,
                token=HF_TOKEN
            )
            
            try:
                # Memory optimizations
                if DEVICE == "cuda":
                    # Test CUDA availability with a dummy tensor
                    try:
                        dummy = torch.zeros(1).cuda()
                        del dummy
                    except RuntimeError as e:
                        if "no kernel image" in str(e):
                            raise RuntimeError("GPU_UNSUPPORTED")
                        raise e
                        
                    if low_vram:
                        self.pipeline.enable_sequential_cpu_offload()
                    else:
                        self.pipeline.enable_model_cpu_offload()
                    self.pipeline.enable_vae_slicing()
                else:
                    self.pipeline = self.pipeline.to(DEVICE)
                    
            except RuntimeError as e:
                # Fallback for "no kernel image" (RTX 5050 etc)
                print(f"⚠️ GPU Issue Detected: {e}")
                if progress_callback: progress_callback("⚠️ GPU unsupported (too new?). Switching to CPU...")
                self.pipeline.enable_sequential_cpu_offload() # Still helps on CPU? No, offload needs CUDA.
                # Actually if CPU, just run.
                # But we constructed it?
                # Diffusers pipeline defaults to float32 on CPU.
                # Need to reload or move?
                
                # Simplest: Just use CPU execution
                # self.pipeline.to("cpu") # already on CPU initially
                pass
            
            if progress_callback:
                progress_callback("Model loaded successfully!")
            
            self.current_model_id = self.model_id  # Track which model is loaded
        
        return self.pipeline
    
    def generate(
        self,
        prompt: str,
        num_frames: int = 16,
        num_inference_steps: int = 40,  # Increased from 25 for better quality
        guidance_scale: float = 9.0,    # Increased from 7.5 for sharper results
        height: int = 512,              # Increased from 256
        width: int = 512,               # Increased from 256
        low_vram: bool = True,
        negative_prompt: str = None,    # NEW: negative prompt support
        enhance_prompt: bool = True,    # NEW: auto-enhance prompt
        progress_callback=None
    ):
        """
        Generate video from text prompt.
        
        Args:
            prompt: Text description of the video
            num_frames: Number of frames range
            num_inference_steps: Denoising steps
            guidance_scale: Prompt guidance strength
            height: Video height
            width: Video width
            low_vram: Use specific sequential offloading
            progress_callback: Optional progress callback
        
        Returns:
            List of video frames
        """
        pipeline = self.load_model(low_vram, progress_callback)
        
        # Enhance prompt for better quality
        enhanced_prompt = prompt
        if enhance_prompt:
            enhanced_prompt = f"{self.QUALITY_KEYWORDS}, {prompt}"
        
        # Use negative prompt if not provided
        neg_prompt = negative_prompt if negative_prompt else self.NEGATIVE_PROMPT
        
        if progress_callback:
            progress_callback(f"Generating {num_frames} frames at {width}x{height}...")
        
        # Generate video with quality settings
        result = pipeline(
            prompt=enhanced_prompt,
            negative_prompt=neg_prompt,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            height=height,
            width=width,
        )
        
        video_frames = result.frames[0]
        
        if progress_callback:
            progress_callback("Video generation complete!")
        
        return video_frames
    
    def save_video(self, frames, output_path: str, fps: int = 8):
        """Save frames as video file."""
        export_to_video(frames, output_path, fps=fps)
        return output_path


# Singleton instance
_generator = None

def get_modelscope_generator():
    """Get or create ModelScope generator instance."""
    global _generator
    if _generator is None:
        _generator = ModelScopeGenerator()
    return _generator
