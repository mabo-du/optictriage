"""base.py — Abstract base class for pipeline stages.
exports: Stage, StageError
used_by: pipeline.py → Orchestrator, import_stage.py → ImportStage
rules:
All stages must implement the run() method and yield progress updates.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional
import traceback

class StageError(Exception):
    """Exception raised for errors during stage execution."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        self.traceback = traceback.format_exc() if original_error else None


class Stage(ABC):
    """Abstract base class for all processing stages in OpticTriage."""

    def __init__(self, session_id: int, db_manager: Any):
        self.session_id = session_id
        self.db_manager = db_manager
        self.name = self.__class__.__name__

    @abstractmethod
    def run(self) -> Generator[Dict[str, Any], None, None]:
        """
        Executes the stage logic. 
        Must yield dictionaries indicating progress.
        Format: {"status": str, "progress": float, "message": str}
        """
        pass

    def validate(self) -> bool:
        """Validates prerequisites before running the stage."""
        return True
