"""Cell Controller simulator (P1.6): speaks the real MQTT contract with no hardware.

Depends on ``core``, ``domain``, ``contracts`` and ``comm`` (ARCHITECTURE.md section 7.2) —
unlike ``vision``/``decision``, this package *is* allowed to know MQTT exists, because its
whole purpose is to stand in for a device that talks MQTT.
"""

from __future__ import annotations

from msfc.sim.engine import SimCellController

__all__ = ["SimCellController"]
