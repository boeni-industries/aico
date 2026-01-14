"""
Ethics Policy Data Models

Dataclasses for ethics policy rule entities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class EthicsPolicyRule:
    """Ethics policy rule model - matches ethics_policy_rules table."""
    rule_id: str
    rule_name: str
    target_type: str
    conditions_json: Dict[str, Any]
    effect: str
    priority: int = 100
    enabled: bool = True
    scope: str = 'global'
    user_message_template: Optional[str] = None
    scope_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
