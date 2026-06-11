"""
Review Quiz Agent — SM-2 Spaced Repetition + Quiz Generation
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from backend.agents.base import BaseAgent
from backend.services.qwen_client import qwen_client
from backend.database.connection import get_db_session
from backend.database.models import Word, Review, LearningRecord, DailyStats
from backend.config import settings


class ReviewQuizAgent(BaseAgent):
    """Agent for handling word reviews and quiz generation with SM-2 algorithm."""

    def __init__(self):
        super().__init__(name="ReviewQuizAgent")

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the review quiz agent with specified action."""
        action = kwargs.get("action")

        if action == "get_due_words":
            return self._get_due_words(
                user_id=kwargs.get("user_id"),
                limit=kwargs.get("limit", 20)
            )
        elif action == "submit_review":
            return self._submit_review(
                word_id=kwargs.get("word_id"),
                user_id=kwargs.get("user_id"),
                quality=kwargs.get("quality")
            )
        elif action == "generate_quiz":
            return self._generate_quiz(
                user_id=kwargs.get("user_id"),
                limit=kwargs.get("limit", 10)
            )
        elif action == "get_word_for_review":
            return self._get_word_for_review(
                word_id=kwargs.get("word_id"),
                user_id=kwargs.get("user_id")
            )
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }

    def _get_due_words(self, user_id: Optional[int] = None, limit: int = 20) -> Dict[str, Any]:
        """Get words that are due for review today."""
        db = get_db_session()
        try:
            now = datetime.now()

            query = db.query(Word, Review).outerjoin(Review, Word.id == Review.word_id)

            filters = [
                or_(
                    Review.id == None,
                    and_(
                        Review.is_due == True,
                        or_(
                            Review.next_review_date == None,
                            Review.next_review_date <= now
                        )
                    )
                )
            ]

            if user_id is not None:
                filters.append(Word.user_id == user_id)

            results = query.filter(and_(*filters)).limit(limit).all()

            due_words = []
            for word, review in results:
                due_words.append({
                    "word_id": word.id,
                    "word": word.word,
                    "phonetic": word.phonetic,
                    "chinese_meaning": word.chinese_meaning,
                    "example_sentence": word.example_sentence,
                    "chinese_translation": word.chinese_translation,
                    "repetitions": review.repetitions if review else 0,
                    "interval": review.interval if review else 1,
                    "ease_factor": review.ease_factor if review else 2.5
                })

            return {
                "success": True,
                "due_count": len(due_words),
                "due_words": due_words,
                "message": f"You have {len(due_words)} words to review today!"
            }

        finally:
            db.close()

    def _submit_review(self, word_id: int, user_id: Optional[int] = None, quality: int = 3) -> Dict[str, Any]:
        """Submit a review with SM-2 algorithm."""
        db = get_db_session()
        try:
            word = db.query(Word).filter(Word.id == word_id).first()
            if not word:
                return {"success": False, "error": "Word not found"}

            review = db.query(Review).filter(Review.word_id == word_id).first()

            if not review:
                review = Review(
                    word_id=word_id,
                    user_id=user_id,
                    interval=1,
                    ease_factor=2.5,
                    repetitions=0,
                    is_due=True
                )
                db.add(review)

            # SM-2 Algorithm
            if quality < 3:
                review.repetitions = 0
                review.interval = 1
            else:
                if review.repetitions == 0:
                    review.interval = 1
                elif review.repetitions == 1:
                    review.interval = 6
                else:
                    review.interval = int(review.interval * review.ease_factor)

                review.repetitions += 1

            review.ease_factor = max(1.3, review.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            review.is_due = False
            review.next_review_date = datetime.now() + timedelta(days=review.interval)
            review.last_review_date = datetime.now()

            # Update learning record
            learning_record = db.query(LearningRecord).filter(
                LearningRecord.word_id == word_id
            ).first()

            if not learning_record:
                learning_record = LearningRecord(
                    word_id=word_id,
                    user_id=user_id,
                    review_count=0,
                    correct_count=0
                )
                db.add(learning_record)

            learning_record.review_count += 1
            if quality >= 3:
                learning_record.correct_count += 1

            # Update daily stats
            today = datetime.now().date()
            daily_stats = db.query(DailyStats).filter(
                DailyStats.date == today
            ).first()

            if not daily_stats:
                daily_stats = DailyStats(
                    date=today,
                    reviews_count=0,
                    words_learned=0
                )
                db.add(daily_stats)

            daily_stats.reviews_count += 1

            # Mark word as learned if quality >= 3
            if quality >= 3 and not word.learned:
                word.learned = True
                daily_stats.words_learned += 1

            db.commit()

            return {
                "success": True,
                "message": f"Review submitted! Next review in {review.interval} days.",
                "interval": review.interval,
                "ease_factor": round(review.ease_factor, 2)
            }

        finally:
            db.close()

    def _generate_quiz(self, user_id: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
        """Generate a quiz from learned words."""
        db = get_db_session()
        try:
            query = db.query(Word).filter(Word.learned == True)

            if user_id is not None:
                query = query.filter(Word.user_id == user_id)

            learned_words = query.limit(limit * 3).all()

            if len(learned_words) < 4:
                return {
                    "success": False,
                    "message": "Not enough learned words for a quiz. Learn more words first!"
                }

            selected_words = random.sample(learned_words, min(limit, len(learned_words)))
            quiz = []

            for word in selected_words:
                distractors = random.sample(
                    [w for w in learned_words if w.id != word.id],
                    min(3, len(learned_words) - 1)
                )

                options = [word.chinese_meaning] + [d.chinese_meaning for d in distractors]
                random.shuffle(options)

                correct_index = options.index(word.chinese_meaning)

                quiz.append({
                    "word_id": word.id,
                    "word": word.word,
                    "question": f"What is the meaning of '{word.word}'?",
                    "options": options,
                    "correct_index": correct_index
                })

            return {
                "success": True,
                "quiz": quiz,
                "message": f"Generated {len(quiz)} quiz questions!"
            }

        finally:
            db.close()

    def _get_word_for_review(self, word_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get a specific word for review."""
        db = get_db_session()
        try:
            word = db.query(Word).filter(Word.id == word_id).first()

            if not word:
                return {"success": False, "message": "Word not found"}

            return {
                "success": True,
                "word_id": word.id,
                "word": word.word,
                "phonetic": word.phonetic,
                "part_of_speech": word.part_of_speech,
                "chinese_meaning": word.chinese_meaning,
                "example_sentence": word.example_sentence,
                "chinese_translation": word.chinese_translation
            }

        finally:
            db.close()


# Global instance
review_quiz_agent = ReviewQuizAgent()