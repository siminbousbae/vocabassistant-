"""
Review and Quiz API endpoints.
Handles: daily reviews, quiz sessions, review submission, force review.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database.connection import get_db
from backend.database.models import Word, Review
from backend.agents.review_quiz import review_quiz_agent
from datetime import datetime

router = APIRouter(prefix="/review", tags=["Review & Quiz"])

# Pydantic schemas
class ReviewSubmit(BaseModel):
    word_id: int
    quality: int  # 0-5 SM-2 scale
    user_id: Optional[int] = None

class QuizAnswer(BaseModel):
    word_id: int
    selected_index: int
    correct_index: int
    user_id: Optional[int] = None

@router.get("/due")
async def get_due_words(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all words due for review today."""
    result = review_quiz_agent.run(action="get_due", user_id=user_id)
    return result

# ========== NEW: Force Review Endpoint ==========
@router.get("/word/{word_id}")
async def get_word_for_review(word_id: int, db: Session = Depends(get_db)):
    """
    Get a specific word for review, regardless of due status.
    Used when user clicks "Review" on a word card.
    """
    word = db.query(Word).filter(Word.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    # Get or create review record
    review = db.query(Review).filter(Review.word_id == word_id).first()
    if not review:
        # Create review record if missing
        review = Review(
            word_id=word_id,
            interval=1,
            ease_factor=2.5,
            repetitions=0,
            is_due=True,
            next_review_date=None
        )
        db.add(review)
        db.commit()

    return {
        "success": True,
        "word_id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "chinese_meaning": word.chinese_meaning,
        "example_sentence": word.example_sentence,
        "chinese_translation": word.chinese_translation,
        "is_due": review.is_due,
        "repetitions": review.repetitions,
        "interval": review.interval,
        "message": "Review this word now!"
    }

@router.post("/submit")
async def submit_review(data: ReviewSubmit, db: Session = Depends(get_db)):
    """
    Submit a review with quality rating.
    Updates SM-2 spaced repetition schedule.
    """
    if not (0 <= data.quality <= 5):
        raise HTTPException(status_code=400, detail="Quality must be between 0 and 5")

    result = review_quiz_agent.run(
        action="review",
        word_id=data.word_id,
        quality=data.quality,
        user_id=data.user_id
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result

@router.get("/quiz")
async def get_quiz(user_id: Optional[int] = None, num_questions: int = 5):
    """Generate a quiz with multiple choice questions."""
    result = review_quiz_agent.run(
        action="quiz",
        user_id=user_id
    )
    return result

@router.post("/quiz/answer")
async def submit_quiz_answer(data: QuizAnswer, db: Session = Depends(get_db)):
    """
    Submit a quiz answer and get feedback.
    Also updates the review schedule based on correctness.
    """
    is_correct = data.selected_index == data.correct_index

    # Map correctness to SM-2 quality
    quality = 4 if is_correct else 1

    # Update review
    result = review_quiz_agent.run(
        action="review",
        word_id=data.word_id,
        quality=quality,
        user_id=data.user_id
    )

    return {
        "success": True,
        "correct": is_correct,
        "quality": quality,
        "review_result": result
    }

@router.get("/word/{word_id}/history")
async def get_word_review_history(word_id: int, db: Session = Depends(get_db)):
    """Get review history for a specific word."""
    reviews = db.query(Review).filter(Review.word_id == word_id).all()

    return {
        "word_id": word_id,
        "total_reviews": len(reviews),
        "reviews": [
            {
                "date": r.review_date.isoformat() if r.review_date else None,
                "quality": r.quality,
                "interval": r.interval,
                "ease_factor": r.ease_factor,
                "repetitions": r.repetitions
            }
            for r in reviews
        ]
    }

@router.post("/reset/{word_id}")
async def reset_word_progress(word_id: int, db: Session = Depends(get_db)):
    """Reset review progress for a word (start over)."""
    review = db.query(Review).filter(Review.word_id == word_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")

    review.interval = 1
    review.ease_factor = 2.5
    review.repetitions = 0
    review.quality = None
    review.is_due = True
    review.next_review_date = None

    # Reset learned status
    word = db.query(Word).filter(Word.id == word_id).first()
    if word:
        word.learned = False

    db.commit()

    return {
        "success": True,
        "message": f"Progress reset for word '{word.word if word else word_id}'"
    }