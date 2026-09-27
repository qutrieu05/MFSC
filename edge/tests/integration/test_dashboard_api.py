"""Dashboard/backend integration tests (section 13's 20-item checklist), against the REAL
FastAPI app + REAL DemoSession (real SimCellController/CellRuntime/InMemoryBus) via Starlette's
TestClient -- no mocking of the backend.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from msfc.dashboard.api import create_app


@pytest.fixture()
def client(repo_root: Path) -> TestClient:
    app = create_app(contracts_root=repo_root / "contracts")
    with TestClient(app) as c:
        yield c


# 1. dashboard starts
def test_01_dashboard_starts(client: TestClient) -> None:
    assert client.get("/api/overview").status_code == 200


# 2. backend adapter starts (session boots to a real, known state)
def test_02_backend_adapter_starts_with_a_real_session(client: TestClient) -> None:
    data = client.get("/api/overview").json()
    assert data["system"]["mode"] == "SIMULATION"
    assert data["system"]["machine_state"] == "IDLE"


# 3. overview data loads
def test_03_overview_data_loads(client: TestClient) -> None:
    data = client.get("/api/overview").json()
    assert set(data.keys()) == {"system", "production", "pipeline", "safety", "health", "oee", "latest_events"}


# 4. production data loads
def test_04_production_data_loads(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/good")
    data = client.get("/api/production").json()
    assert data["total"] == 1
    assert data["good"] == 1


# 5. Vision data loads
def test_05_vision_data_loads(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/good")
    data = client.get("/api/vision-ocr").json()
    vision = next(s for s in data["stages"] if s["stage"] == "vision")
    assert vision["available"] is True
    assert vision["verdict"] == "GOOD"


# 6. OCR data loads
def test_06_ocr_data_loads(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/good")
    data = client.get("/api/vision-ocr").json()
    ocr = next(s for s in data["stages"] if s["stage"] == "ocr")
    assert ocr["available"] is True
    assert ocr["verdict"] == "GOOD"


# 7. Safety data loads
def test_07_safety_data_loads(client: TestClient) -> None:
    data = client.get("/api/safety").json()
    assert data["safety_level"] == "SAFE"
    assert data["machine_state"] == "IDLE"


# 8. Health data loads
def test_08_health_data_loads(client: TestClient) -> None:
    client.post("/api/control/simulate/health-warning")
    data = client.get("/api/health").json()
    assert data["configured"] is True
    assert data["health_state"] == "WARNING"


# 9. OEE data loads
def test_09_oee_data_loads(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/good")
    data = client.get("/api/oee").json()
    assert data["configured"] is True
    assert data["good_count"] == 1


# 10. event log loads
def test_10_event_log_loads(client: TestClient) -> None:
    client.post("/api/control/start")
    events = client.get("/api/events").json()
    assert len(events) > 0
    assert {"mono_ms", "category", "severity", "message"} <= events[0].keys()


# 11. controller state is represented correctly
def test_11_controller_state_represented_correctly(client: TestClient) -> None:
    client.post("/api/control/start")
    data = client.get("/api/overview").json()
    assert data["system"]["machine_state"] == "RUNNING"
    assert data["system"]["runtime_state"] == "RUNNING"


# 12. E-STOP is represented correctly
def test_12_estop_represented_correctly(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/safety-stop")
    data = client.get("/api/safety").json()
    assert data["safety_level"] == "ESTOP"
    diag = client.get("/api/diagnostics").json()
    assert "F001" in diag["active_fault_codes"]


# 13. UNKNOWN state is represented correctly
def test_13_unknown_state_represented_correctly(client: TestClient) -> None:
    # No sensor reading has been pushed yet in this fresh session -> health must read UNKNOWN,
    # never a fabricated HEALTHY (section 11's explicit rule).
    data = client.get("/api/health").json()
    assert data["health_state"] == "UNKNOWN"
    # No product processed yet -> pipeline stages are all unavailable, not fabricated GOOD.
    pipeline = client.get("/api/vision-ocr").json()
    assert all(not s["available"] for s in pipeline["stages"])


# 14. backend unavailable behavior
def test_14_backend_unavailable_returns_system_offline(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(contracts_root=repo_root / "contracts")
    session = app.state.session

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated backend outage")

    monkeypatch.setattr(session.runtime, "snapshot", _boom)
    # raise_server_exceptions=False: we are deliberately testing the registered 500 handler's
    # own response, not asking the test harness to re-raise for debugging (its default).
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/overview")
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "SYSTEM OFFLINE"


# 15. invalid control command
def test_15_invalid_control_command_is_rejected(client: TestClient) -> None:
    # Exact status (404 vs 405) is a routing implementation detail; what section 12 requires is
    # that it is REJECTED (a 4xx), never silently accepted/succeeding.
    assert client.post("/api/control/simulate/not-a-real-action").status_code in (404, 405)
    assert client.get("/api/production", params={"filter": "not-a-real-filter"}).status_code == 400


# 16. simulation mode
def test_16_simulation_mode_is_explicit(client: TestClient) -> None:
    assert client.get("/api/overview").json()["system"]["mode"] == "SIMULATION"
    assert client.get("/api/diagnostics").json()["mode"] == "SIMULATION"


# 17. full demo
def test_17_full_demo_runs_end_to_end(client: TestClient) -> None:
    summary = client.post("/api/control/demo/full").json()
    assert summary["products_processed"] >= 4
    assert summary["label"] == "SOFTWARE SIMULATION -- NO PHYSICAL HARDWARE"
    assert summary["final_runtime_state"] == "RUNNING"  # demo ends with production resumed


# 18. dashboard does not bypass P2
def test_18_dashboard_does_not_bypass_safety(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/safety-stop")
    result = client.post("/api/control/simulate/good").json()
    assert result["runtime_state"] == "SAFE_STOP"  # still latched -- the control did not clear it
    production = client.get("/api/production").json()
    assert production["history"][0]["outcome"] == "SAFETY_DENIED"


# 19. dashboard does not independently calculate authoritative OEE
def test_19_oee_matches_backend_exactly(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/good")
    api_oee = client.get("/api/oee").json()
    session = client.app.state.session
    backend_status = session.machine_monitor.status(now_mono_ms=session.mono_ms)
    assert api_oee["oee"] == backend_status.oee.oee
    assert api_oee["availability"] == backend_status.oee.availability


# 20. dashboard does not independently make product decisions
def test_20_decision_matches_backend_decision_engine_exactly(client: TestClient) -> None:
    client.post("/api/control/start")
    client.post("/api/control/simulate/defect")
    session = client.app.state.session
    backend_trace = session.runtime.product_history()[-1]
    api_pipeline = client.get("/api/vision-ocr").json()
    decision_stage = next(s for s in api_pipeline["stages"] if s["stage"] == "decision")
    assert decision_stage["verdict"] == backend_trace.decision.final_verdict.value


# ------------------------------------------------------------------ bonus: WebSocket + docs
def test_websocket_live_pushes_an_overview_payload(client: TestClient) -> None:
    with client.websocket_connect("/ws/live") as ws:
        payload = ws.receive_json()
        assert "system" in payload and "safety" in payload


def test_openapi_docs_are_generated(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/overview" in schema["paths"]
    assert "/api/control/start" in schema["paths"]
