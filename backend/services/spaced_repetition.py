"""
SM-2 Spaced Repetition Algorithm Implementation.

The SM-2 algorithm is the foundation of Anki and many SRS systems.
It calculates optimal review intervals based on user performance.

Algorithm:
1. Quality rating: 0-5 (5=perfect, 0=blackout)
2. If quality >= 3 (correct):
   - First repetition: interval = 1 day
   - Second repetition: interval = 6 days
   - Subsequent: interval = previous_interval * ease_factor
   - Increase repetitions
3. If quality < 3 (incorrect):
   - Reset interval to 1 day
   - Reset repetitions to 0
4. Update ease_factor:
   - ease_factor = ease_factor + (0.1 - (5-quality) * (0.08 + (5-quality) * 0.02))
   - Minimum ease_factor = 1.3
5. Schedule next review: now + interval days

Features:
- SM-2 core algorithm
- Due date calculation
- Learning statistics
- Difficulty estimation
- Customizable parameters
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class SM2Result:
    """Result of SM-2 calculation."""
    interval: int           # Days until next review
    ease_factor: float      # Updated ease factor
    repetitions: int        # Updated repetition count
    quality: int            # Input quality rating
    next_review_date: datetime
    is_learned: bool       # True if repetitions >= 2 and quality >= 3


@dataclass
class SM2Card:
    """Represents a card/review item in SM-2."""
    word_id: int
    interval: int = 1
    ease_factor: float = 2.5
    repetitions: int = 0
    quality: Optional[int] = None
    last_review: Optional[datetime] = None
    next_review: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word_id": self.word_id,
            "interval": self.interval,
            "ease_factor": self.ease_factor,
            "repetitions": self.repetitions,
            "quality": self.quality,
            "last_review": self.last_review.isoformat() if self.last_review else None,
            "next_review": self.next_review.isoformat() if self.next_review else None
        }


class SM2Algorithm:
    """
    SM-2 Spaced Repetition Algorithm.

    Based on the SuperMemo-2 algorithm by Piotr Wozniak.
    """

    # SM-2 constants
    MIN_EASE_FACTOR = 1.3
    INITIAL_INTERVAL = 1
    SECOND_INTERVAL = 6

    def __init__(self, min_ease: float = 1.3):
        self.min_ease = min_ease

    def review(self, card: SM2Card, quality: int) -> SM2Result:
        """
        Process a review and calculate next interval.

        Args:
            card: Current card state
            quality: Quality of response (0-5)

        Returns:
            SM2Result with updated scheduling
        """
        if not (0 <= quality <= 5):
            raise ValueError("Quality must be between 0 and 5")

        # Update ease factor
        new_ease = self._calculate_ease_factor(card.ease_factor, quality)

        # Calculate new interval and repetitions
        if quality >= 3:
            # Correct response
            new_reps = card.repetitions + 1

            if new_reps == 1:
                new_interval = self.INITIAL_INTERVAL
            elif new_reps == 2:
                new_interval = self.SECOND_INTERVAL
            else:
                new_interval = round(card.interval * new_ease)
        else:
            # Incorrect response - reset
            new_reps = 0
            new_interval = self.INITIAL_INTERVAL

        # Calculate next review date
        next_review = datetime.now() + timedelta(days=new_interval)

        # Determine if word is "learned"
        is_learned = new_reps >= 2 and quality >= 3

        return SM2Result(
            interval=new_interval,
            ease_factor=new_ease,
            repetitions=new_reps,
            quality=quality,
            next_review_date=next_review,
            is_learned=is_learned
        )

    def _calculate_ease_factor(self, current_ease: float, quality: int) -> float:
        """
        Calculate new ease factor.

        Formula: EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
        Minimum: 1.3
        """
        new_ease = current_ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        return max(self.min_ease, new_ease)

    def is_due(self, card: SM2Card) -> bool:
        """Check if a card is due for review."""
        if card.next_review is None:
            return True  # New card
        return datetime.now() >= card.next_review

    def get_due_cards(self, cards: List[SM2Card]) -> List[SM2Card]:
        """Filter cards that are due for review."""
        return [card for card in cards if self.is_due(card)]

    def estimate_difficulty(self, card: SM2Card) -> int:
        """
        Estimate word difficulty based on review history.

        Returns: 1-5 difficulty rating
        """
        # Lower ease factor = harder word
        # Fewer repetitions = newer/harder word

        ease_score = min(5, max(1, int((3.0 - card.ease_factor) * 2.5 + 3)))
        rep_score = min(5, max(1, card.repetitions + 1))

        # Weighted average
        difficulty = int((ease_score * 0.6 + rep_score * 0.4))
        return min(5, max(1, difficulty))

    def get_retention_estimate(self, card: SM2Card) -> float:
        """
        Estimate retention probability for a card.

        Based on interval and ease factor.
        Higher = better retention.
        """
        if card.repetitions == 0:
            return 0.5  # Unknown

        # Simplified estimate
        base_retention = 0.9
        ease_bonus = (card.ease_factor - 1.3) / 2.0 * 0.1
        interval_penalty = min(0.2, card.interval / 365 * 0.1)

        return min(0.99, base_retention + ease_bonus - interval_penalty)

    def get_study_plan(self, cards: List[SM2Card], days: int = 7) -> Dict[str, List[int]]:
        """
        Generate study plan for upcoming days.

        Returns:
            Dict mapping date string to list of word IDs
        """
        plan = {}

        for day_offset in range(days):
            date = (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            plan[date] = []

        for card in cards:
            if card.next_review:
                review_date = card.next_review.strftime("%Y-%m-%d")
                if review_date in plan:
                    plan[review_date].append(card.word_id)

        return plan

    def get_learning_stats(self, cards: List[SM2Card]) -> Dict[str, Any]:
        """Get statistics about learning progress."""
        if not cards:
            return {
                "total_cards": 0,
                "learned_cards": 0,
                "average_ease": 0,
                "average_interval": 0,
                "due_today": 0,
                "retention_estimate": 0
            }

        total = len(cards)
        learned = sum(1 for c in cards if c.repetitions >= 2)
        due = sum(1 for c in cards if self.is_due(c))
        avg_ease = sum(c.ease_factor for c in cards) / total
        avg_interval = sum(c.interval for c in cards) / total
        avg_retention = sum(self.get_retention_estimate(c) for c in cards) / total

        return {
            "total_cards": total,
            "learned_cards": learned,
            "learning_rate": round(learned / total * 100, 1),
            "average_ease": round(avg_ease, 2),
            "average_interval": round(avg_interval, 1),
            "due_today": due,
            "retention_estimate": round(avg_retention * 100, 1)
        }

    def get_optimal_new_cards_per_day(self, cards: List[SM2Card]) -> int:
        """
        Recommend optimal number of new cards per day.

        Based on current workload and retention.
        """
        due_count = sum(1 for c in cards if self.is_due(c))
        avg_interval = sum(c.interval for c in cards) / len(cards) if cards else 1

        # Base recommendation
        base = 20

        # Adjust based on due count
        if due_count > 50:
            base = 10
        elif due_count < 10:
            base = 30

        # Adjust based on average interval (mature cards = more new cards ok)
        if avg_interval > 30:
            base += 5

        return base


class ReviewScheduler:
    """
    High-level review scheduler that uses SM-2.
    Integrates with database models.
    """

    def __init__(self):
        self.sm2 = SM2Algorithm()

    def schedule_review(self, word_id: int, quality: int, 
                        current_interval: int = 1,
                        current_ease: float = 2.5,
                        current_reps: int = 0) -> SM2Result:
        """
        Schedule next review for a word.

        Args:
            word_id: Word ID
            quality: Review quality (0-5)
            current_interval: Current interval in days
            current_ease: Current ease factor
            current_reps: Current repetition count

        Returns:
            SM2Result with scheduling info
        """
        card = SM2Card(
            word_id=word_id,
            interval=current_interval,
            ease_factor=current_ease,
            repetitions=current_reps
        )

        return self.sm2.review(card, quality)

    def get_due_words(self, reviews: List[Any]) -> List[int]:
        """
        Get list of word IDs due for review.

        Args:
            reviews: List of Review database objects

        Returns:
            List of word IDs
        """
        due_ids = []

        for review in reviews:
            card = SM2Card(
                word_id=review.word_id,
                interval=review.interval or 1,
                ease_factor=review.ease_factor or 2.5,
                repetitions=review.repetitions or 0,
                next_review=review.next_review_date
            )

            if self.sm2.is_due(card):
                due_ids.append(review.word_id)

        return due_ids

    def calculate_daily_workload(self, reviews: List[Any]) -> Dict[str, Any]:
        """
        Calculate daily review workload.

        Returns:
            Dict with workload statistics
        """
        cards = []
        for review in reviews:
            cards.append(SM2Card(
                word_id=review.word_id,
                interval=review.interval or 1,
                ease_factor=review.ease_factor or 2.5,
                repetitions=review.repetitions or 0,
                next_review=review.next_review_date
            ))

        stats = self.sm2.get_learning_stats(cards)
        plan = self.sm2.get_study_plan(cards, days=7)

        return {
            "stats": stats,
            "weekly_plan": plan,
            "recommended_new_cards": self.sm2.get_optimal_new_cards_per_day(cards)
        }


# Global instances
sm2_algorithm = SM2Algorithm()
review_scheduler = ReviewScheduler()
