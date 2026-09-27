"""Decision Engine (Layer 4, IF-06). Depends only on ``msfc.core`` and ``msfc.domain``."""

from __future__ import annotations

from msfc.decision.engine import DecisionEngine
from msfc.decision.policy import DecisionPolicy

__all__ = ["DecisionEngine", "DecisionPolicy"]
