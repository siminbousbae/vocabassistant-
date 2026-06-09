"""
Base Agent class for the Vocabulary Assistant.
Provides shared functionality: logging, database access, error handling.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from backend.database.connection import get_db_session
from backend.database.models import LearningRecord


class BaseAgent(ABC):
    """Abstract base class for all vocabulary agents."""

    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None

    def log_activity(self, word_id: int, action: str, score: Optional[int] = None, details: Optional[Dict] = None):
        """Log agent activity to learning_records table."""
        try:
            db = get_db_session()
            record = LearningRecord(
                word_id=word_id,
                action=action,
                score=score,
                details=details
            )
            db.add(record)
            db.commit()
            db.close()
        except Exception as e:
            print(f"Failed to log activity: {e}")

    def start(self):
        """Start agent execution timer."""
        self.start_time = time.time()
        print(f"[{self.name}] Agent started at {datetime.now()}")

    def finish(self) -> float:
        """Finish agent execution and return duration."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        print(f"[{self.name}] Agent finished in {duration:.2f}s")
        return duration

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Main execution method - must be implemented by subclasses."""
        pass

    def run(self, **kwargs) -> Dict[str, Any]:
        """Wrapper that handles timing and error catching."""
        self.start()
        try:
            result = self.execute(**kwargs)
            result["agent_name"] = self.name
            # Don't overwrite success if agent already set it
            if "success" not in result:
                result["success"] = True
        except Exception as e:
            result = {
                "agent_name": self.name,
                "success": False,
                "error": str(e)
            }
            print(f"[{self.name}] Error: {e}")
        finally:
            duration = self.finish()
            result["duration_seconds"] = duration

        return result