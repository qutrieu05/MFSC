# Official Dashboard Architecture — MSFC

**Ngày:** 2026-09-19 · **Trạng thái:** SOFTWARE COMPLETE (software-only, no hardware) · Đi kèm: [OFFICIAL_DASHBOARD_USER_GUIDE.md](OFFICIAL_DASHBOARD_USER_GUIDE.md), [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md)

## 1. Purpose

The Official Web Dashboard is the user-facing interface for the S1 Mini Smart Factory Cell. It is **not** a demo prototype meant to be thrown away — it is the permanent presentation layer for the software platform P1–P6 already built, designed so that when real hardware eventually replaces the simulator, **no dashboard code changes**. Today it demonstrates the complete software flow (Vision → OCR → Decision → Safety → Controller → Production → OEE → Machine Health) entirely in simulation.

## 2. Architecture

```
                 OFFICIAL WEB DASHBOARD  (static/index.html, styles.css, app.js — plain JS, no build step)
                         │  fetch() / WebSocket
                         ▼
                 Dashboard Adapter/API   (msfc.dashboard.api — FastAPI app, REST + WebSocket)
                         │  reads/controls
                         ▼
                 DemoSession             (msfc.dashboard.session — owns ONE demo cell)
                         │
        ┌────────────────┼──────────────────────┬─────────────────────┐
        ▼                ▼                      ▼                     ▼
   CellRuntime      MachineMonitor      MachineHealthMonitor      SimCellController
 (msfc.services)     (msfc.analytics)      (msfc.analytics)         (msfc.sim)
        │                                                              │
        └──────────────────────── MessageBus (msfc.comm.InMemoryBus) ──┘
```

`msfc.dashboard` is Layer 8, pre-declared since Phase 0 (ARCHITECTURE.md §7.1, ADR-0012 — "technology choice deferred to Phase 4," now decided here). It composes the existing platform; it introduces **no new business logic** for vision, OCR, decision, safety, OEE, or health — every number the UI shows is read from `msfc.services`/`msfc.analytics`/`msfc.sim`, never recomputed.

### 2.1 Module boundary inside `msfc.dashboard`

| Module | Responsibility | Imports `msfc.sim`/`vision`/`ocr`/`decision`? |
|---|---|---|
| `dtos.py` | Pure view-model builders: internal dataclass → pydantic DTO. No I/O, no state. | No |
| `session.py` | `DemoSession` — owns the one `SimCellController`+`CellRuntime`+`InMemoryBus` demo cell; the only module allowed to construct engines/the simulator. | **Yes** — the one deliberate seam (see §6) |
| `api.py` | FastAPI app: REST routes call `dtos.*_from_*(session.*)`; control routes call exactly one `DemoSession` method each. | No |
| `static/*` | Plain HTML/CSS/JS frontend, served as static files by `api.py`. | N/A (browser-side) |
| `__main__.py`, `run_dashboard.py` | Process entry points (`uvicorn.run`). | No |

### 2.2 Layer dependency rule (enforced by `edge/tests/unit/test_layer_dependencies.py`)

