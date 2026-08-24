from enum import Enum

class PolicyDecision(str, Enum):
    """
    The deterministic output of a policy evaluation.
    
    ALLOW: The action is permitted to proceed autonomously.
    HUMAN_APPROVAL_REQUIRED: The action is not strictly forbidden, but requires human merchant approval.
    DENY: The action violates a hard constraint (e.g. price floor) and is forbidden.
    """
    ALLOW = "allow"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    DENY = "deny"

class ActionType(str, Enum):
    """
    Controlled actions that an agent can request to perform.
    """
    CREATE_AGREEMENT = "create_agreement"
