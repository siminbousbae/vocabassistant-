"""
Agent trigger API endpoints.
Directly trigger agents via HTTP API.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.agents.example_search import example_search_agent
from backend.agents.vocab_tutor import vocab_tutor_agent
from backend.agents.review_quiz import review_quiz_agent

router = APIRouter(prefix="/agents", tags=["Agents"])


# Pydantic schemas
class AddWordRequest(BaseModel):
    word: str
    user_id: Optional[int] = None

class TutorRequest(BaseModel):
    word: str
    user_id: Optional[int] = None

class ReviewRequest(BaseModel):
    word_id: int
    quality: int  # 0-5
    user_id: Optional[int] = None


@router.post("/example-search")
async def trigger_example_search(request: AddWordRequest):
    """
    Trigger the Example Search Agent.

    This is the CORE agent that:
    - Searches Tavily for real news articles
    - Extracts sentences with the target word
    - Uses Qwen to select best example and translate
    - Saves everything to database

    Returns complete word data with real example from news.
    """
    result = example_search_agent.run(word=request.word, user_id=request.user_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Agent failed"))

    return {
        "success": True,
        "agent": "ExampleSearchAgent",
        "data": result
    }


@router.post("/vocab-tutor")
async def trigger_vocab_tutor(request: TutorRequest):
    """
    Trigger the Vocabulary Tutor Agent.

    Generates comprehensive word info:
    - Phonetic symbol
    - Part of speech
    - Chinese meaning
    - Common collocations
    - Synonyms
    - Antonyms
    """
    result = vocab_tutor_agent.run(word=request.word, user_id=request.user_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Agent failed"))

    return {
        "success": True,
        "agent": "VocabTutorAgent",
        "data": result
    }


@router.post("/review")
async def trigger_review(request: ReviewRequest):
    """
    Submit a review with quality rating.

    Quality scale (SM-2):
    5 = Perfect response
    4 = Correct after hesitation
    3 = Correct with difficulty
    2 = Incorrect, correct remembered
    1 = Incorrect, correct easy to recall
    0 = Complete blackout
    """
    result = review_quiz_agent.run(
        action="review",
        word_id=request.word_id,
        quality=request.quality,
        user_id=request.user_id
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Review failed"))

    return {
        "success": True,
        "agent": "ReviewQuizAgent",
        "data": result
    }


@router.get("/due-words")
async def get_due_words(user_id: Optional[int] = None):
    """Get words due for review today."""
    result = review_quiz_agent.run(action="get_due", user_id=user_id)
    return {
        "success": True,
        "data": result
    }


@router.get("/quiz")
async def get_quiz(user_id: Optional[int] = None, num_questions: int = 5):
    """Generate a quiz with multiple choice questions."""
    result = review_quiz_agent.run(action="quiz", user_id=user_id, limit=num_questions)
    return {
        "success": True,
        "data": result
    }
