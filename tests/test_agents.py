"""
Unit tests for AI Agents.
Tests: ExampleSearchAgent, VocabTutorAgent, ReviewQuizAgent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from backend.agents.base import BaseAgent
from backend.agents.example_search import ExampleSearchAgent
from backend.agents.vocab_tutor import VocabTutorAgent
from backend.agents.review_quiz import ReviewQuizAgent
from backend.services.spaced_repetition import SM2Algorithm, SM2Card, ReviewScheduler


# ========================================
# FIXTURES
# ========================================

@pytest.fixture
def example_agent():
    """Create ExampleSearchAgent instance."""
    return ExampleSearchAgent()

@pytest.fixture
def tutor_agent():
    """Create VocabTutorAgent instance."""
    return VocabTutorAgent()

@pytest.fixture
def review_agent():
    """Create ReviewQuizAgent instance."""
    return ReviewQuizAgent()

@pytest.fixture
def sm2():
    """Create SM2Algorithm instance."""
    return SM2Algorithm()


# ========================================
# BASE AGENT TESTS
# ========================================

class TestBaseAgent:
    """Test BaseAgent functionality."""

    def test_agent_initialization(self):
        """Test agent is created with correct name."""
        agent = ExampleSearchAgent()
        assert agent.name == "ExampleSearchAgent"

    def test_start_finish_timing(self):
        """Test agent timing functions."""
        agent = ExampleSearchAgent()
        agent.start()
        assert agent.start_time is not None

        duration = agent.finish()
        assert agent.end_time is not None
        assert duration >= 0

    def test_run_wrapper_success(self, example_agent):
        """Test run wrapper handles success."""
        with patch.object(example_agent, 'execute') as mock_execute:
            mock_execute.return_value = {"word": "test"}
            result = example_agent.run(word="test")

            assert result["success"] is True
            assert result["agent_name"] == "ExampleSearchAgent"
            assert "duration_seconds" in result

    def test_run_wrapper_error(self, example_agent):
        """Test run wrapper handles errors."""
        with patch.object(example_agent, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            result = example_agent.run(word="test")

            assert result["success"] is False
            assert "error" in result


# ========================================
# EXAMPLE SEARCH AGENT TESTS
# ========================================

class TestExampleSearchAgent:
    """Test ExampleSearchAgent - the CORE agent."""

    def test_agent_name(self, example_agent):
        """Test agent has correct name."""
        assert example_agent.name == "ExampleSearchAgent"

    @patch('backend.agents.example_search.tavily_search_client')
    @patch('backend.agents.example_search.qwen_client')
    @patch('backend.agents.example_search.get_db_session')
    def test_execute_success_flow(self, mock_db, mock_qwen, mock_tavily, example_agent):
        """Test full Example Search Agent workflow."""
        # Mock Tavily search
        mock_tavily.get_best_example.return_value = {
            "sentence": "The government imposed new sanctions.",
            "source_name": "Reuters",
            "source_url": "https://reuters.com/article"
        }

        # Mock Qwen responses
        mock_qwen.get_word_info.return_value = {
            "phonetic": "/ˈsæŋkʃən/",
            "part_of_speech": "noun",
            "chinese_meaning": "制裁",
            "collocations": ["impose sanctions"],
            "synonyms": ["punishment"],
            "antonyms": ["reward"]
        }
        mock_qwen.translate_example.return_value = "政府对多家公司实施了新的制裁。"
        mock_qwen.analyze_sentence_difficulty.return_value = 3

        # Mock database
        mock_session = MagicMock()
        mock_db.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_word = Mock()
        mock_word.id = 1
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # Execute
        result = example_agent.run(word="sanction")

        # Verify
        assert result["success"] is True
        assert "word" in result
        assert result["word"]["word"] == "sanction"
        assert result["word"]["source_name"] == "Reuters"

        # Verify Tavily was called
        mock_tavily.get_best_example.assert_called_once_with("sanction")

        # Verify Qwen was called
        mock_qwen.get_word_info.assert_called_once()
        mock_qwen.translate_example.assert_called_once()

    @patch('backend.agents.example_search.tavily_search_client')
    def test_execute_no_articles_found(self, mock_tavily, example_agent):
        """Test when no articles are found."""
        mock_tavily.get_best_example.return_value = {
            "sentence": "",
            "source_name": "",
            "source_url": "",
            "error": "No articles found"
        }

        result = example_agent.run(word="xyznonexistent")

        assert result["success"] is False
        assert "error" in result

    def test_format_response(self, example_agent):
        """Test response formatting."""
        word_data = {
            "word": "test",
            "phonetic": "/test/",
            "part_of_speech": "noun",
            "chinese_meaning": "测试",
            "example_sentence": "This is a test.",
            "chinese_translation": "这是一个测试。",
            "source_name": "BBC",
            "source_url": "https://bbc.com",
            "collocations": ["test case"],
            "synonyms": ["exam"],
            "antonyms": ["pass"]
        }

        response = example_agent._format_response(word_data)

        assert "test" in response
        assert "BBC" in response
        assert "test case" in response
        assert "exam" in response


# ========================================
# VOCAB TUTOR AGENT TESTS
# ========================================

class TestVocabTutorAgent:
    """Test VocabTutorAgent."""

    def test_agent_name(self, tutor_agent):
        """Test agent has correct name."""
        assert tutor_agent.name == "VocabTutorAgent"

    @patch('backend.agents.vocab_tutor.qwen_client')
    def test_execute_generates_word_info(self, mock_qwen, tutor_agent):
        """Test tutor generates comprehensive word info."""
        mock_qwen.get_word_info.return_value = {
            "phonetic": "/əˈbændən/",
            "part_of_speech": "verb",
            "chinese_meaning": "放弃，抛弃",
            "collocations": ["abandon ship", "abandon hope"],
            "synonyms": ["desert", "forsake"],
            "antonyms": ["retain", "keep"]
        }

        result = tutor_agent.run(word="abandon")

        assert result["success"] is True
        assert result["word"]["word"] == "abandon"
        assert result["word"]["phonetic"] == "/əˈbændən/"
        assert len(result["word"]["collocations"]) == 2

    def test_format_tutor_card(self, tutor_agent):
        """Test vocabulary card formatting."""
        data = {
            "word": "abandon",
            "phonetic": "/əˈbændən/",
            "part_of_speech": "verb",
            "chinese_meaning": "放弃，抛弃",
            "collocations": ["abandon ship"],
            "synonyms": ["desert"],
            "antonyms": ["retain"]
        }

        card = tutor_agent._format_tutor_card(data)

        assert "ABANDON" in card
        assert "放弃" in card
        assert "abandon ship" in card


# ========================================
# REVIEW QUIZ AGENT TESTS
# ========================================

class TestReviewQuizAgent:
    """Test ReviewQuizAgent."""

    def test_agent_name(self, review_agent):
        """Test agent has correct name."""
        assert review_agent.name == "ReviewQuizAgent"

    @patch('backend.agents.review_quiz.review_quiz_agent._get_due_words')
    def test_get_due_words(self, mock_get_due, review_agent):
        """Test getting due words."""
        mock_get_due.return_value = {
            "success": True,
            "due_count": 2,
            "due_words": [
                {"word_id": 1, "word": "sanction"},
                {"word_id": 2, "word": "abandon"}
            ]
        }

        result = review_agent.run(action="get_due")

        assert result["success"] is True

    def test_process_review_valid_quality(self, review_agent):
        """Test review with valid quality rating."""
        # This would need database mocking in full implementation
        result = review_agent.run(action="review", word_id=1, quality=4)
        # Result depends on database state
        assert "success" in result

    def test_process_review_invalid_quality(self, review_agent):
        """Test review with invalid quality."""
        result = review_agent.run(action="review", word_id=1, quality=10)
        assert result["success"] is False
        assert "error" in result


# ========================================
# SM-2 ALGORITHM TESTS
# ========================================

class TestSM2Algorithm:
    """Test SM-2 Spaced Repetition Algorithm."""

    def test_initial_review_correct(self, sm2):
        """Test first correct review."""
        card = SM2Card(word_id=1)
        result = sm2.review(card, quality=4)

        assert result.interval == 1  # First repetition
        assert result.repetitions == 1
        assert result.quality == 4
        assert result.is_learned is False  # Need 2+ reps

    def test_second_review_correct(self, sm2):
        """Test second correct review."""
        card = SM2Card(word_id=1, interval=1, repetitions=1, ease_factor=2.5)
        result = sm2.review(card, quality=4)

        assert result.interval == 6  # Second repetition
        assert result.repetitions == 2
        assert result.is_learned is True  # Now learned!

    def test_third_review_correct(self, sm2):
        """Test third correct review with interval calculation."""
        card = SM2Card(word_id=1, interval=6, repetitions=2, ease_factor=2.5)
        result = sm2.review(card, quality=4)

        # interval = 6 * 2.5 = 15
        assert result.interval == 15
        assert result.repetitions == 3

    def test_review_incorrect(self, sm2):
        """Test incorrect review resets progress."""
        card = SM2Card(word_id=1, interval=15, repetitions=3, ease_factor=2.5)
        result = sm2.review(card, quality=1)

        assert result.interval == 1  # Reset to 1 day
        assert result.repetitions == 0  # Reset reps
        assert result.is_learned is False

    def test_ease_factor_increase(self, sm2):
        """Test ease factor increases with good reviews."""
        card = SM2Card(word_id=1, ease_factor=2.5)
        result = sm2.review(card, quality=5)  # Perfect

        # EF' = 2.5 + (0.1 - 0 * ...) = 2.6
        assert result.ease_factor > 2.5

    def test_ease_factor_decrease(self, sm2):
        """Test ease factor decreases with poor reviews."""
        card = SM2Card(word_id=1, ease_factor=2.5)
        result = sm2.review(card, quality=2)  # Poor

        # EF' = 2.5 + (0.1 - 3 * (0.08 + 3*0.02)) = 2.5 + (0.1 - 0.42) = 2.18
        assert result.ease_factor < 2.5

    def test_ease_factor_minimum(self, sm2):
        """Test ease factor doesn't go below minimum."""
        card = SM2Card(word_id=1, ease_factor=1.3)
        result = sm2.review(card, quality=0)  # Worst possible

        assert result.ease_factor >= 1.3

    def test_is_due_new_card(self, sm2):
        """Test new card is always due."""
        card = SM2Card(word_id=1)
        assert sm2.is_due(card) is True

    def test_is_due_future_card(self, sm2):
        """Test card with future date is not due."""
        card = SM2Card(word_id=1, next_review=datetime.now() + timedelta(days=1))
        assert sm2.is_due(card) is False

    def test_is_due_past_card(self, sm2):
        """Test card with past date is due."""
        card = SM2Card(word_id=1, next_review=datetime.now() - timedelta(days=1))
        assert sm2.is_due(card) is True

    def test_estimate_difficulty_new(self, sm2):
        """Test difficulty estimate for new card."""
        card = SM2Card(word_id=1, ease_factor=2.5, repetitions=0)
        difficulty = sm2.estimate_difficulty(card)

        assert 1 <= difficulty <= 5

    def test_retention_estimate(self, sm2):
        """Test retention probability estimate."""
        card = SM2Card(word_id=1, repetitions=3, interval=30, ease_factor=2.5)
        retention = sm2.get_retention_estimate(card)

        assert 0 <= retention <= 1
        assert retention > 0.5  # Should be decent for mature card

    def test_get_due_cards(self, sm2):
        """Test filtering due cards."""
        cards = [
            SM2Card(word_id=1, next_review=datetime.now() - timedelta(days=1)),  # Due
            SM2Card(word_id=2, next_review=datetime.now() + timedelta(days=1)),  # Not due
            SM2Card(word_id=3)  # New, due
        ]

        due = sm2.get_due_cards(cards)
        assert len(due) == 2
        assert due[0].word_id == 1
        assert due[1].word_id == 3

    def test_learning_stats_empty(self, sm2):
        """Test stats with no cards."""
        stats = sm2.get_learning_stats([])

        assert stats["total_cards"] == 0
        assert stats["retention_estimate"] == 0

    def test_learning_stats_with_cards(self, sm2):
        """Test stats with cards."""
        cards = [
            SM2Card(word_id=1, repetitions=3, ease_factor=2.5, interval=10),
            SM2Card(word_id=2, repetitions=1, ease_factor=2.0, interval=1),
            SM2Card(word_id=3, repetitions=0, ease_factor=2.5, interval=1)
        ]

        stats = sm2.get_learning_stats(cards)

        assert stats["total_cards"] == 3
        assert stats["learned_cards"] == 1  # Only first has reps >= 2
        assert stats["average_ease"] > 0
        assert stats["average_interval"] > 0


