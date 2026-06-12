from backend.database.connection import get_db_session
from backend.database.models import Word, Review

db = get_db_session()

words = db.query(Word).all()
print(f"Found {len(words)} words")

for word in words:
    review = db.query(Review).filter(Review.word_id == word.id).first()
    if not review:
        review = Review(
            word_id=word.id,
            interval=1,
            ease_factor=2.5,
            repetitions=0,
            is_due=True,
            next_review_date=None
        )
        db.add(review)
        print(f"Created review for: {word.word}")
    else:
        review.is_due = True
        review.next_review_date = None
        print(f"Reset review for: {word.word}")

db.commit()
print("Done! All words are now due for review.")