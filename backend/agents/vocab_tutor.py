"""
Vocabulary Tutor Agent.

Automatically generates comprehensive word information:
- Phonetic symbols
- Definitions
- Common collocations
- Synonyms
- Antonyms
- Example translations

Input: word (str)
Output: Complete vocabulary card data
"""

from typing import Dict, Any, Optional
from backend.agents.base import BaseAgent
from backend.services.qwen_client import qwen_client
from backend.database.connection import get_db_session
from backend.database.models import Word


class VocabTutorAgent(BaseAgent):
    """
    Tutor Agent: Generates comprehensive word information using Qwen LLM.
    Can be used standalone or as part of the add word flow.
    """

    def __init__(self):
        super().__init__("VocabTutorAgent")

    def execute(
        self,
        word: str,
        user_id: Optional[int] = None,
        update_existing: bool = False,
        word_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate or enrich word information.

        Args:
            word: English word to analyze
            user_id: Optional user ID
            update_existing: If True, updates existing DB record
            word_id: Optional existing word ID to enrich

        Returns:
            Dict with full word data
        """
        word = word.strip().lower()

        print(f"[{self.name}] Generating vocabulary info for '{word}'...")

        # Get comprehensive info from Qwen
        word_info = qwen_client.get_word_info(word)

        # Build result
        result = {
            "word": word,
            "phonetic": word_info.get("phonetic", ""),
            "part_of_speech": word_info.get("part_of_speech", ""),
            "chinese_meaning": word_info.get("chinese_meaning", ""),
            "collocations": word_info.get("collocations", []),
            "synonyms": word_info.get("synonyms", []),
            "antonyms": word_info.get("antonyms", []),
        }

        # Update database if requested
        if word_id is not None:
            updated = self._update_database_by_id(word_id, result, user_id)
            if not updated:
                return {"success": False, "error": "Word not found"}
        elif update_existing:
            self._update_database(word, result, user_id)

        # Log activity
        # Note: word_id might not exist yet if just generating info

        return {
            "success": True,
            "word": result,
            "message": self._format_tutor_card(result)
        }

    def enrich_existing_word(self, word_id: int) -> Dict[str, Any]:
        """
        Enrich an existing word in database with full tutor info.
        Useful for words added without full info.
        """
        db = get_db_session()
        try:
            word_record = db.query(Word).filter(Word.id == word_id).first()
            if not word_record:
                return {"success": False, "error": "Word not found"}

            # Get full info
            result = self.execute(word_record.word, update_existing=False)

            # Update record
            word_record.phonetic = result["word"]["phonetic"]
            word_record.part_of_speech = result["word"]["part_of_speech"]
            word_record.chinese_meaning = result["word"]["chinese_meaning"]
            word_record.collocations = result["word"]["collocations"]
            word_record.synonyms = result["word"]["synonyms"]
            word_record.antonyms = result["word"]["antonyms"]

            db.commit()

            self.log_activity(
                word_id=word_id,
                action="enriched_by_tutor",
                details={"agent": self.name}
            )

            return {
                "success": True,
                "word_id": word_id,
                "message": "Word enriched successfully"
            }

        finally:
            db.close()

    def _update_database(self, word: str, data: Dict, user_id: Optional[int] = None):
        """Update or create word in database."""
        db = get_db_session()
        try:
            existing = db.query(Word).filter(Word.word == word).first()
            if existing:
                existing.phonetic = data["phonetic"]
                existing.part_of_speech = data["part_of_speech"]
                existing.chinese_meaning = data["chinese_meaning"]
                existing.collocations = data["collocations"]
                existing.synonyms = data["synonyms"]
                existing.antonyms = data["antonyms"]
                db.commit()
            else:
                db_word = Word(
                    user_id=user_id,
                    word=word,
                    phonetic=data["phonetic"],
                    part_of_speech=data["part_of_speech"],
                    chinese_meaning=data["chinese_meaning"],
                    collocations=data["collocations"],
                    synonyms=data["synonyms"],
                    antonyms=data["antonyms"],
                )
                db.add(db_word)
                db.commit()
        finally:
            db.close()

    def _update_database_by_id(self, word_id: int, data: Dict, user_id: Optional[int] = None) -> bool:
        """Update an existing word by ID."""
        db = get_db_session()
        try:
            query = db.query(Word).filter(Word.id == word_id)
            if user_id is not None:
                query = query.filter(Word.user_id == user_id)

            existing = query.first()
            if not existing:
                return False

            existing.phonetic = data["phonetic"]
            existing.part_of_speech = data["part_of_speech"]
            existing.chinese_meaning = data["chinese_meaning"]
            existing.collocations = data["collocations"]
            existing.synonyms = data["synonyms"]
            existing.antonyms = data["antonyms"]
            db.commit()
            return True
        finally:
            db.close()

    def _format_tutor_card(self, data: Dict[str, Any]) -> str:
        """Format as a vocabulary study card."""
        lines = [
            f"📚 {data['word'].upper()}",
            f"   [{data['phonetic']}]  {data['part_of_speech']}",
            f"   {data['chinese_meaning']}",
            "",
        ]

        if data.get("collocations"):
            lines.append("🔗 Common Collocations:")
            for col in data["collocations"]:
                lines.append(f"   • {col}")
            lines.append("")

        if data.get("synonyms"):
            lines.append(f"🔄 Synonyms: {', '.join(data['synonyms'])}")

        if data.get("antonyms"):
            lines.append(f"🔀 Antonyms: {', '.join(data['antonyms'])}")

        return "\n".join(lines)


# Global instance
vocab_tutor_agent = VocabTutorAgent()
