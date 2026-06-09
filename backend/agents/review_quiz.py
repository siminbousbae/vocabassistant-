"""
Review & Quiz Agent with Spaced Repetition (SM-2 Algorithm).

Features:
- SM-2 spaced repetition algorithm for optimal review scheduling
- Quiz generation using Qwen LLM
- Review history tracking
- Daily due words calculation
- Learning statistics

Input: user_id, action ("get_due", "review", "quiz")
Output: Due words list, quiz questions, or review results
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
    """
    Review & Quiz Agent: Manages spaced repetition and generates quizzes.
    Implements the SM-2 algorithm for optimal learning.
    """

    def __init__(self):
        super().__init__("ReviewQuizAgent")

    def execute(self, action: str, user_id: Optional[int] = None,
                word_id: Optional[int] = None, quality: Optional[int] = None,
                **kwargs) -> Dict[str, Any]:
        """
        Execute review/quiz action.

        Actions:
        - "get_due": Get list of words due for review
        - "review": Submit a review with quality rating (0-5)
        - "quiz": Generate quiz for due words
        - "stats": Get learning statistics
        """
        if action == "get_due":
            return self._get_due_words(user_id)
        elif action == "review":
            return self._process_review(word_id, quality, user_id)
        elif action == "quiz":
            return self._generate_quiz(user_id)
        elif action == "stats":
            return self._get_stats(user_id)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    def _get_due_words(self, user_id: Optional[int] = None, limit: int = 20) -> Dict[str, Any]:
        """Get words that are due for review today."""
        db = get_db_session()
        try:
            now = datetime.now()

            query = db.query(Word, Review).join(Review, Word.id == Review.word_id)

            # Build filters properly
            filters = [Review.is_due == True]

            # Due date filter
            due_filter = or_(
                Review.next_review_date == None,
                Review.next_review_date <= now
            )
            filters.append(due_filter)

            # Apply user filter only if provided
            if user_id is not None:
                filters.append(Review.user_id == user_id)

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
                    "repetitions": review.repetitions,
                    "interval": review.interval,
                    "ease_factor": review.ease_factor
                })

            return {
                "success": True,
                "due_count": len(due_words),
                "due_words": due_words,
                "message": f"You have {len(due_words)} words to review today!"
            }

        finally:
            db.close()

    def _process_review(self, word_id: int, quality: int,
                        user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Process a review with SM-2 algorithm.

        Quality: 0-5 scale
        5 = perfect response
        4 = correct response after hesitation
        3 = correct response with serious difficulty
        2 = incorrect response; correct one remembered
        1 = incorrect response; correct one easy to recall
        0 = complete blackout
        """
        if quality is None or not (0 <= quality <= 5):
            return {"success": False, "error": "Quality must be 0-5"}

        db = get_db_session()
        try:
            # Build query properly
            query = db.query(Review).filter(Review.word_id == word_id)
            if user_id is not None:
                query = query.filter(Review.user_id == user_id)
            review = query.first()

            if not review:
                return {"success": False, "error": "Review record not found"}

            word = db.query(Word).filter(Word.id == word_id).first()

            # SM-2 Algorithm
            old_interval = review.interval
            old_ease = review.ease_factor
            old_reps = review.repetitions

            if quality >= 3:
                # Correct response
                if old_reps == 0:
                    new_interval = 1
                elif old_reps == 1:
                    new_interval = 6
                else:
                    new_interval = round(old_interval * old_ease)

                new_reps = old_reps + 1
            else:
                # Incorrect response - reset
                new_interval = 1
                new_reps = 0

            # Update ease factor
            new_ease = old_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            new_ease = max(1.3, new_ease)  # Minimum ease factor 1.3

            # Update review record
            review.interval = new_interval
            review.ease_factor = new_ease
            review.repetitions = new_reps
            review.quality = quality
            review.reviewed_count = (review.reviewed_count or 0) + 1  # FIX: handle None
            review.review_date = datetime.now()
            review.next_review_date = datetime.now() + timedelta(days=new_interval)
            review.is_due = False  # Will become due again based on interval

            # Mark word as learned if quality >= 3 and reps >= 2
            if quality >= 3 and new_reps >= 2 and word:
                word.learned = True

            db.commit()

            # Log activity
            self.log_activity(
                word_id=word_id,
                action="reviewed",
                score=quality,
                details={
                    "interval": new_interval,
                    "ease": new_ease,
                    "reps": new_reps
                }
            )

            # Update daily stats
            self._update_daily_stats(user_id, "review")

            return {
                "success": True,
                "word_id": word_id,
                "word": word.word if word else "",
                "quality": quality,
                "next_review_in_days": new_interval,
                "next_review_date": review.next_review_date.isoformat(),
                "message": f"Reviewed '{word.word if word else ''}'. Next review in {new_interval} day(s)."
            }

        finally:
            db.close()

    def _generate_quiz(self, user_id: Optional[int] = None,
                       num_questions: int = 5) -> Dict[str, Any]:
        """Generate quiz questions for due words."""
        db = get_db_session()
        try:
            # Get due words
            due_result = self._get_due_words(user_id, limit=num_questions)
            due_words = due_result.get("due_words", [])

            if not due_words:
                return {
                    "success": True,
                    "quiz": [],
                    "message": "No words due for quiz! Great job!"
                }

            questions = []
            for word_data in due_words:
                try:
                    # Generate quiz question using Qwen
                    quiz = qwen_client.generate_quiz_question(
                        word_data["word"],
                        word_data["chinese_meaning"]
                    )

                    questions.append({
                        "word_id": word_data["word_id"],
                        "word": word_data["word"],
                        "question": quiz["question"],
                        "options": quiz["options"],
                        "correct_index": quiz["correct_index"],
                        "explanation": quiz["explanation"]
                    })
                except Exception as e:
                    print(f"Failed to generate quiz for {word_data['word']}: {e}")
                    continue

            return {
                "success": True,
                "quiz": questions,
                "message": f"Quiz with {len(questions)} questions ready!"
            }

        finally:
            db.close()

    def _get_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive learning statistics."""
        db = get_db_session()
        try:
            # Total words
            total_words = db.query(Word).count()
            learned_words = db.query(Word).filter(Word.learned == True).count()

            # Due today
            due_result = self._get_due_words(user_id)
            due_count = due_result["due_count"]

            # Reviews this week
            week_ago = datetime.now() - timedelta(days=7)
            weekly_reviews = db.query(LearningRecord).filter(
                LearningRecord.action == "reviewed",
                LearningRecord.created_at >= week_ago
            ).count()

            # Average quality
            avg_quality = db.query(LearningRecord).filter(
                LearningRecord.action == "reviewed"
            ).with_entities(func.avg(LearningRecord.score)).scalar()

            # Streak calculation
            streak = self._calculate_streak(user_id)

            return {
                "success": True,
                "stats": {
                    "total_words": total_words,
                    "learned_words": learned_words,
                    "learning_rate": round(learned_words / total_words * 100, 1) if total_words > 0 else 0,
                    "due_today": due_count,
                    "weekly_reviews": weekly_reviews,
                    "average_quality": round(avg_quality, 2) if avg_quality else 0,
                    "current_streak": streak,
                    "mastery_level": self._get_mastery_level(learned_words)
                }
            }

        finally:
            db.close()

    def _calculate_streak(self, user_id: Optional[int] = None) -> int:
        """Calculate current daily learning streak."""
        db = get_db_session()
        try:
            from sqlalchemy import func as sql_func

            # Get distinct dates with activity
            records = db.query(
                sql_func.date(LearningRecord.created_at).label("date")
            ).distinct().order_by(sql_func.date(LearningRecord.created_at).desc()).all()

            if not records:
                return 0

            streak = 0
            today = datetime.now().date()

            for i, record in enumerate(records):
                # Handle both string and date object returns from SQLAlchemy
                if isinstance(record.date, str):
                    record_date = datetime.strptime(record.date, "%Y-%m-%d").date()
                else:
                    record_date = record.date

                expected_date = today - timedelta(days=i)

                if record_date == expected_date:
                    streak += 1
                else:
                    break

            return streak

        finally:
            db.close()

    def _get_mastery_level(self, learned_words: int) -> str:
        """Get mastery level based on learned words count."""
        if learned_words >= 500:
            return "Expert"
        elif learned_words >= 200:
            return "Advanced"
        elif learned_words >= 50:
            return "Intermediate"
        elif learned_words >= 10:
            return "Beginner"
        else:
            return "Novice"

    def _update_daily_stats(self, user_id: Optional[int] = None, action_type: str = "review"):
        """Update daily statistics aggregation."""
        db = get_db_session()
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            stat = db.query(DailyStats).filter(
                DailyStats.date == today,
                DailyStats.user_id == user_id
            ).first()

            if not stat:
                stat = DailyStats(user_id=user_id, date=today)
                db.add(stat)

            # FIX: Handle None values
            if action_type == "review":
                stat.words_reviewed = (stat.words_reviewed or 0) + 1
            elif action_type == "add":
                stat.words_added = (stat.words_added or 0) + 1

            db.commit()

        finally:
            db.close()

    def schedule_daily_review(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get today's review schedule with all due words."""
        return self._get_due_words(user_id, limit=50)


# Global instance
review_quiz_agent = ReviewQuizAgent()