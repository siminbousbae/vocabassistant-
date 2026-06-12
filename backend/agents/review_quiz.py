"""
Review Quiz Agent — SM-2 Spaced Repetition + Quiz Generation
"""

import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func
from backend.agents.base import BaseAgent
from backend.services.qwen_client import qwen_client
from backend.services.spaced_repetition import SM2Algorithm, SM2Card
from backend.database.connection import get_db_session
from backend.database.models import Word, Review, LearningRecord, DailyStats
from backend.config import settings


class ReviewQuizAgent(BaseAgent):
    """Agent for handling word reviews and quiz generation with SM-2 algorithm."""

    def __init__(self):
        super().__init__(name="ReviewQuizAgent")
        self.sm2 = SM2Algorithm()

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the review quiz agent with specified action."""
        action = kwargs.get("action")
        action_aliases = {
            "get_due": "get_due_words",
            "review": "submit_review",
            "quiz": "generate_quiz",
            "stats": "get_stats",
            "word": "get_word_for_review",
        }
        action = action_aliases.get(action, action)

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
        elif action == "get_stats":
            return self._get_stats(user_id=kwargs.get("user_id"))
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
                    Review.next_review_date == None,
                    Review.next_review_date <= now
                )
            ]

            if user_id is not None:
                filters.append(Word.user_id == user_id)

            results = query.filter(and_(*filters)).limit(limit).all()

            due_words = []
            for word, review in results:
                if review and not review.is_due:
                    review.is_due = True
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

            db.commit()

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
        if word_id is None:
            return {"success": False, "error": "word_id is required"}
        if quality is None or not (0 <= quality <= 5):
            return {"success": False, "error": "Quality must be between 0 and 5"}

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
                    is_due=True,
                    next_review_date=None
                )
                db.add(review)

            sm2_result = self.sm2.review(
                SM2Card(
                    word_id=word_id,
                    interval=review.interval or 1,
                    ease_factor=review.ease_factor or 2.5,
                    repetitions=review.repetitions or 0,
                    quality=review.quality,
                    last_review=review.review_date,
                    next_review=review.next_review_date,
                ),
                quality
            )

            review.interval = sm2_result.interval
            review.ease_factor = sm2_result.ease_factor
            review.repetitions = sm2_result.repetitions
            review.quality = quality
            review.is_due = False
            review.next_review_date = sm2_result.next_review_date
            review.review_date = datetime.now()

            learning_record = LearningRecord(
                word_id=word_id,
                user_id=user_id,
                action="reviewed",
                score=quality,
                details={
                    "interval": sm2_result.interval,
                    "ease_factor": round(sm2_result.ease_factor, 2),
                    "repetitions": sm2_result.repetitions,
                    "next_review_date": sm2_result.next_review_date.isoformat(),
                }
            )
            db.add(learning_record)

            # Update daily stats
            today = datetime.now().strftime("%Y-%m-%d")
            daily_stats = db.query(DailyStats).filter(
                DailyStats.date == today,
                DailyStats.user_id == user_id
            ).first()

            if not daily_stats:
                daily_stats = DailyStats(
                    user_id=user_id,
                    date=today,
                    words_reviewed=0,
                    words_learned=0
                )
                db.add(daily_stats)

            daily_stats.words_reviewed += 1

            if sm2_result.is_learned and not word.learned:
                word.learned = True
                daily_stats.words_learned += 1
            elif quality < 3:
                word.learned = False

            db.commit()

            return {
                "success": True,
                "message": f"Review submitted! Next review in {sm2_result.interval} days.",
                "interval": sm2_result.interval,
                "ease_factor": round(sm2_result.ease_factor, 2),
                "repetitions": sm2_result.repetitions,
                "learned": sm2_result.is_learned,
                "next_review_date": sm2_result.next_review_date.isoformat()
            }

        finally:
            db.close()

    def _generate_quiz(self, user_id: Optional[int] = None, limit: int = 10) -> Dict[str, Any]:
        """Generate a quiz from learned words."""
        db = get_db_session()
        try:
            query = db.query(Word).filter(Word.chinese_meaning != None)

            if user_id is not None:
                query = query.filter(Word.user_id == user_id)

            learned_words = query.limit(max(limit * 3, 4)).all()

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
        if word_id is None:
            return {"success": False, "message": "word_id is required"}

        db = get_db_session()
        try:
            query = db.query(Word).filter(Word.id == word_id)
            if user_id is not None:
                query = query.filter(Word.user_id == user_id)
            word = query.first()

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

    def _get_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Return overview stats used by the web UI and Telegram bot."""
        db = get_db_session()
        try:
            word_query = db.query(Word)
            review_query = db.query(Review)
            record_query = db.query(LearningRecord)
            stats_query = db.query(DailyStats)

            if user_id is not None:
                word_query = word_query.filter(Word.user_id == user_id)
                review_query = review_query.filter(Review.user_id == user_id)
                record_query = record_query.filter(LearningRecord.user_id == user_id)
                stats_query = stats_query.filter(DailyStats.user_id == user_id)

            total_words = word_query.count()
            learned_words = word_query.filter(Word.learned == True).count()

            now = datetime.now()
            due_reviews = review_query.filter(
                or_(Review.next_review_date == None, Review.next_review_date <= now)
            ).count()

            review_records = record_query.filter(LearningRecord.action == "reviewed")
            total_reviews = review_records.count()
            avg_quality = review_records.with_entities(func.avg(LearningRecord.score)).scalar() or 0

            daily_rows = stats_query.order_by(DailyStats.date.desc()).limit(30).all()
            active_days = {row.date for row in daily_rows if row.words_reviewed or row.words_added or row.words_learned}
            streak = 0
            cursor = now.date()
            while cursor.strftime("%Y-%m-%d") in active_days:
                streak += 1
                cursor -= timedelta(days=1)

            mastery_level = "Novice"
            if learned_words >= 100:
                mastery_level = "Advanced"
            elif learned_words >= 30:
                mastery_level = "Intermediate"
            elif learned_words >= 10:
                mastery_level = "Beginner"

            return {
                "success": True,
                "stats": {
                    "total_words": total_words,
                    "learned_words": learned_words,
                    "due_words": due_reviews,
                    "total_reviews": total_reviews,
                    "average_quality": round(float(avg_quality), 2),
                    "current_streak": streak,
                    "mastery_level": mastery_level,
                }
            }

        finally:
            db.close()


# Global instance
review_quiz_agent = ReviewQuizAgent()
