"""
Example Search Agent - THE CORE AGENT of the project.

Workflow:
1. User inputs word
2. Search Tavily for real news articles containing the word
3. Extract sentences with the target word
4. Use Qwen LLM to select the best example
5. Generate Chinese translation
6. Get full word info (phonetic, POS, collocations, synonyms, antonyms)
7. Analyze sentence difficulty (1-5)
8. Save everything to database
9. Return formatted result to user

This agent interacts with:
- Tavily API (external search service)
- Qwen LLM (external AI service)
- SQLite Database (external storage)
"""

from typing import Dict, Any, Optional
from datetime import datetime
from backend.agents.base import BaseAgent
from backend.services.tavily_client import tavily_search_client
from backend.services.qwen_client import qwen_client
from backend.database.connection import get_db_session
from backend.database.models import Word, Review
from backend.config import settings

class ExampleSearchAgent(BaseAgent):
    """
    Core Agent: Searches real English sources for authentic example sentences.

    Input: word (str) - e.g., "sanction"
    Output: Complete vocabulary entry with real example from news
    """

    def __init__(self):
        super().__init__("ExampleSearchAgent")

    def execute(self, word: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Main execution flow for the Example Search Agent.

        Args:
            word: The English word to search for
            user_id: Optional user ID for multi-user support

        Returns:
            Dict with full word data or error info
        """
        word = word.strip().lower()

        print(f"[{self.name}] Step 1/7: Searching Tavily for articles containing '{word}'...")

        # Step 1: Search Tavily for real articles
        search_result = tavily_search_client.get_best_example(word)

        if not search_result.get("sentence"):
            return {
                "success": False,
                "error": f"No articles found containing '{word}' in trusted news sources.",
                "word": word
            }

        example_sentence = search_result["sentence"]
        source_name = search_result["source_name"]
        source_url = search_result["source_url"]

        print(f"[{self.name}] Step 2/7: Found example from {source_name}")
        print(f"[{self.name}] Sentence: {example_sentence[:100]}...")

        # Step 2: Use Qwen to get comprehensive word info
        print(f"[{self.name}] Step 3/7: Getting word info from Qwen...")
        word_info = qwen_client.get_word_info(word)

        # Step 3: Translate the example sentence
        print(f"[{self.name}] Step 4/7: Translating example to Chinese...")
        chinese_translation = qwen_client.translate_example(example_sentence, word)

        # Step 4: Analyze difficulty
        print(f"[{self.name}] Step 5/7: Analyzing sentence difficulty...")
        difficulty = qwen_client.analyze_sentence_difficulty(example_sentence)

        # Step 5: Build complete word data
        print(f"[{self.name}] Step 6/7: Building vocabulary entry...")
        word_data = {
            "word": word,
            "phonetic": word_info.get("phonetic", ""),
            "part_of_speech": word_info.get("part_of_speech", ""),
            "chinese_meaning": word_info.get("chinese_meaning", ""),
            "example_sentence": example_sentence,
            "chinese_translation": chinese_translation,
            "source_name": source_name,
            "source_url": source_url,
            "collocations": word_info.get("collocations", []),
            "synonyms": word_info.get("synonyms", []),
            "antonyms": word_info.get("antonyms", []),
            "difficulty": difficulty,
            "learned": False
        }

        # Step 6: Save to database
        print(f"[{self.name}] Step 7/7: Saving to database...")
        word_id = self._save_to_database(word_data, user_id)

        # Log activity
        self.log_activity(
            word_id=word_id,
            action="added_via_example_search",
            details={
                "source": source_name,
                "url": source_url,
                "agent": self.name
            }
        )

        # Return formatted result
        return {
            "success": True,
            "word": word_data,
            "database_id": word_id,
            "message": self._format_response(word_data)
        }

    def _save_to_database(self, word_data: Dict[str, Any], user_id: Optional[int] = None) -> int:
        """Save word data to database and create/update review record. Returns word ID."""
        db = get_db_session()

        try:
            # Check if word already exists
            existing = db.query(Word).filter(Word.word == word_data["word"]).first()
            if existing:
                # Update existing word
                existing.phonetic = word_data["phonetic"]
                existing.part_of_speech = word_data["part_of_speech"]
                existing.chinese_meaning = word_data["chinese_meaning"]
                existing.example_sentence = word_data["example_sentence"]
                existing.chinese_translation = word_data["chinese_translation"]
                existing.source_name = word_data["source_name"]
                existing.source_url = word_data["source_url"]
                existing.collocations = word_data["collocations"]
                existing.synonyms = word_data["synonyms"]
                existing.antonyms = word_data["antonyms"]
                existing.difficulty = word_data["difficulty"]
                db.commit()

                # FIX: Ensure review record exists for existing words too!
                self._ensure_review_record(db, existing.id, user_id)

                return existing.id
            else:
                # Create new word
                db_word = Word(
                    user_id=user_id,
                    word=word_data["word"],
                    phonetic=word_data["phonetic"],
                    part_of_speech=word_data["part_of_speech"],
                    chinese_meaning=word_data["chinese_meaning"],
                    example_sentence=word_data["example_sentence"],
                    chinese_translation=word_data["chinese_translation"],
                    source_name=word_data["source_name"],
                    source_url=word_data["source_url"],
                    collocations=word_data["collocations"],
                    synonyms=word_data["synonyms"],
                    antonyms=word_data["antonyms"],
                    difficulty=word_data["difficulty"]
                )
                db.add(db_word)
                db.commit()

                # Create initial review record for spaced repetition
                self._create_review_record(db, db_word.id, user_id)

                return db_word.id

        finally:
            db.close()

    def _ensure_review_record(self, db, word_id: int, user_id: Optional[int] = None):
        """FIX: Create review record if it doesn't exist (for existing words)."""
        review = db.query(Review).filter(Review.word_id == word_id).first()
        if not review:
            # No review record exists - create one and mark as due
            self._create_review_record(db, word_id, user_id)
            print(f"[{self.name}] Created missing review record for word_id={word_id}")
        else:
            # Review exists - make sure it's due for review
            review.is_due = True
            review.next_review_date = None  # Reset so it shows as due now
            db.commit()
            print(f"[{self.name}] Updated review record for word_id={word_id} to is_due=True")

    def _create_review_record(self, db, word_id: int, user_id: Optional[int] = None):
        """Create a fresh review record for a word."""
        review = Review(
            word_id=word_id,
            user_id=user_id,
            interval=settings.SM2_INITIAL_INTERVAL,
            ease_factor=settings.SM2_INITIAL_EASE,
            is_due=True,
            next_review_date=None,
            repetitions=0,
            quality=None
        )
        db.add(review)
        db.commit()
        print(f"[{self.name}] Created new review record for word_id={word_id}")

    def _format_response(self, word_data: Dict[str, Any]) -> str:
        """Format the result as a nice message for the user."""
        lines = [
            f"✅ Word added: {word_data['word']}",
            "",
            f"📌 Phonetic: {word_data['phonetic']}",
            f"📌 Part of Speech: {word_data['part_of_speech']}",
            f"📌 Meaning: {word_data['chinese_meaning']}",
            "",
            f"📝 Example:",
            f"  {word_data['example_sentence']}",
            f"  {word_data['chinese_translation']}",
            "",
            f"📰 Source: {word_data['source_name']}",
            f"🔗 URL: {word_data['source_url']}",
        ]

        if word_data.get("collocations"):
            lines.extend(["", f"🔗 Collocations: {', '.join(word_data['collocations'])}"])
        if word_data.get("synonyms"):
            lines.extend([f"🔄 Synonyms: {', '.join(word_data['synonyms'])}"])
        if word_data.get("antonyms"):
            lines.extend([f"🔀 Antonyms: {', '.join(word_data['antonyms'])}"])

        return "\n".join(lines)

# Global instance
example_search_agent = ExampleSearchAgent()