"""pipeline.py — Orchestrator for running stages sequentially.
exports: PipelineOrchestrator
used_by: app.py → MainWindow
rules:
Must handle state transitions and database updates cleanly.
"""

from typing import List, Type, Dict, Any, Generator
from optictriage.database import DatabaseManager
from optictriage.models import Session
from optictriage.stages.base import Stage, StageError

class PipelineOrchestrator:
    """Manages the execution of sequential pipeline stages."""

    def __init__(self, session_id: int, db_manager: DatabaseManager):
        self.session_id = session_id
        self.db_manager = db_manager
        self.stages: List[Stage] = []

    def add_stage(self, stage_class: Type[Stage]) -> None:
        """Instantiates and appends a stage to the pipeline."""
        self.stages.append(stage_class(self.session_id, self.db_manager))

    def run(self) -> Generator[Dict[str, Any], None, None]:
        """Executes all stages in sequence, yielding progress."""
        self._update_session_state("processing")
        
        try:
            for stage in self.stages:
                yield {"stage": stage.name, "status": "starting", "progress": 0.0, "message": f"Starting {stage.name}..."}
                
                if not stage.validate():
                    raise StageError(f"Validation failed for {stage.name}")
                    
                for progress_update in stage.run():
                    # Decorate the stage's progress with orchestrator context
                    update = {"stage": stage.name, **progress_update}
                    yield update
                    
            self._update_session_state("complete")
            yield {"stage": "Pipeline", "status": "complete", "progress": 100.0, "message": "All stages completed successfully."}
            
        except Exception as e:
            self._update_session_state("error")
            yield {"stage": "Pipeline", "status": "error", "progress": 0.0, "message": str(e)}
            raise

    def _update_session_state(self, state: str) -> None:
        """Updates the session's high-level state in the database."""
        with self.db_manager.get_session() as db_session:
            session_obj = db_session.query(Session).get(self.session_id)
            if session_obj:
                session_obj.state = state
