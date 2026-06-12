from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel
from backend.database.connection import get_db
from backend.database.models import Word, Review
from backend.agents.example_search import example_search_agent
from backend.agents.vocab_tutor import vocab_tutor_agent

router = APIRouter(prefix="/words", tags=["Words"])

# Pydantic schemas
class WordCreate(BaseModel):
    word: str
    user_id: Optional[int] = None

class WordUpdate(BaseModel):
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    chinese_meaning: Optional[str] = None
    example_sentence: Optional[str] = None
    chinese_translation: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[List[str]] = None
    difficulty: Optional[int] = None

class WordResponse(BaseModel):
    id: int
    word: str
    phonetic: Optional[str] = None
    part_of_speech: Optional[str] = None
    chinese_meaning: Optional[str] = None
    example_sentence: Optional[str] = None
    chinese_translation: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    collocations: Optional[List[str]] = None
    synonyms: Optional[List[str]] = None
    antonyms: Optional[List[str]] = None
    difficulty: int = 1
    is_due: bool = False
    learned: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

def _word_to_dict(word: Word) -> dict:
    """Convert Word ORM object to dict with datetime fields as strings."""
    is_due = True
    if word.reviews:
        review = word.reviews[0]
        is_due = (
            review.next_review_date is None
            or review.next_review_date <= datetime.now()
        )

    return {
        "id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "part_of_speech": word.part_of_speech,
        "chinese_meaning": word.chinese_meaning,
        "example_sentence": word.example_sentence,
        "chinese_translation": word.chinese_translation,
        "source_name": word.source_name,
        "source_url": word.source_url,
        "collocations": word.collocations,
        "synonyms": word.synonyms,
        "antonyms": word.antonyms,
        "difficulty": word.difficulty,
        "is_due": is_due,
        "learned": word.learned,
        "created_at": word.created_at.isoformat() if word.created_at else None,
    }

@router.post("/add", response_model=WordResponse)
async def add_word(data: WordCreate, db: Session = Depends(get_db)):
    """
    Add a new word using the Example Search Agent.
    """
    existing = db.query(Word).filter(Word.word == data.word.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Word '{data.word}' already exists")

    result = example_search_agent.run(word=data.word, user_id=data.user_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Agent failed"))

    db_word = db.query(Word).filter(Word.word == data.word.lower()).first()
    if not db_word:
        raise HTTPException(status_code=500, detail="Agent completed but word was not saved")

    # Create a review record so the word appears in daily reviews
    review = db.query(Review).filter(Review.word_id == db_word.id).first()
    if not review:
        review = Review(
            word_id=db_word.id,
            user_id=data.user_id,
            interval=1,
            ease_factor=2.5,
            repetitions=0,
            is_due=True,
            next_review_date=None
        )
        db.add(review)
        db.commit()

    return _word_to_dict(db_word)

@router.get("/query/{word}", response_model=WordResponse)
async def query_word(word: str, db: Session = Depends(get_db)):
    """Query a word by its text."""
    db_word = db.query(Word).filter(Word.word == word.lower()).first()
    if not db_word:
        raise HTTPException(status_code=404, detail=f"Word '{word}' not found")
    return _word_to_dict(db_word)

@router.get("/list", response_model=List[WordResponse])
async def list_words(
    skip: int = 0,
    limit: int = 50,
    learned: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all words with pagination and optional filtering."""
    query = db.query(Word).options(selectinload(Word.reviews))
    if learned is not None:
        query = query.filter(Word.learned == learned)
    words = query.order_by(Word.created_at.desc(), Word.id.desc()).offset(skip).limit(limit).all()
    return [_word_to_dict(w) for w in words]

@router.put("/update/{word_id}", response_model=WordResponse)
async def update_word(word_id: int, data: WordUpdate, db: Session = Depends(get_db)):
    """Update a word's information."""
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    for field, value in data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(db_word, field, value)

    db.commit()
    db.refresh(db_word)
    return _word_to_dict(db_word)

@router.delete("/delete/{word_id}")
async def delete_word(word_id: int, db: Session = Depends(get_db)):
    """Delete a word and its associated reviews."""
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    # Delete associated reviews
    db.query(Review).filter(Review.word_id == word_id).delete()

    db.delete(db_word)
    db.commit()
    return {"success": True, "message": "Word deleted successfully"}

@router.post("/enrich/{word_id}")
async def enrich_word(word_id: int, db: Session = Depends(get_db)):
    """Enrich a word with additional information using the Vocab Tutor Agent."""
    db_word = db.query(Word).filter(Word.id == word_id).first()
    if not db_word:
        raise HTTPException(status_code=404, detail="Word not found")

    result = vocab_tutor_agent.run(word=db_word.word, word_id=word_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Enrichment failed"))

    # Refresh word data after enrichment
    db.refresh(db_word)
    return _word_to_dict(db_word)
