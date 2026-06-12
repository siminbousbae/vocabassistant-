"""
Statistics API endpoints.
Provides: learning stats, daily progress, streak, mastery level.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from backend.database.connection import get_db
from backend.database.models import Word, Review, LearningRecord, DailyStats
from backend.agents.review_quiz import review_quiz_agent
from datetime import datetime, timedelta

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/overview")
async def get_overview_stats(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get comprehensive learning overview."""
    result = review_quiz_agent.run(action="stats", user_id=user_id)
    return result


@router.get("/words")
async def get_word_stats(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get word-related statistics."""
    word_query = db.query(Word)
    if user_id is not None:
        word_query = word_query.filter(Word.user_id == user_id)

    total = word_query.count()
    learned = word_query.filter(Word.learned == True).count()
    by_difficulty = word_query.with_entities(
        Word.difficulty,
        sql_func.count(Word.id)
    ).group_by(Word.difficulty).all()

    return {
        "total_words": total,
        "learned_words": learned,
        "learning_rate": round(learned / total * 100, 1) if total > 0 else 0,
        "by_difficulty": {f"level_{d}": c for d, c in by_difficulty}
    }


@router.get("/reviews")
async def get_review_stats(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get review activity statistics."""
    # Total reviews
    record_query = db.query(LearningRecord).filter(LearningRecord.action == "reviewed")
    review_query = db.query(Review)
    if user_id is not None:
        record_query = record_query.filter(LearningRecord.user_id == user_id)
        review_query = review_query.filter(Review.user_id == user_id)

    total_reviews = record_query.count()

    # Reviews this week
    week_ago = datetime.now() - timedelta(days=7)
    weekly_reviews = record_query.filter(
        LearningRecord.created_at >= week_ago
    ).count()

    # Reviews today
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_reviews = record_query.filter(
        LearningRecord.created_at >= today
    ).count()

    # Average quality
    avg_quality = record_query.with_entities(sql_func.avg(LearningRecord.score)).scalar()

    # Due words count
    due_count = review_query.filter(
        (Review.next_review_date == None) | (Review.next_review_date <= datetime.now())
    ).count()

    return {
        "total_reviews": total_reviews,
        "weekly_reviews": weekly_reviews,
        "daily_reviews": daily_reviews,
        "average_quality": round(avg_quality, 2) if avg_quality else 0,
        "due_words": due_count
    }


@router.get("/daily")
async def get_daily_stats(days: int = 30, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get daily learning statistics for the last N days."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    stats = db.query(DailyStats).filter(
        DailyStats.date >= start_date
    )
    if user_id is not None:
        stats = stats.filter(DailyStats.user_id == user_id)
    stats = stats.order_by(DailyStats.date).all()

    return {
        "period_days": days,
        "daily_data": [
            {
                "date": s.date,
                "words_added": s.words_added,
                "words_reviewed": s.words_reviewed,
                "words_learned": s.words_learned,
                "quiz_score_avg": s.quiz_score_avg,
                "study_minutes": s.study_minutes
            }
            for s in stats
        ]
    }


@router.get("/streak")
async def get_streak(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get current learning streak."""
    result = review_quiz_agent.run(action="stats", user_id=user_id)
    if result.get("success"):
        return {
            "current_streak": result["stats"]["current_streak"],
            "mastery_level": result["stats"]["mastery_level"]
        }
    return {"current_streak": 0, "mastery_level": "Novice"}


@router.get("/activity")
async def get_recent_activity(limit: int = 20, db: Session = Depends(get_db)):
    """Get recent learning activity."""
    records = db.query(LearningRecord).order_by(
        LearningRecord.created_at.desc()
    ).limit(limit).all()

    return {
        "activities": [
            {
                "id": r.id,
                "word_id": r.word_id,
                "action": r.action,
                "score": r.score,
                "details": r.details,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]
    }
