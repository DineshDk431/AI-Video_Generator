import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from . import HF_TOKEN, DEVICE, DTYPE

class PromptRefiner:
    """LLM-based prompt refinement for video generation."""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    
    def load_model(self, progress_callback=None):
        """Load the LLM for prompt refinement."""
        if self.model is None:
            if progress_callback:
                progress_callback("Loading prompt refinement model...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                token=HF_TOKEN,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                token=HF_TOKEN,
                torch_dtype=DTYPE,
                device_map="auto" if DEVICE == "cuda" else None,
                trust_remote_code=True
            )
            
            if DEVICE != "cuda":
                self.model = self.model.to(DEVICE)
            
            if progress_callback:
                progress_callback("Refinement model loaded!")
        
        return self.model, self.tokenizer
    
    def refine_prompt(
        self,
        original_prompt: str,
        user_feedback: str = None,
        style: str = "cinematic",
        progress_callback=None
    ) -> str:
        """
        Refine a video generation prompt based on user feedback.
        
        Args:
            original_prompt: The original user prompt
            user_feedback: Optional feedback for refinement (e.g., "make it more dramatic")
            style: Desired video style
            progress_callback: Optional progress callback
        
        Returns:
            Refined prompt string
        """
        model, tokenizer = self.load_model(progress_callback)
        system_prompt = """You are an expert at creating prompts for AI video generation (Sora, RunCam, CogVideo). 
Your task is to enhance prompts to create stunning, high-definition videos.
Output a single, highly detailed paragraph focusing on:
- Visual specs: 4k, photorealistic, cinematic lighting, sharp focus
- Camera movement: steady cam, slow pan, zoom, tracking shot
- Atmosphere: detailed background, specific mood, lighting effects
- Action: clear movement description
Keep it under 75 words. Return ONLY the refined prompt."""

        if user_feedback:
            user_message = f"""Original prompt: "{original_prompt}"
User feedback: "{user_feedback}"
Style: {style}

Refine this prompt incorporating the feedback. Return ONLY the refined prompt, nothing else."""
        else:
            user_message = f"""Original prompt: "{original_prompt}"
Style: {style}

Enhance this prompt with more visual details for AI video generation. Return ONLY the refined prompt, nothing else."""

        # Format for chat
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if progress_callback:
            progress_callback("Refining prompt...")
        
        # Generate
        input_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = tokenizer(input_text, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id
            )
        
        # Decode and extract refined prompt
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the generated part
        refined = full_response.split(user_message)[-1].strip()
        refined = refined.replace("assistant", "").strip()
        
        # Clean up any remaining artifacts
        if refined.startswith(":"):
            refined = refined[1:].strip()
        if refined.startswith('"') and refined.endswith('"'):
            refined = refined[1:-1]
        
        if progress_callback:
            progress_callback("Prompt refined!")
        
        return refined if refined else original_prompt
    
    def refine_to_json(
        self,
        prompt: str,
        progress_callback=None
    ) -> dict:
        """
        Refine prompt into a JSON structure with video generation parameters.
        
        Args:
            prompt: User input prompt
            progress_callback: Optional callback
        
        Returns:
            Dictionary with keys: prompt, negative_prompt, style, fps, num_inference_steps
        """
        model, tokenizer = self.load_model(progress_callback)
        import json
        
        system_prompt = """You are an AI video generation expert. 
Convert the user's request into a structured JSON for a video generation model.
Analyze the prompt to determine the best settings (style, fps, etc).
Return ONLY valid JSON."""

        user_message = f"""Input: "{prompt}"

Create a JSON object with these fields:
- prompt: A highly detailed, visual description for the video (2-3 sentences).
- negative_prompt: Things to avoid (e.g. "blurry, distorted").
- style: The visual style (e.g. "Cinematic", "Anime", "Realistic", "3D Render").
- fps: Best frame rate (e.g. 24 for cinematic, 60 for smooth).
- num_inference_steps: Quality steps (20-50).

Return ONLY the JSON object."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if progress_callback:
            progress_callback("Analyzing prompt for structure...")
        
        input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(input_text, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        response_text = full_response.split(user_message)[-1].strip()
        
        # Extract JSON
        try:
            # Find first { and last }
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                return data
        except Exception:
            pass
            
        # Fallback
        return {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, distorted",
            "style": "Cinematic",
            "fps": 24,
            "num_inference_steps": 30
        }
    
    def generate_variations(
        self,
        prompt: str,
        num_variations: int = 3,
        progress_callback=None
    ) -> list:
        """
        Generate multiple variations of a prompt.
        
        Args:
            prompt: The base prompt
            num_variations: Number of variations to generate
            progress_callback: Optional progress callback
        
        Returns:
            List of prompt variations
        """
        model, tokenizer = self.load_model(progress_callback)
        
        system_prompt = """You are an expert at creating prompts for AI video generation.
Generate creative variations of the given prompt, each with different visual interpretations."""

        user_message = f"""Base prompt: "{prompt}"

Generate {num_variations} different variations of this prompt for AI video generation.
Each variation should have a unique visual interpretation.
Return only the numbered list of prompts, one per line."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        if progress_callback:
            progress_callback("Generating variations...")
        
        input_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = tokenizer(input_text, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=0.7,
                do_sample=True,
                top_p=0.95,
                pad_token_id=tokenizer.eos_token_id
            )
        
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Parse variations from response
        variations = []
        lines = full_response.split("\n")
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                clean = line.lstrip("0123456789.-) ").strip()
                if clean:
                    variations.append(clean)
        
        return variations[:num_variations] if variations else [prompt]


# Singleton
_refiner = None

def get_prompt_refiner():
    """Get or create prompt refiner instance."""
    global _refiner
    if _refiner is None:
        _refiner = PromptRefiner()
    return _refiner
