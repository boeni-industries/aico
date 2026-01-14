"""
AMS Consolidation Data Models

Dataclasses for AMS consolidation state.
"""

from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime


@dataclass
class AMSConsolidationState:
    """AMS consolidation state model - matches ams_consolidation_state table."""
    id: str
    state_json: Dict[str, Any]
    updated_at: datetime
