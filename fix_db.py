from backend.database.connection import get_db_session
from backend.database.models import Word, Review
from datetime import datetime

db = get_db_session()

words = db.query(Word).all()
fixed = 0

for word in words:
    review = db.query(Review).filter(Review.word_id == word.id).first()
    if not review:
        # Create missing review
        review = Review(
            word_id=word.id,
            user_id=word.user_id,
            interval=1,
            ease_factor=2.5,
            repetitions=0,
            is_due=True,
            next_review_date=None
        )
        db.add(review)
        fixed += 1
    else:
        # Force existing review to be due
        review.is_due = True
        review.next_review_date = None
        fixed += 1

db.commit()
print(f"Fixed {fixed} words. Now refresh your browser and click Review!")