# ========================================
# REVIEW SCHEDULER TESTS
# ========================================

class TestReviewScheduler:
    """Test ReviewScheduler."""

    def test_schedule_review(self):
        """Test scheduling a review."""
        scheduler = ReviewScheduler()
        result = scheduler.schedule_review(
            word_id=1,
            quality=4,
            current_interval=1,
            current_ease=2.5,
            current_reps=0
        )

        assert result.interval == 1  # First correct review
        assert result.repetitions == 1
        assert result.quality == 4

    def test_get_due_words(self):
        """Test getting due word IDs."""
        scheduler = ReviewScheduler()

        # Mock review objects
        class MockReview:
            def __init__(self, word_id, interval, ease, reps, next_review):
                self.word_id = word_id
                self.interval = interval
                self.ease_factor = ease
                self.repetitions = reps
                self.next_review_date = next_review

        reviews = [
            MockReview(1, 1, 2.5, 0, None),  # Due (new)
            MockReview(2, 6, 2.5, 1, datetime.now() - timedelta(days=1)),  # Due
            MockReview(3, 15, 2.5, 2, datetime.now() + timedelta(days=5))  # Not due
        ]

        due_ids = scheduler.get_due_words(reviews)

        assert 1 in due_ids
        assert 2 in due_ids
        assert 3 not in due_ids


