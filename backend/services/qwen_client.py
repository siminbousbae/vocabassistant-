"""
Qwen (DashScope) API client for the Vocabulary Assistant.
Handles: translation, phonetics, collocations, synonyms, antonyms, 
example filtering, and audio generation.
"""

import json
import re
from typing import Optional, List, Dict, Any
import dashscope
from dashscope import Generation
from backend.config import settings


class QwenClient:
    """Client for Qwen LLM via DashScope API."""

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.QWEN_MODEL
        dashscope.api_key = self.api_key

    def _call(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Call Qwen API with retry logic."""
        try:
            response = Generation.call(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                result_format="message"
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"Qwen API error: {response.status_code} - {response.message}")
        except Exception as e:
            print(f"Qwen API call failed: {e}")
            raise

    def get_word_info(self, word: str) -> Dict[str, Any]:
        """
        Get comprehensive word information from Qwen.
        Returns: phonetic, POS, chinese_meaning, collocations, synonyms, antonyms
        """
        system_prompt = """You are an expert English vocabulary tutor. 
Return ONLY valid JSON. Do not include markdown formatting or explanations.
The JSON must have these exact keys: phonetic, part_of_speech, chinese_meaning, 
collocations, synonyms, antonyms.
collocations, synonyms, antonyms should be arrays of strings."""

        user_prompt = (
            'Analyze the English word "' + word + '" and provide:\n'
            '1. IPA phonetic symbol\n'
            '2. Part of speech (noun/verb/adjective/adverb/etc.)\n'
            '3. Chinese meaning (most common 1-2 meanings)\n'
            '4. Common collocations (3-5 phrases)\n'
            '5. Synonyms (3-5 words)\n'
            '6. Antonyms (3-5 words)\n\n'
            'Return as JSON:\n'
            '{\n'
            '    "phonetic": "...",\n'
            '    "part_of_speech": "...",\n'
            '    "chinese_meaning": "...",\n'
            '    "collocations": ["...", "..."],\n'
            '    "synonyms": ["...", "..."],\n'
            '    "antonyms": ["...", "..."]\n'
            '}'
        )

        response = self._call(system_prompt, user_prompt)

        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise

    def translate_example(self, sentence: str, word: str) -> str:
        """Translate an English example sentence to Chinese."""
        system_prompt = "You are a professional translator. Translate English to natural, accurate Chinese."
        user_prompt = (
            'Translate this English sentence to Chinese. '
            'The sentence contains the word "' + word + '".'
            '\n\nEnglish: ' + sentence + '\n\n'
            'Return ONLY the Chinese translation, no explanation.'
        )

        return self._call(system_prompt, user_prompt, temperature=0.1).strip()

    def filter_best_example(self, word: str, sentences: List[str]) -> str:
        """
        Select the best example sentence from a list.
        Criteria: natural usage, clear context, appropriate difficulty.
        """
        if not sentences:
            return ""

        system_prompt = """You are an English teacher selecting the best example sentence.
Return ONLY the index number (0-based) of the best sentence. No explanation."""

        sentences_text = "\n".join([f"{i}. {s}" for i, s in enumerate(sentences)])
        user_prompt = (
            'Word: "' + word + '"\n\n'
            'Candidate sentences:\n' + sentences_text + '\n\n'
            'Select the BEST sentence that:\n'
            '- Shows natural, authentic usage of "' + word + '"\n'
            '- Has clear context\n'
            '- Is not too simple nor too complex\n'
            '- Is from a reputable news source\n\n'
            'Return ONLY the number (0-' + str(len(sentences)-1) + ').'
        )

        response = self._call(system_prompt, user_prompt, temperature=0.1).strip()

        # Extract number
        numbers = re.findall(r'\d+', response)
        if numbers:
            idx = int(numbers[0])
            if 0 <= idx < len(sentences):
                return sentences[idx]

        # Fallback: return first sentence
        return sentences[0] if sentences else ""

    def generate_phonetic(self, word: str) -> str:
        """Generate IPA phonetic symbol for a word."""
        system_prompt = "You are a phonetics expert. Return ONLY the IPA phonetic symbol."
        user_prompt = 'What is the IPA phonetic symbol for "' + word + '"? Return ONLY the symbol, no explanation.'
        return self._call(system_prompt, user_prompt, temperature=0.1).strip()

    def generate_audio_text(self, word: str, example: str) -> str:
        """Generate SSML or text for TTS audio."""
        return f"{word}. {example}"

    def analyze_sentence_difficulty(self, sentence: str) -> int:
        """Rate sentence difficulty 1-5."""
        system_prompt = "Rate sentence difficulty 1-5. Return ONLY the number."
        user_prompt = 'Rate difficulty (1-5): "' + sentence + '"'
        response = self._call(system_prompt, user_prompt, temperature=0.1).strip()
        numbers = re.findall(r'\d+', response)
        if numbers:
            return min(5, max(1, int(numbers[0])))
        return 3

    def generate_quiz_question(self, word: str, chinese_meaning: str) -> Dict[str, Any]:
        """Generate a multiple choice quiz question."""
        system_prompt = (
            "You are a quiz generator. Return ONLY valid JSON.\n"
            'Format: {"question": "...", "options": ["A", "B", "C", "D"], '
            '"correct_index": 0, "explanation": "..."}'
        )

        user_prompt = (
            'Create a multiple choice question for the word "' + word + '" '
            '(meaning: ' + chinese_meaning + ').\n\n'
            'The question should test understanding of the word in context.\n'
            'Provide 4 options where only 1 is correct.\n\n'
            'Return JSON:\n'
            '{\n'
            '    "question": "Fill in the blank or choose correct usage...",\n'
            '    "options": ["option A", "option B", "option C", "option D"],\n'
            '    "correct_index": 0,\n'
            '    "explanation": "Why this is correct"\n'
            '}'
        )

        response = self._call(system_prompt, user_prompt, temperature=0.5)
        response = response.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(response)


# Global instance
qwen_client = QwenClient()
