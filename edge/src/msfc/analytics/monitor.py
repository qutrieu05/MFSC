"""Machine monitoring layer (P4.11).

    Mock Machine Events -> MachineMonitor -> OEE Engine -> OEE Result   (today, P4.13's simulator)
    Real ESP32/PLC/Sensors -> same MachineEvent interface -> MachineMonitor -> ...   (later)

MachineMonitor is a thin wrapper around one ProductionSession — it exists as its own class
(rather than exposing ProductionSession directly) so the "current session" can be swapped
(P4.9: multiple sessions) without callers holding a stale reference, and so nothing outside
this module needs to know ProductionSession's internals.

P4.12 (safety authority): this module is READ-ONLY with respect to the rest of the system --
it consumes MachineEvent objects a caller hands it and produces MachineStatus/OeeResult
snapshots. It has no method that commands anything, and per the layer dependency rules
(edge/tests/unit/test_layer_dependencies.py: "analytics": {"core", "domain"}) it cannot even
import msfc.sim, msfc.decision, or the firmware -- it is architecturally incapable of
disabling safety, bypassing interlocks, or clearing an E-STOP, not merely disciplined not to.
"""

from __future__ import annotations

from msfc.domain import MachineState
from msfc.analytics.events import MachineEvent
from msfc.analytics.models import CycleStatistics, MachineStatus, OeeResult
from msfc.analytics.session import ProductionSession, SessionConfig


class MachineMonitor:
    def __init__(self, session: ProductionSession) -> None:
        self._session = session

    @property
    def session(self) -> ProductionSession:
        return self._session

    def start_new_session(self, config: SessionConfig, *, started_at_mono_ms: int,
                           initial_state: MachineState | None = None) -> None:
        """P4.9: multiple production sessions -- swap in a fresh one without losing the
        ability to have reported on the previous one right before this call."""
        self._session = ProductionSession(
            config, started_at_mono_ms=started_at_mono_ms,
            initial_state=initial_state if initial_state is not None else self._session.state,
        )

    def apply(self, event: MachineEvent) -> None:
        self._session.record_event(event)

    def apply_many(self, events: tuple[MachineEvent, ...]) -> None:
        for event in events:
            self.apply(event)

    def status(self, *, now_mono_ms: int) -> MachineStatus:
        return self._session.status(now_mono_ms=now_mono_ms)

    def oee_snapshot(self, *, now_mono_ms: int) -> OeeResult:
        return self._session.calculate_oee(now_mono_ms=now_mono_ms)

    def cycle_statistics(self) -> CycleStatistics:
        return self._session.cycle_statistics()
