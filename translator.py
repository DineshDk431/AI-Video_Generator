"""
TranslateGemma Multi-language Translation Module.
Handles translation of non-English prompts to English for video generation.
Uses HuggingFace Inference API for lightweight deployment.
"""
import os
from typing import Dict, Optional
from huggingface_hub import InferenceClient
from . import HF_TOKEN


class PromptTranslator:
    """Translate prompts to English using HuggingFace Inference API."""
    
    def __init__(self):
        self.client = None
        # Use a supported model on HuggingFace Inference API
        self.model_id = "Qwen/Qwen2.5-72B-Instruct"  # Widely available on HF
        self.fallback_model = "mistralai/Mistral-7B-Instruct-v0.3"
        
    def _get_client(self):
        """Get or create the inference client."""
        if self.client is None:
            token = HF_TOKEN or os.getenv("HF_TOKEN")
            if not token:
                raise ValueError("HuggingFace token not set. Set HF_TOKEN environment variable.")
            self.client = InferenceClient(token=token)
        return self.client
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text.
        
        Args:
            text: Input text to detect language for
            
        Returns:
            Language code (e.g., 'en', 'es', 'zh', 'hi')
        """
        try:
            client = self._get_client()
            
            messages = [
                {
                    "role": "user",
                    "content": f"""Detect the language of this text and respond with ONLY the 2-letter language code (e.g., en, es, fr, zh, hi, ta, ar).

Text: "{text}"

Language code:"""
                }
            ]
            
            response = client.chat_completion(
                model=self.model_id,
                messages=messages,
                max_tokens=10,
                temperature=0.1
            )
            
            lang_code = response.choices[0].message.content.strip().lower()[:2]
            return lang_code if len(lang_code) == 2 else "en"
            
        except Exception as e:
            print(f"Language detection error: {e}")
            return "en"  # Default to English
    
    def translate_to_english(
        self, 
        text: str, 
        source_lang: str = "auto",
        progress_callback=None
    ) -> Dict:
        """
        Translate input text to English.
        
        Args:
            text: Input text in any language
            source_lang: Source language code ('auto' for detection)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with original text, detected language, and translation
        """
        try:
            if progress_callback:
                progress_callback("Detecting language...")
            
            # Detect language if auto
            if source_lang == "auto":
                detected_lang = self.detect_language(text)
            else:
                detected_lang = source_lang
            
            # If already English, return as-is
            if detected_lang == "en":
                return {
                    "original": text,
                    "detected_language": "en",
                    "translated": text,
                    "was_translated": False
                }
            
            if progress_callback:
                progress_callback(f"Translating from {detected_lang} to English...")
            
            client = self._get_client()
            
            messages = [
                {
                    "role": "user",
                    "content": f"""Translate the following text to English. Output ONLY the English translation, nothing else.

Original text ({detected_lang}): "{text}"

English translation:"""
                }
            ]
            
            response = client.chat_completion(
                model=self.model_id,
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )
            
            translation = response.choices[0].message.content.strip()
            
            # Clean up any quotes
            if translation.startswith('"') and translation.endswith('"'):
                translation = translation[1:-1]
            
            if progress_callback:
                progress_callback("Translation complete!")
            
            return {
                "original": text,
                "detected_language": detected_lang,
                "translated": translation,
                "was_translated": True
            }
            
        except Exception as e:
            print(f"Translation error: {e}")
            return {
                "original": text,
                "detected_language": "unknown",
                "translated": text,
                "was_translated": False,
                "error": str(e)
            }


# Singleton instance
_translator = None


def get_translator() -> PromptTranslator:
    """Get or create the translator instance."""
    global _translator
    if _translator is None:
        _translator = PromptTranslator()
    return _translator
