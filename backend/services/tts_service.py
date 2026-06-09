"""
Text-to-Speech (TTS) Audio Generation Service.

Features:
- Qwen TTS API integration (if available)
- Browser Web Speech API fallback
- Audio file caching
- Word + example sentence audio generation
- Playback speed control
"""

import os
import base64
import hashlib
from typing import Optional
from pathlib import Path
import requests
from backend.config import settings


class TTSService:
    """Text-to-Speech service for vocabulary audio generation."""

    def __init__(self):
        self.cache_dir = Path("./audio_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.api_key = settings.DASHSCOPE_API_KEY
        self.tts_enabled = settings.TTS_ENABLED
        self.voice = settings.TTS_VOICE

    def _get_cache_path(self, text: str) -> Path:
        """Generate cache file path for text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        return self.cache_dir / f"{text_hash}.mp3"

    def _is_cached(self, text: str) -> bool:
        """Check if audio is already cached."""
        return self._get_cache_path(text).exists()

    def generate_audio(self, text: str, word: str = "") -> Optional[str]:
        """
        Generate audio for text.

        Args:
            text: Text to convert to speech
            word: Optional word for context

        Returns:
            Path to audio file or None if failed
        """
        if not self.tts_enabled:
            return None

        cache_path = self._get_cache_path(text)

        # Return cached file if exists
        if cache_path.exists():
            return str(cache_path)

        # Try Qwen TTS API first
        audio_data = self._try_qwen_tts(text)

        if audio_data:
            # Save to cache
            with open(cache_path, "wb") as f:
                f.write(audio_data)
            return str(cache_path)

        # Fallback: try other TTS services
        audio_data = self._try_edge_tts(text)

        if audio_data:
            with open(cache_path, "wb") as f:
                f.write(audio_data)
            return str(cache_path)

        return None

    def _try_qwen_tts(self, text: str) -> Optional[bytes]:
        """Try Qwen/DashScope TTS API."""
        try:
            url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/speech"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "speech-tts",
                "input": {
                    "text": text
                },
                "parameters": {
                    "voice": self.voice,
                    "format": "mp3"
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if "output" in result and "audio" in result["output"]:
                    # Decode base64 audio
                    audio_base64 = result["output"]["audio"]
                    return base64.b64decode(audio_base64)

            return None

        except Exception as e:
            print(f"Qwen TTS failed: {e}")
            return None

    def _try_edge_tts(self, text: str) -> Optional[bytes]:
        """Try Microsoft Edge TTS as fallback."""
        try:
            # Edge TTS free API
            url = "https://speech.platform.bing.com/speech/recognition/interactive/cognitiveservices/v1"
            # This is a simplified placeholder - in production use edge-tts Python library
            return None

        except Exception as e:
            print(f"Edge TTS failed: {e}")
            return None

    def generate_word_audio(self, word: str, example: str = "") -> Optional[str]:
        """
        Generate audio for a word and its example sentence.

        Format: "word. example sentence."

        Args:
            word: The vocabulary word
            example: Example sentence (optional)

        Returns:
            Path to audio file
        """
        text = word
        if example:
            text = f"{word}. {example}"

        return self.generate_audio(text, word)

    def get_audio_url(self, word_id: int) -> Optional[str]:
        """
        Get or generate audio URL for a word.

        Args:
            word_id: Database word ID

        Returns:
            URL to audio file or None
        """
        from backend.database.connection import get_db_session
        from backend.database.models import Word

        db = get_db_session()
        try:
            word_record = db.query(Word).filter(Word.id == word_id).first()
            if not word_record:
                return None

            text = word_record.word
            if word_record.example_sentence:
                text = f"{word_record.word}. {word_record.example_sentence}"

            audio_path = self.generate_audio(text, word_record.word)

            if audio_path:
                # Update database with audio URL
                word_record.audio_url = audio_path
                db.commit()

            return audio_path

        finally:
            db.close()

    def delete_cached_audio(self, text: str):
        """Delete cached audio file."""
        cache_path = self._get_cache_path(text)
        if cache_path.exists():
            cache_path.unlink()

    def clear_cache(self):
        """Clear all cached audio files."""
        for file in self.cache_dir.glob("*.mp3"):
            file.unlink()
        print("Audio cache cleared")


# Global instance
tts_service = TTSService()
