"""
Subtitle generator using Google TranslateGemma model.
Automatically generates contextual subtitles for video content.
"""
import os
from typing import List, Optional
import torch


class TranslateGemmaSubtitleGenerator:
    """Generate subtitles using Google TranslateGemma model from HuggingFace."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_id = "google/translategemma-4b"  # 4B variant for efficiency
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.loaded = False
    
    def load_model(self, progress_callback=None):
        """Load the TranslateGemma model."""
        if self.loaded:
            return
        
        if progress_callback:
            progress_callback("Loading TranslateGemma subtitle model...")
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                token=os.getenv("HF_TOKEN", ""),
                trust_remote_code=True
            )
            
            # Load model with appropriate settings
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                token=os.getenv("HF_TOKEN", ""),
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            self.loaded = True
            
            if progress_callback:
                progress_callback("TranslateGemma loaded successfully!")
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Using fallback subtitle mode: {str(e)[:50]}")
            # Fallback mode - use simple text processing
            self.model = None
            self.loaded = False
    
    def generate_subtitles(
        self,
        prompt: str,
        duration_seconds: float = 4.0,
        language: str = "en",
        progress_callback=None
    ) -> List[dict]:
        """
        Generate contextual subtitles for a video based on the prompt.
        
        Args:
            prompt: The video description/prompt
            duration_seconds: Total video duration
            language: Target language code
            progress_callback: Optional progress callback
        
        Returns:
            List of subtitle segments with timing
        """
        if progress_callback:
            progress_callback("Generating subtitles...")
        
        # Try to load model if not loaded
        if not self.loaded:
            self.load_model(progress_callback)
        
        if self.model and self.tokenizer:
            return self._generate_with_model(prompt, duration_seconds, language, progress_callback)
        else:
            return self._generate_fallback(prompt, duration_seconds, progress_callback)
            

    
    def _generate_with_model(
        self,
        prompt: str,
        duration_seconds: float,
        language: str,
        progress_callback=None
    ) -> List[dict]:
        """Generate subtitles using TranslateGemma model."""
        from utils import clean_memory
        clean_memory()
        
        # Reload if needed (in case it was offloaded)
        if not self.model: 
             self.load_model(progress_callback)
        
        if progress_callback:
            progress_callback("Creating contextual subtitles with AI...")
        
        # Create prompt for subtitle generation
        system_prompt = f"""You are a subtitle generator. Given a video description, create short, 
descriptive subtitle segments that would appear in the video. Each segment should be 1-2 seconds.
Make the subtitles descriptive and immersive, describing what the viewer would see.

Video description: {prompt}
Duration: {duration_seconds} seconds
Language: {language}

Generate {max(2, int(duration_seconds / 2))} subtitle segments. Format each as:
[TIME] Text

Example:
[0-2s] The scene opens with a vast ocean
[2-4s] Waves gently crash on the shore
"""
        
        try:
            inputs = self.tokenizer(system_prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=200,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Parse the response into subtitle segments
            return self._parse_subtitle_response(response, duration_seconds)
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"Fallback mode: {str(e)[:30]}")
            return self._generate_fallback(prompt, duration_seconds, progress_callback)
    
    def _generate_fallback(
        self,
        prompt: str,
        duration_seconds: float,
        progress_callback=None
    ) -> List[dict]:
        """Fallback subtitle generation without model."""
        
        if progress_callback:
            progress_callback("Creating subtitles...")
        
        # Split prompt into meaningful segments
        words = prompt.split()
        num_segments = max(2, int(duration_seconds / 2))
        segment_duration = duration_seconds / num_segments
        
        subtitles = []
        words_per_segment = max(1, len(words) // num_segments)
        
        for i in range(num_segments):
            start_idx = i * words_per_segment
            end_idx = start_idx + words_per_segment if i < num_segments - 1 else len(words)
            
            segment_words = words[start_idx:end_idx]
            if not segment_words:
                continue
            
            text = " ".join(segment_words)
            # Capitalize first letter and add context
            text = text.capitalize()
            if not text.endswith(('.', '!', '?')):
                text += "..."
            
            subtitles.append({
                "start": round(i * segment_duration, 2),
                "end": round((i + 1) * segment_duration, 2),
                "text": text
            })
        
        return subtitles
    
    def _parse_subtitle_response(
        self,
        response: str,
        duration_seconds: float
    ) -> List[dict]:
        """Parse model response into subtitle segments."""
        import re
        
        subtitles = []
        lines = response.split('\n')
        
        # Parse lines like "[0-2s] Text" or "[0:00-0:02] Text"
        pattern = r'\[(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)s?\]\s*(.+)'
        
        for line in lines:
            match = re.search(pattern, line)
            if match:
                start = float(match.group(1))
                end = float(match.group(2))
                text = match.group(3).strip()
                
                if text and end <= duration_seconds + 1:
                    subtitles.append({
                        "start": start,
                        "end": min(end, duration_seconds),
                        "text": text
                    })
        
        # If parsing failed, use fallback
        if not subtitles:
            return self._generate_fallback(response.split("description:")[-1], duration_seconds, None)
        
        return subtitles


# Singleton instance
_generator = None

def get_subtitle_generator() -> TranslateGemmaSubtitleGenerator:
    """Get singleton subtitle generator."""
    global _generator
    if _generator is None:
        _generator = TranslateGemmaSubtitleGenerator()
    return _generator


def generate_video_subtitles(
    prompt: str,
    duration_seconds: float = 4.0,
    language: str = "en",
    progress_callback=None
) -> List[dict]:
    """
    Convenience function to generate subtitles for a video.
    
    Returns list of subtitle segments like:
    [{"start": 0.0, "end": 2.0, "text": "A beautiful sunset..."}, ...]
    """
    generator = get_subtitle_generator()
    return generator.generate_subtitles(prompt, duration_seconds, language, progress_callback)
