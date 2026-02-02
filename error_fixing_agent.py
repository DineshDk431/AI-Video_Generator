"""
Qwen 3 Coder Error-Fixing Agent.
Automatically detects and fixes errors in the video generation workflow.
Downloads model for offline use after first internet connection.
"""
import os
import json
import traceback
from typing import Dict, Optional, Callable
from pathlib import Path

# Model path for offline use
MODEL_CACHE_DIR = Path("models/qwen3_coder_cache")
MODEL_ID = "Qwen/Qwen3-Coder-1.5B"  # Lightweight coder model


class ErrorFixingAgent:
    """Agent that automatically detects and attempts to fix workflow errors."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.error_history = []
        self.fix_attempts = 0
        self.max_fix_attempts = 3
        
    def load_model(self, progress_callback: Optional[Callable] = None):
        """Load the Qwen 3 Coder model. Downloads on first use, then runs offline."""
        if self.is_loaded:
            return True
            
        try:
            if progress_callback:
                progress_callback("Loading Qwen 3 Coder agent...")
            
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Check for HF token
            from . import HF_TOKEN
            token = HF_TOKEN or os.getenv("HF_TOKEN")
            
            # Create cache directory
            MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            
            if progress_callback:
                progress_callback("Downloading model (first time only)...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                MODEL_ID,
                token=token,
                cache_dir=str(MODEL_CACHE_DIR),
                trust_remote_code=True
            )
            
            # Load in 4-bit for efficiency
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID,
                token=token,
                cache_dir=str(MODEL_CACHE_DIR),
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.is_loaded = True
            if progress_callback:
                progress_callback("Qwen 3 Coder agent ready!")
            return True
            
        except Exception as e:
            print(f"Error loading Qwen 3 Coder: {e}")
            return False
    
    def analyze_error(
        self, 
        error_message: str, 
        error_context: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Analyze an error and suggest fixes.
        
        Args:
            error_message: The error message / traceback
            error_context: Context about where the error occurred
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with analysis and suggested fixes
        """
        # Store error for learning
        self.error_history.append({
            "error": error_message,
            "context": error_context,
            "timestamp": self._get_timestamp()
        })
        
        # Try to fix with loaded model, or use rule-based fallback
        if self.is_loaded and self.model is not None:
            return self._analyze_with_model(error_message, error_context, progress_callback)
        else:
            return self._analyze_with_rules(error_message, error_context)
    
    def _analyze_with_model(
        self, 
        error_message: str, 
        error_context: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """Use Qwen 3 Coder to analyze error."""
        import torch
        
        if progress_callback:
            progress_callback("Analyzing error with Qwen 3 Coder...")
        
        system_prompt = """You are an expert Python debugger. Analyze the error and provide:
1. Root cause of the error
2. Specific fix to apply
3. Whether the error is recoverable

Respond in JSON format only."""

        user_prompt = f"""Error Message:
{error_message}

Context:
- Function: {error_context.get('function', 'unknown')}
- Module: {error_context.get('module', 'unknown')}
- Parameters: {json.dumps(error_context.get('params', {}), indent=2)}

Provide analysis as JSON with keys: root_cause, fix_suggestion, is_recoverable, fix_code"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            input_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            inputs = self.tokenizer(input_text, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=500,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Parse JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                analysis = json.loads(response[start:end])
                return analysis
                
        except Exception as e:
            print(f"Model analysis failed: {e}")
        
        # Fallback to rules
        return self._analyze_with_rules(error_message, error_context)
    
    def _analyze_with_rules(self, error_message: str, error_context: Dict) -> Dict:
        """Rule-based error analysis fallback."""
        error_lower = error_message.lower()
        
        # Common error patterns and fixes
        if "model_not_supported" in error_lower or "not supported by any provider" in error_lower:
            return {
                "root_cause": "The specified model is not available on HuggingFace Inference API",
                "fix_suggestion": "Switch to a supported model like Qwen/Qwen2.5-72B-Instruct or mistralai/Mistral-7B-Instruct-v0.3",
                "is_recoverable": True,
                "auto_fix": "switch_model"
            }
        
        elif "cuda" in error_lower and "out of memory" in error_lower:
            return {
                "root_cause": "GPU memory exhausted",
                "fix_suggestion": "Reduce batch size, use CPU offloading, or restart the application",
                "is_recoverable": True,
                "auto_fix": "reduce_memory"
            }
        
        elif "connection" in error_lower or "timeout" in error_lower:
            return {
                "root_cause": "Network connection issue",
                "fix_suggestion": "Check internet connection and retry",
                "is_recoverable": True,
                "auto_fix": "retry"
            }
        
        elif "firebase" in error_lower or "firestore" in error_lower:
            return {
                "root_cause": "Firebase/Firestore connection error",
                "fix_suggestion": "Check Firebase configuration and service account key",
                "is_recoverable": True,
                "auto_fix": "retry_firebase"
            }
        
        elif "token" in error_lower and ("invalid" in error_lower or "expired" in error_lower):
            return {
                "root_cause": "Invalid or expired authentication token",
                "fix_suggestion": "Update HF_TOKEN in .env file",
                "is_recoverable": False,
                "auto_fix": None
            }
        
        return {
            "root_cause": "Unknown error",
            "fix_suggestion": "Check logs and try again",
            "is_recoverable": True,
            "auto_fix": "retry"
        }
    
    def attempt_auto_fix(
        self, 
        analysis: Dict, 
        error_context: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Attempt to automatically fix the error based on analysis.
        
        Returns:
            Dictionary with success status and result
        """
        if self.fix_attempts >= self.max_fix_attempts:
            return {
                "success": False,
                "message": "Maximum fix attempts reached. Manual intervention required."
            }
        
        self.fix_attempts += 1
        auto_fix = analysis.get("auto_fix")
        
        if progress_callback:
            progress_callback(f"Attempting auto-fix: {auto_fix}...")
        
        if auto_fix == "switch_model":
            return {
                "success": True,
                "action": "switch_model",
                "new_model": "Qwen/Qwen2.5-72B-Instruct",
                "message": "Switched to supported model"
            }
        
        elif auto_fix == "reduce_memory":
            return {
                "success": True,
                "action": "reduce_memory",
                "settings": {"low_vram": True, "num_frames": 32},
                "message": "Reduced memory usage settings"
            }
        
        elif auto_fix == "retry":
            return {
                "success": True,
                "action": "retry",
                "message": "Ready to retry operation"
            }
        
        elif auto_fix == "retry_firebase":
            return {
                "success": True,
                "action": "retry_firebase",
                "message": "Ready to retry Firebase connection"
            }
        
        return {
            "success": False,
            "message": "No automatic fix available"
        }
    
    def reset_fix_attempts(self):
        """Reset the fix attempt counter after successful operation."""
        self.fix_attempts = 0
    
    def get_error_statistics(self) -> Dict:
        """Get statistics about errors encountered."""
        return {
            "total_errors": len(self.error_history),
            "fix_attempts": self.fix_attempts,
            "recent_errors": self.error_history[-5:] if self.error_history else []
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


# Singleton instance
_agent = None


def get_error_agent() -> ErrorFixingAgent:
    """Get or create the error-fixing agent instance."""
    global _agent
    if _agent is None:
        _agent = ErrorFixingAgent()
    return _agent


def auto_fix_decorator(func):
    """Decorator to automatically handle and fix errors in functions."""
    def wrapper(*args, **kwargs):
        agent = get_error_agent()
        
        for attempt in range(3):
            try:
                result = func(*args, **kwargs)
                agent.reset_fix_attempts()
                return result
            except Exception as e:
                error_context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "params": {"args": str(args)[:100], "kwargs": str(kwargs)[:100]},
                    "attempt": attempt + 1
                }
                
                analysis = agent.analyze_error(str(e), error_context)
                fix_result = agent.attempt_auto_fix(analysis, error_context)
                
                if not fix_result.get("success") or attempt == 2:
                    raise e
                
                # Apply fix and retry
                if fix_result.get("action") == "retry":
                    continue
                else:
                    # Can't auto-fix, re-raise
                    raise e
        
        return None
    
    return wrapper
