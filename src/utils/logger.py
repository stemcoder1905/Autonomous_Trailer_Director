"""Observability and Decision Logger for Autonomous Trailer Director."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.models.schemas import DecisionLogEntry

logger = logging.getLogger("autonomous_trailer_director")


class DecisionLogger:
    """Records audit logs and structured decision traces across all agents."""
    
    def __init__(self, log_path: Optional[Path] = None):
        self.entries: List[DecisionLogEntry] = []
        self.log_path = log_path
        self._setup_python_logging()

    def _setup_python_logging(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        if not logger.handlers:
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    def log_decision(
        self,
        agent: str,
        action: str,
        reason: str,
        input_evidence: Optional[List[str]] = None,
        selected_decision: Optional[Dict[str, Any]] = None,
        rejected_decisions: Optional[List[Dict[str, Any]]] = None,
        validation_results: Optional[List[Dict[str, Any]]] = None,
        risk: str = "LOW",
        cost: float = 0.0,
        affected_segments: Optional[List[str]] = None,
        revision: int = 1,
        model_provider: str = "mock"
    ) -> DecisionLogEntry:
        """Create and store a structured decision log entry."""
        log_id = f"log_{len(self.entries) + 1:04d}"
        now_iso = datetime.now(timezone.utc).isoformat()
        
        entry = DecisionLogEntry(
            log_id=log_id,
            timestamp=now_iso,
            agent=agent,
            action=action,
            input_evidence=input_evidence or [],
            selected_decision=selected_decision or {},
            rejected_decisions=rejected_decisions or [],
            validation_results=validation_results or [],
            risk=risk,
            cost=cost,
            affected_segments=affected_segments or [],
            revision=revision,
            reason=reason,
            model_provider=model_provider
        )
        self.entries.append(entry)
        
        logger.info(
            f"[{agent}] Action: {action} | Reason: {reason} | Risk: {risk} | "
            f"Affected: {affected_segments or []}"
        )
        if self.log_path:
            self.persist()
        return entry

    def persist(self, path: Optional[Path] = None):
        """Save all log entries to a JSON file."""
        target = path or self.log_path
        if not target:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in self.entries], f, indent=2)

    def get_entries_by_agent(self, agent_name: str) -> List[DecisionLogEntry]:
        return [e for e in self.entries if e.agent == agent_name]

    def get_rejected_events(self) -> List[DecisionLogEntry]:
        return [e for e in self.entries if len(e.rejected_decisions) > 0 or "reject" in e.action.lower()]
