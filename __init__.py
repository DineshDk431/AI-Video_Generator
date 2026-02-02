"""
Utilities for memory management and common tasks.
"""
import torch
import gc
import os

def clean_memory():
    """Aggressively clean CUDA cache and garbage collect."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    gc.collect()

def get_device():
    """Get best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"
