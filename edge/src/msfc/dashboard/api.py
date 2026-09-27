"""The Dashboard Adapter/API (section 1's diagram): a FastAPI app exposing exactly the
information/control surface the web UI needs, reading from one :class:`~msfc.dashboard.session.DemoSession`.

Route handlers never compute a verdict, an OEE number, or a health state themselves -- every
one of them calls a builder from :mod:`msfc.dashboard.dtos`, which only reshapes data already
produced by :mod:`msfc.services`/:mod:`msfc.analytics`/:mod:`msfc.sim` (section 2: "DO NOT
create a second implementation of these systems inside the UI").

Control routes (section 12, security/safety boundary): each one calls exactly one
:class:`~msfc.dashboard.session.DemoSession` method -- never an arbitrary Python function, never
a shell command, never a direct GPIO/hardware call (none exists). A malformed control request
(unknown action, bad body) is rejected with 4xx before it reaches the session.
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from msfc.dashboard import dtos
from msfc.dashboard.session import DemoSession

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_DEFAULT_CONTRACTS_ROOT = Path(__file__).resolve().parents[4] / "contracts"
_BACKGROUND_INTERVAL_S = 0.2
_VALID_PRODUCTION_FILTERS = {"all", "good", "defect", "uncertain", "rejected", "passed"}


def _session_name(session: DemoSession) -> str | None:
    return session.machine_monitor.session.config.name if session.machine_monitor else None


def _oee_status(session: DemoSession) -> dtos.OeeStatusDTO:
    status = session.machine_monitor.status(now_mono_ms=session.mono_ms) if session.machine_monitor else None
    return dtos.oee_status_from_machine_status(status)


def _health_status(session: DemoSession) -> dtos.HealthStatusDTO:
    snap = session.health_monitor.snapshot(mono_ms=session.mono_ms) if session.health_monitor else None
    return dtos.health_status_from_snapshot(snap)


def _overview(session: DemoSession) -> dtos.OverviewDTO:
    snap = session.runtime.snapshot(mono_ms=session.mono_ms)
    history = session.runtime.product_history()
    events = session.runtime.event_log(limit=20)
    return dtos.OverviewDTO(
        system=dtos.system_status_from_snapshot(snap, contract_version=session.registry.contract_version),
        production=dtos.production_summary_from_history(history, session_name=_session_name(session)),
        pipeline=dtos.vision_ocr_pipeline_from_trace(snap.last_product),
        safety=dtos.safety_status_from_snapshot(snap),
        health=_health_status(session),
        oee=_oee_status(session),
        latest_events=[dtos.event_dto_from_event(e) for e in reversed(events)],
    )


def _control_response(session: DemoSession, message: str) -> dtos.ControlResponseDTO:
    snap = session.runtime.snapshot(mono_ms=session.mono_ms)
    return dtos.ControlResponseDTO(ok=True, message=message, runtime_state=snap.runtime_state.value,
                                    machine_state=snap.machine_state.value if snap.machine_state else None)


def create_app(*, contracts_root: Path | None = None) -> FastAPI:
    """Builds one FastAPI app around one fresh :class:`DemoSession`. Each call is independent
    (used by tests to get an isolated session per test)."""
    session = DemoSession(contracts_root=contracts_root or _DEFAULT_CONTRACTS_ROOT)
    ws_clients: set[WebSocket] = set()

    async def _background_loop() -> None:
        while True:
            await asyncio.sleep(_BACKGROUND_INTERVAL_S)
            session.background_tick()
            if not ws_clients:
                continue
            payload = _overview(session).model_dump()
            dead = []
            for ws in ws_clients:
                try:
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_json(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                ws_clients.discard(ws)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(_background_loop())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="S1 Mini Smart Factory Cell -- Official Dashboard", version="1.0.0", lifespan=lifespan)
    app.state.session = session

    # ------------------------------------------------------------------ read endpoints (section 4)
    @app.get("/api/overview", response_model=dtos.OverviewDTO, tags=["overview"])
    async def get_overview() -> dtos.OverviewDTO:
        return _overview(session)

    @app.get("/api/production", response_model=dtos.ProductionSummaryDTO, tags=["production"])
    async def get_production(filter: str = "all") -> dtos.ProductionSummaryDTO:
        if filter.lower() not in _VALID_PRODUCTION_FILTERS:
            raise HTTPException(status_code=400, detail=(
                f"unknown filter {filter!r}; must be one of {sorted(_VALID_PRODUCTION_FILTERS)}"
            ))
        return dtos.production_summary_from_history(session.runtime.product_history(),
                                                      session_name=_session_name(session), filter_=filter.lower())

    @app.get("/api/vision-ocr", response_model=dtos.VisionOcrPipelineDTO, tags=["vision-ocr"])
    async def get_vision_ocr() -> dtos.VisionOcrPipelineDTO:
        snap = session.runtime.snapshot(mono_ms=session.mono_ms)
        return dtos.vision_ocr_pipeline_from_trace(snap.last_product)

    @app.get("/api/safety", response_model=dtos.SafetyStatusDTO, tags=["safety"])
    async def get_safety() -> dtos.SafetyStatusDTO:
        return dtos.safety_status_from_snapshot(session.runtime.snapshot(mono_ms=session.mono_ms))

    @app.get("/api/health", response_model=dtos.HealthStatusDTO, tags=["health"])
    async def get_health() -> dtos.HealthStatusDTO:
        return _health_status(session)

    @app.get("/api/oee", response_model=dtos.OeeStatusDTO, tags=["oee"])
    async def get_oee() -> dtos.OeeStatusDTO:
        return _oee_status(session)

    @app.get("/api/events", response_model=list[dtos.EventDTO], tags=["events"])
    async def get_events(limit: int = 100) -> list[dtos.EventDTO]:
        return [dtos.event_dto_from_event(e) for e in reversed(session.runtime.event_log(limit=limit))]

    @app.get("/api/diagnostics", response_model=dtos.DiagnosticsDTO, tags=["diagnostics"])
    async def get_diagnostics() -> dtos.DiagnosticsDTO:
        snap = session.runtime.snapshot(mono_ms=session.mono_ms)
        return dtos.diagnostics_from_snapshot(snap, contract_version=session.registry.contract_version)

    # ------------------------------------------------------------------ operator controls (section 5)
    @app.post("/api/control/start", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_start() -> dtos.ControlResponseDTO:
        session.send_start()
        return _control_response(session, "START sent to Cell Controller")

    @app.post("/api/control/stop", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_stop() -> dtos.ControlResponseDTO:
        session.send_stop()
        return _control_response(session, "STOP sent to Cell Controller")

    @app.post("/api/control/reset", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_reset() -> dtos.ControlResponseDTO:
        session.send_reset()
        return _control_response(session, "RESET sent to Cell Controller")

    @app.post("/api/control/simulate/good", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_good() -> dtos.ControlResponseDTO:
        product_id = session.simulate_good()
        return _control_response(session, f"simulated GOOD product ({product_id})")

    @app.post("/api/control/simulate/defect", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_defect() -> dtos.ControlResponseDTO:
        product_id = session.simulate_defect()
        return _control_response(session, f"simulated DEFECT product ({product_id})")

    @app.post("/api/control/simulate/uncertain", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_uncertain() -> dtos.ControlResponseDTO:
        product_id = session.simulate_uncertain()
        return _control_response(session, f"simulated UNCERTAIN vision result ({product_id})")

    @app.post("/api/control/simulate/ocr-failure", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_ocr_failure() -> dtos.ControlResponseDTO:
        product_id = session.simulate_ocr_failure()
        return _control_response(session, f"simulated OCR channel unavailable ({product_id})")

    @app.post("/api/control/simulate/health-warning", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_health_warning() -> dtos.ControlResponseDTO:
        session.simulate_health_warning()
        return _control_response(session, "simulated machine-health WARNING")

    @app.post("/api/control/simulate/health-critical", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_health_critical() -> dtos.ControlResponseDTO:
        session.simulate_health_critical()
        return _control_response(session, "simulated machine-health CRITICAL")

    @app.post("/api/control/simulate/health-recovery", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_health_recovery() -> dtos.ControlResponseDTO:
        session.simulate_health_recovery()
        return _control_response(session, "simulated machine-health recovery")

    @app.post("/api/control/simulate/safety-stop", response_model=dtos.ControlResponseDTO, tags=["control"])
    async def control_simulate_safety_stop() -> dtos.ControlResponseDTO:
        session.simulate_safety_stop()
        return _control_response(session, "simulated E-STOP press")

    @app.post("/api/control/demo/full", response_model=dtos.FullDemoSummaryDTO, tags=["control"])
    async def control_full_demo() -> dtos.FullDemoSummaryDTO:
        """Scoped strictly to what happened DURING this call (section 6's "demonstration
        summary" is the demo's own results, not whatever the operator did earlier in the
        session) -- captured by snapshotting history/event-log lengths before running it."""
        products_before = len(session.runtime.product_history())
        events_before = len(session.runtime.event_log())
        session.run_full_demo()
        history = list(session.runtime.product_history())[products_before:]
        events = list(session.runtime.event_log())[events_before:]
        snap = session.runtime.snapshot(mono_ms=session.mono_ms)
        return dtos.full_demo_summary(
            history=history, oee_status=_oee_status(session),
            health_state=_health_status(session).health_state, events=events,
            final_machine_state=snap.machine_state.value if snap.machine_state else None,
            final_runtime_state=snap.runtime_state.value,
        )

    # ------------------------------------------------------------------ error handling (section 11)
    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(_, exc: Exception):  # pragma: no cover - defensive
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"ok": False, "error": "SYSTEM OFFLINE", "detail": str(exc)})

    # ------------------------------------------------------------------ live updates
    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket) -> None:
        await websocket.accept()
        ws_clients.add(websocket)
        try:
            await websocket.send_json(_overview(session).model_dump())
            while True:
                await websocket.receive_text()  # the client never needs to send anything meaningful
        except WebSocketDisconnect:
            pass
        finally:
            ws_clients.discard(websocket)

    if _STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app


__all__ = ["create_app"]