`dashboard` is allowed to import: `core, domain, contracts, comm, storage` (declared since Phase 0) plus, added this phase: `services, analytics, sim, vision, ocr, decision`. See DECISIONS.md D-065 for why each addition was necessary (the dashboard cannot display `CellRuntime`/OEE/health data, or build a demonstration session, without them) and why this is not a "redesign" of P1–P6 (rule 7 of the PO's directive: an actual integration blocker was found and documented, not silently routed around).

`msfc.dashboard` still **cannot** import firmware or bypass `msfc.services`' own restriction on `msfc.sim` — only `session.py` touches the simulator; `api.py` and `dtos.py` never do.

## 3. Frontend/backend boundary

- **Frontend**: vanilla HTML/CSS/JS, no framework, no build step (`static/index.html`, `styles.css`, `app.js`). Chosen per section 3 of the directive ("avoid unnecessary infrastructure... avoid a large enterprise stack"): a student can open the page, read the JS directly, and understand it without npm/webpack/React.
- **Backend**: FastAPI + Uvicorn (new dependencies, D-064) — chosen for native async + WebSocket support and automatic OpenAPI documentation (`GET /openapi.json`, human-readable at `GET /docs`), avoiding a heavier framework.
- The frontend **never** computes a verdict, OEE figure, or health state; it only renders what the API returns.

## 4. Data flow

```
Operator clicks "SIMULATE DEFECT" (or a physical sensor, later)
   → POST /api/control/simulate/defect
   → DemoSession.simulate_defect(): sets the scripted vision engine's next score,
     then fires the REAL sim.detect_product() → CellRuntime pipeline → sim.arrive_at_s2()
   → CellRuntime computes InspectionResult(s) → DecisionRecord → VerdictCommand → publishes
     over the REAL InMemoryBus → SimCellController receives and sorts the product
   → CellRuntime records the outcome in its (additive, this-phase) product_history()/event_log()
   → GET /api/overview (or the WebSocket push) reads CellRuntime.snapshot()/product_history()/
     event_log(), MachineMonitor.status(), MachineHealthMonitor.snapshot()
   → dtos.py reshapes these into JSON view-models
   → app.js renders them
```

Every step above is real code executing — none of it is fabricated for display purposes.

## 5. API/data contract

See the auto-generated OpenAPI schema at `GET /openapi.json` (or `/docs` for the interactive Swagger UI) once the server is running — this is the authoritative, always-up-to-date contract. Summary:

| Method | Path | Returns | Notes |
|---|---|---|---|
| GET | `/api/overview` | `OverviewDTO` | Aggregate of all sections below |
| GET | `/api/production?filter=` | `ProductionSummaryDTO` | filter ∈ all/good/defect/uncertain/passed/rejected |
| GET | `/api/vision-ocr` | `VisionOcrPipelineDTO` | Latest product's 4 pipeline stages |
| GET | `/api/safety` | `SafetyStatusDTO` | |
| GET | `/api/health` | `HealthStatusDTO` | `configured=false` if no health monitor wired |
| GET | `/api/oee` | `OeeStatusDTO` | `configured=false` if no OEE monitor wired |
| GET | `/api/events?limit=` | `list[EventDTO]` | Most-recent-first |
| GET | `/api/diagnostics` | `DiagnosticsDTO` | |
| POST | `/api/control/{start,stop,reset}` | `ControlResponseDTO` | Operator commands |
| POST | `/api/control/simulate/{good,defect,uncertain,ocr-failure,health-warning,health-critical,health-recovery,safety-stop}` | `ControlResponseDTO` | Demonstration inputs (§5 of the PO directive) |
| POST | `/api/control/demo/full` | `FullDemoSummaryDTO` | The 14-step scripted demo (§6) |
| WS | `/ws/live` | `OverviewDTO` (JSON) pushed ~5×/s | Live updates while connected |

Errors: a malformed control action (unknown route/method) returns 404/405; an invalid query parameter (e.g. unknown `filter`) returns 400 with a `detail` message; any unhandled internal exception returns 503 `{"ok": false, "error": "SYSTEM OFFLINE", "detail": "..."}` — the UI never silently shows stale data as if it were current (§11).

## 6. Safety boundary (non-negotiable, unchanged from P2/P6)

The Cell Controller (`SimCellController` today, real firmware later) remains the **sole** safety authority. The dashboard:

- Never clears an E-stop, an interlock, or a fault by itself — `POST /api/control/reset` calls `sim.local_reset()`/`sim.release_estop()`, the exact same operator action a physical RESET button would trigger, subject to the exact same SAF-05 rules (a still-held simulated E-stop cannot be reset).
- Never forces a motor/servo/GPIO — none exist; the closest analogue, `POST /api/control/simulate/safety-stop`, calls `sim.press_estop()`, documented in `msfc.sim.engine` itself as "a physical input, modelled as a direct method call" — architecturally identical to a real button.
- Never independently decides GOOD/DEFECT — `DecisionEngine.decide()` (P1, unmodified) is the only place that happens; `test_20_decision_matches_backend_decision_engine_exactly` proves the API's reported decision is byte-for-byte the same object the backend produced.
- Never independently computes OEE — `test_19_oee_matches_backend_exactly` proves the same.
- Never shows a fabricated "HEALTHY"/"SAFE" when the backend hasn't reported one — `HealthStatusDTO.configured=False` / `SafetyStatusDTO.safety_level="UNKNOWN"` are the explicit "we don't know" states (`test_13_unknown_state_represented_correctly`).

## 7. Simulation mode vs. real hardware mode

Every response includes an explicit `mode: "SIMULATION"` field (`SystemStatusDTO`, `DiagnosticsDTO`) and the header UI carries a permanent `SOFTWARE SIMULATION · NO HARDWARE` badge. There is currently no code path that produces `mode: "REAL_HARDWARE"` — this is intentional (no hardware exists to validate it) and is the one flag a future hardware-integration phase would need to wire up, changing only `session.py` (§8).

## 8. Future hardware compatibility

Per the layer boundary in §2.1, only `msfc.dashboard.session` would need to change to move from simulation to real hardware:

- `SimCellController` → a real MQTT client (`msfc.comm.MqttBus`, already exists, untouched) talking to real firmware — `CellRuntime` itself already only depends on `MessageBus`, so this swap needs zero changes in `msfc.services` or `msfc.dashboard.api`/`dtos.py`.
- The scripted `_ScriptedVisionEngine`/`FixtureOcrEngine` → real `InferenceEngine`/`OcrEngine` implementations (already-existing interfaces, e.g. `ClassicCvBaseline`, a real OCR backend) — `VisionStageConfig`/`OcrStageConfig` accept any conforming implementation.
- `_ControllableSensor` → a real `SensorSource` reading actual hardware.

No route, DTO, or frontend file needs to change for any of the above.

## 9. Known limitations

See PHASE_DASHBOARD_COMPLETION_REPORT.md §11 for the full list; the headline ones:

- Single demo session, single process, in-memory only — no persistence, no multi-user support, no authentication (not requested, and inappropriate for a local student prototype exposing safety-adjacent controls to arbitrary network clients — bind to `127.0.0.1` only, as `run_dashboard.py`'s default does).
- No automated browser/JS test suite (Selenium/Playwright) — the frontend was manually verified in Claude's built-in browser tool (screenshots in the completion report); the backend/API is fully covered by automated tests via `TestClient`.
- Machine-health "recovery" demo requires the health window to age out (handled internally by advancing the demo clock — see D-067) — this is a demonstration convenience, not a claim about real sensor recovery timing.
