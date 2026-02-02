"""
Model utilities and initialization for AI Video Generator.
"""
import os
import torch
from dotenv import load_dotenv

load_dotenv()

# Get HuggingFace token
HF_TOKEN = os.getenv("HF_TOKEN")

def get_device():
    """Get the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def get_torch_dtype():
    """Get optimal torch dtype based on device."""
    if torch.cuda.is_available():
        return torch.float16
    return torch.float32

DEVICE = get_device()
DTYPE = get_torch_dtype()

# Available models
AVAILABLE_MODELS = {
    "modelscope": {
        "name": "Alibaba DAMO T2V",
        "repo": "damo-vilab/text-to-video-ms-1.7b",
        "description": "Alibaba DAMO text-to-video synthesis model",
        "vram": "~8GB",
        "type": "text2video"
    }
}
