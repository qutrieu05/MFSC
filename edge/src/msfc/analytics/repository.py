"""OEE persistence abstraction (P4.17) — interface + in-memory implementation only, no
production database (P4.17: "do NOT introduce a production database unless clearly required").

D-050 (DECISIONS.md): this lives inside msfc.analytics rather than the separately pre-declared
msfc.storage package (ARCHITECTURE.md L7, also {"core","domain"}-only) because
edge/tests/unit/test_layer_dependencies.py does not permit "analytics" to import "storage" --
adding that permission would be a layer-rule change beyond this round's scope. A future
SQLite/other-backed OeeRepository belongs in msfc.storage, wired to msfc.analytics by
msfc.services (which is allowed to depend on both), not by analytics importing storage
directly.
"""

from __future__ import annotations

from typing import Protocol

from msfc.analytics.models import OeeResult


class OeeSnapshotRepository(Protocol):
    """Persists periodic OEE snapshots for one session, keyed by (session_name, mono_ms)."""

    def save(self, session_name: str, mono_ms: int, result: OeeResult) -> None: ...
    def latest(self, session_name: str) -> tuple[int, OeeResult] | None: ...
    def history(self, session_name: str) -> tuple[tuple[int, OeeResult], ...]: ...


class InMemoryOeeSnapshotRepository:
    """The only implementation this phase ships — process-lifetime only, matches
    "the software-first phase must remain lightweight" (P4.17)."""

    def __init__(self) -> None:
        self._by_session: dict[str, list[tuple[int, OeeResult]]] = {}

    def save(self, session_name: str, mono_ms: int, result: OeeResult) -> None:
        self._by_session.setdefault(session_name, []).append((mono_ms, result))

    def latest(self, session_name: str) -> tuple[int, OeeResult] | None:
        entries = self._by_session.get(session_name)
        return entries[-1] if entries else None

    def history(self, session_name: str) -> tuple[tuple[int, OeeResult], ...]:
        return tuple(self._by_session.get(session_name, ()))
