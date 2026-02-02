import os
import json
from typing import Dict, List, Optional
from huggingface_hub import InferenceClient
from . import HF_TOKEN


class LlamaPromptGenerator:
    """Generate structured video prompts using LLAMA 4 Scout via HuggingFace Inference API."""
    
    def __init__(self):
        self.client = None
        # Use LLAMA 4 Scout via Inference API
        self.model_id = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
        # Fallback model if Scout not available
        self.fallback_model = "meta-llama/Llama-3.3-70B-Instruct"
        
    def _get_client(self):
        """Get or create the inference client."""
        if self.client is None:
            token = HF_TOKEN or os.getenv("HF_TOKEN")
            if not token:
                raise ValueError("HuggingFace token not set. Set HF_TOKEN environment variable.")
            self.client = InferenceClient(token=token)
        return self.client
    
    def analyze_prompt(
        self, 
        text: str,
        progress_callback=None
    ) -> Dict:
        """
        Analyze user prompt to extract intent, topic, and emotions.
        
        Args:
            text: User input prompt
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with intent, topic, emotions, style, and elements
        """
        try:
            if progress_callback:
                progress_callback("Analyzing prompt with LLAMA 4 Scout...")
            
            client = self._get_client()
            
            system_prompt = """You are an expert at analyzing video generation prompts. 
Analyze the user's request and extract structured information.
Always respond with valid JSON only."""
            
            user_message = f"""Analyze this video generation prompt and extract:
- intent: What the user wants (e.g., "create_video", "generate_scene", "animate")
- topic: Main subject/theme (e.g., "nature", "technology", "emotions")
- emotions: List of emotions conveyed (e.g., ["peaceful", "exciting", "mysterious"])
- style: Visual style recommendation (e.g., "Cinematic", "Anime", "Documentary", "Abstract")
- elements: Key visual elements to include (e.g., ["mountains", "sunset", "birds"])
- motion: Suggested camera/motion type (e.g., "slow_pan", "zoom_in", "tracking", "static")

User prompt: "{text}"

Respond with ONLY valid JSON:"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Try primary model first
            try:
                response = client.chat_completion(
                    model=self.model_id,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.3
                )
            except Exception:
                # Fallback to alternative model
                response = client.chat_completion(
                    model=self.fallback_model,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.3
                )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON from response
            try:
                # Find JSON in response
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                    analysis = json.loads(json_str)
                else:
                    raise ValueError("No JSON found")
            except json.JSONDecodeError:
                analysis = self._default_analysis(text)
            
            if progress_callback:
                progress_callback("Analysis complete!")
            
            return analysis
            
        except Exception as e:
            print(f"Analysis error: {e}")
            return self._default_analysis(text)
    
    def _default_analysis(self, text: str) -> Dict:
        """Return default analysis when API fails."""
        return {
            "intent": "generate_video",
            "topic": "general",
            "emotions": ["neutral"],
            "style": "Cinematic",
            "elements": [],
            "motion": "smooth",
            "error": "Using default analysis"
        }
    
    def generate_video_prompt(
        self, 
        analysis: Dict,
        original_prompt: str,
        progress_callback=None
    ) -> Dict:
        """
        Generate a structured JSON prompt for video generation based on analysis.
        
        Args:
            analysis: Analysis results from analyze_prompt()
            original_prompt: The original user prompt
            progress_callback: Optional callback for progress updates
            
        Returns:
            Complete video generation configuration
        """
        try:
            if progress_callback:
                progress_callback("Generating enhanced video prompt...")
            
            client = self._get_client()
            
            system_prompt = """You are an expert at creating detailed prompts for AI video generation.
Create rich, visual descriptions that will produce high-quality videos.
Always respond with valid JSON only."""

            user_message = f"""Based on this analysis and original prompt, create an enhanced video generation configuration:

Original prompt: "{original_prompt}"
Analysis: {json.dumps(analysis)}

Create a JSON with:
- prompt: A detailed, visual description for the video (2-3 sentences, rich in visual detail)
- negative_prompt: Things to avoid (e.g., "blurry, distorted, low quality, text, watermark")
- style: Visual style from the analysis
- fps: Recommended frame rate (8-24 based on content type)
- duration_seconds: Suggested duration (2-8 seconds)
- camera_motion: Suggested camera movement
- lighting: Lighting recommendation
- color_palette: Color scheme suggestion

Respond with ONLY valid JSON:"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            try:
                response = client.chat_completion(
                    model=self.model_id,
                    messages=messages,
                    max_tokens=600,
                    temperature=0.5
                )
            except Exception:
                response = client.chat_completion(
                    model=self.fallback_model,
                    messages=messages,
                    max_tokens=600,
                    temperature=0.5
                )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            try:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                    config = json.loads(json_str)
                else:
                    raise ValueError("No JSON found")
            except json.JSONDecodeError:
                config = self._default_config(original_prompt, analysis)
            
            if progress_callback:
                progress_callback("Enhanced prompt ready!")
            
            return config
            
        except Exception as e:
            print(f"Generation error: {e}")
            return self._default_config(original_prompt, analysis)
    
    def _default_config(self, prompt: str, analysis: Dict) -> Dict:
        """Return default config when API fails."""
        return {
            "prompt": prompt,
            "negative_prompt": "blurry, distorted, low quality, text, watermark",
            "style": analysis.get("style", "Cinematic"),
            "fps": 24,
            "duration_seconds": 4,
            "camera_motion": analysis.get("motion", "smooth"),
            "lighting": "natural",
            "color_palette": "balanced"
        }


# Singleton instance
_generator = None


def get_llama_generator() -> LlamaPromptGenerator:
    """Get or create the LLAMA prompt generator instance."""
    global _generator
    if _generator is None:
        _generator = LlamaPromptGenerator()
    return _generator