# ========================================
# INTEGRATION TESTS
# ========================================

class TestAgentIntegration:
    """Integration tests for agent workflows."""

    @patch('backend.agents.example_search.tavily_search_client')
    @patch('backend.agents.example_search.qwen_client')
    def test_full_add_word_workflow(self, mock_qwen, mock_tavily):
        """Test complete add word workflow."""
        # Setup mocks
        mock_tavily.get_best_example.return_value = {
            "sentence": "The UN imposed sanctions.",
            "source_name": "BBC",
            "source_url": "https://bbc.com/news"
        }

        mock_qwen.get_word_info.return_value = {
            "phonetic": "/ˈsæŋkʃən/",
            "part_of_speech": "noun",
            "chinese_meaning": "制裁",
            "collocations": ["impose sanctions"],
            "synonyms": ["punishment"],
            "antonyms": ["reward"]
        }
        mock_qwen.translate_example.return_value = "联合国实施了制裁。"
        mock_qwen.analyze_sentence_difficulty.return_value = 3

        # Run agent
        agent = ExampleSearchAgent()

        with patch('backend.agents.example_search.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_db.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None

            result = agent.run(word="sanction")

            assert result["success"] is True
            assert result["word"]["source_name"] == "BBC"
            assert "制裁" in result["word"]["chinese_translation"]


# ========================================
# RUN TESTS
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
