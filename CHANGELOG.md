# Changelog

Định dạng theo [Keep a Changelog](https://keepachangelog.com/vi/1.1.0/); phiên bản theo [SemVer](https://semver.org/lang/vi/).

## [Unreleased]

### Added — Official Web Dashboard (2026-09-19)

PO directive "S1 — OFFICIAL WEB DASHBOARD", after Phase 6's close. Build the permanent
user-facing interface for the S1 software platform — **explicitly not Phase 7** (the PO's own
rule 23: "Do NOT create Phase 7 or invent a new project phase beyond this dashboard phase").
Software-only: no hardware, no MQTT broker, no ESP-IDF; entirely backed by the existing
simulation infrastructure.

**Mandatory skill discovery (performed first, per the PO's directive):** searched the entire
repository for a `skills/` directory or any `SKILL.md` file. **None exists.** `.claude/company/`
contains only internal role-play management metadata (`project.json`), not a skill. Conclusion:
no pre-existing frontend/UI/dashboard skill was available to use; the dashboard was designed
directly against the PO's own information-architecture spec and general industrial-HMI
conventions (dark theme, high-contrast state pills, no reliance on color alone).

**New package `edge/src/msfc/dashboard/`** (Layer 8, pre-declared since Phase 0, ADR-0012 —
technology choice deferred to "Phase 4+", decided here):
- `dtos.py` — pure view-model builders (pydantic models) from existing P1-P6 objects
  (`CellSnapshot`, `MachineStatus`, `MachineHealthSnapshot`, `ProductCycleTrace`) to JSON. No
  verdict, OEE figure, or health state is computed here — every builder only reshapes a value
  already produced by `msfc.services`/`msfc.analytics`/`msfc.sim`.
- `session.py` — `DemoSession`: owns the one demonstration cell (a real `SimCellController` +
  real `CellRuntime` + real `InMemoryBus`, plus scripted vision/OCR engines and a controllable
  sensor). Exposes operator controls (start/stop/reset) and demonstration controls (simulate
  good/defect/uncertain/OCR-failure/health-warning/health-critical/health-recovery/safety-stop,
  plus a scripted 14-step full-demo sequence) — every one of them drives the real architecture
  (a real `ControlCommand`, a real `sim.press_estop()`, a real product cycle through
  `CellRuntime`), never a shortcut into internal state.
- `api.py` — FastAPI app: REST endpoints for overview/production/vision-ocr/safety/health/oee/
  events/diagnostics, control endpoints for every demo action, a `/ws/live` WebSocket pushing
  live snapshots, a global exception handler returning `503 SYSTEM OFFLINE` (never a stale value
  presented as current), auto-generated OpenAPI docs at `/docs`.
- `static/{index.html,styles.css,app.js}` — plain HTML/CSS/vanilla JS frontend, no framework, no
  build step; 8 tabs (Overview, Production, Vision & OCR, Safety, Machine Health, OEE, Event
  Log, Diagnostics) plus a persistent control dock and a full-demo summary modal.
- `__main__.py` / `edge/run_dashboard.py` — process entry points (`python edge/run_dashboard.py`
  or `cd edge && python -m msfc.dashboard`), binding to `127.0.0.1` by default.

**Layer rule extended (D-065):** `ALLOWED["dashboard"]` (previously `core, domain, contracts,
comm, storage`) now also permits `services, analytics, sim, vision, ocr, decision` — the
dashboard cannot display `CellRuntime`/OEE/health data or build a demonstration session without
them, and the PO's own directive names `SimCellController` as reuse infrastructure for the demo
mode. Confined to `session.py`; `api.py`/`dtos.py` never import `sim`/`vision`/`ocr`/`decision`
directly.

**Additive extension to `msfc.services.CellRuntime` (D-066, no existing behavior changed):**
`product_history()` and `event_log()` (bounded, most-recent-last, matching `DedupeFilter`'s
existing LRU-eviction style) plus `ocr`/`vision` properties allowing a caller to swap the stage
configuration between cycles (needed by the "SIMULATE OCR FAILURE" control). All 43 pre-existing
Phase 6 tests pass unmodified.

**New dependency (D-064, the first since Phase 0):** `fastapi`, `uvicorn` (runtime), `httpx`
(dev/test, required by `starlette.testclient`) — declared in `edge/pyproject.toml`.

**Two real bugs caught and fixed before finalizing (D-067, same discipline as
D-039/D-044/D-049/D-055/D-056/D-058/D-061):**
1. `DemoSession._advance()` originally allowed a single large simulated-time jump (e.g. to age a
   machine-health reading out of its window), which tripped a spurious COMM_LOSS fault because
   the Cell Controller checks heartbeat staleness at the instant of `tick()`, before this
   method's own refresh could run. Fixed by chunking any advance into safe steps (≤200 ms), each
   immediately followed by a heartbeat refresh.
2. A test's initial assumption that "SIMULATE HEALTH RECOVERY" would show `HEALTHY` immediately
   was wrong — P5's window-based anomaly detection (D-055) correctly keeps reporting the last
   anomalous reading until it ages out of the window. Fixed the *demo control*, not `msfc.
   analytics`: `simulate_health_recovery()` now explicitly advances the clock past the window
   before pushing a healthy reading.

**Test:** 4 new test files, **51 new tests** (7 `test_services_runtime_observability.py` +
11 `test_dashboard_dtos.py` + 11 `test_dashboard_session.py` + 22
`tests/integration/test_dashboard_api.py`, covering all 20 items the PO's directive required
plus WebSocket and OpenAPI checks). Full regression: **859 passed, 1 skipped** (up from 808+1 —
net +51, zero broken). Firmware C untouched, re-confirmed 262/262.

**Visual verification:** the dashboard was actually run (`preview_start` + Claude's built-in
browser) and driven end-to-end — START, SIMULATE GOOD/DEFECT, all 8 tabs, E-STOP (proving the
next product is denied without vision/OCR/decision ever running), RESET+START recovery, and RUN
FULL DEMO (14-step scripted sequence, summary modal) — with zero browser console errors.

**Deferred / out of scope:** no authentication, no multi-user support, no persistent storage
beyond the running process, no automated browser/JS test suite (manual verification via Claude's
browser tool instead), no cloud deployment.

See [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md),
[OFFICIAL_DASHBOARD_ARCHITECTURE.md](OFFICIAL_DASHBOARD_ARCHITECTURE.md), and
[OFFICIAL_DASHBOARD_USER_GUIDE.md](OFFICIAL_DASHBOARD_USER_GUIDE.md) for full detail.

### Added — Phase 6: Edge AI Platform / Final Software Integration (2026-09-19)

PO directive "PHASE 6 — EDGE AI PLATFORM & FINAL SOFTWARE INTEGRATION", after approving Phase 5's
close. Unify the existing P1-P5 subsystems (vision, OCR, decision, safety, machine health, OEE)
into one hardware-independent orchestration/runtime platform — the **final software phase** of
the roadmap, subject to the validation-status limitations below. Software-only: no hardware, no
Mosquitto/ESP-IDF install, no new safety authority, no Phase 7 work.

**Architecture-first finding, before any code:** `msfc.services` (Layer 6) was already declared
in ARCHITECTURE.md section 7.1/7.2 and in `edge/tests/unit/test_layer_dependencies.py`'s
`ALLOWED` dict since Phase 0, deferred until now. Several P1-P5 modules already say so explicitly
in their own docstrings (`msfc.vision.frame.FrameSource`, `msfc.ocr.pipeline`,
`msfc.analytics.health_p4_bridge`, DECISIONS.md Q-17). Phase 6 builds exactly that pre-declared
package rather than inventing a new one, and does not touch the layer-dependency rule.

**New package `edge/src/msfc/services/`** (9 modules):
- `platform_model.py` — P6.1: `CellIdentity` (`cell_id`, `cell_device_id`, `edge_device_id`,
  `line_id`), `RuntimeState` (INIT/READY/RUNNING/DEGRADED/FAULT/SAFE_STOP/SHUTDOWN — a genuinely
  new concept, distinct from and never overriding `MachineState`), `PipelineOutcome`
  (GOOD/DEFECT/SAFETY_DENIED/NO_DECISION), `ProductCycleTrace`, `SubsystemHealth`, `CellSnapshot`.
  Reuses every existing P1-P5 type it can (`MachineState`, `InspectionResult`, `DecisionRecord`,
  `MachineHealthSnapshot`, `MachineStatus`) rather than duplicating them; `product_id` is reused
  as the one correlation id end-to-end.
- `codec.py` — P6.6: decode functions (envelope `data` → domain object) for every Cell Controller
  message `msfc.services` consumes — the mirror image of `msfc.sim.codec`'s encoders, which
  `msfc.services` cannot import (layer rule). Also encodes `VerdictCommand`/`ControlCommand`/the
  Edge Server's own `edge_heartbeat.v1` for publishing.
- `timing.py` — P6.12: `StageTimer`/`PipelineTiming`/`TimingStats`, a HOST/SIMULATION-ONLY timing
  model, explicitly documented as unrelated to firmware's own `timing_stats.v1` contract and not
  wired to any MQTT topic.
- `vision_pipeline.py` — P6.2: composes `Frame → preprocess → InferenceEngine.predict →
  postprocess` into one `InspectionResult`-producing function, living here (not inside
  `msfc.vision`, unlike OCR's own `pipeline.py`) because the PO's directive forbade modifying
  `msfc.vision` (D-063).
- `safety_gate.py` — P6.4: `evaluate_safety_gate()`, an explicitly-documented courtesy/
  defense-in-depth check, never the safety authority — the Cell Controller remains the sole
  enforcer regardless of this module's answer. Fail-closed on an unknown cell state.
- `pipeline.py` — P6.2/P6.5: `run_product_cycle()` — pure, bus-free per-product orchestration:
  safety gate → vision (fail-closed on failure/absence) → OCR (already fail-closed, unchanged) →
  `DecisionEngine.decide()` on whatever channels are present → `NO_DECISION` (no verdict
  published) if none are. Precedence is built entirely from decisions that already exist
  elsewhere (ADR-0005's "no verdict = reject", `DecisionPolicy.uncertain_verdict`'s default
  DEFECT) — no new precedence hierarchy invented.
- `health_pipeline.py` — P6.2/P6.11: `ingest_sensors()`/`bridge_critical_events()` — thin
  composition over P5's `MachineHealthMonitor` and the existing opt-in
  `bridge_critical_health_to_machine_event`; a failing sensor is skipped, never faked as OK.
- `runtime.py` — P6.3: `CellRuntime` — the top-level lifecycle. Subscribes to
  `conveyor.state`/`fault`/`event.product_detected`/`event.product_sorted`/`event.state_changed`/
  `ack` (each wrapped in the existing `DedupeFilter`), runs the per-product pipeline, publishes
  verdicts and its own `system.heartbeat` (`services_ok` reflects the runtime's own health, not
  the cell's). Never imports `msfc.sim`; talks to the Cell Controller purely through
  `MessageBus`+`ContractRegistry`, verified end-to-end against the real, unmodified
  `SimCellController` over a real `InMemoryBus`. Never calls `bus.start()`/`bus.stop()` (shared
  bus discipline). Computes `RuntimeState` from what it has actually observed — INIT until the
  first `conveyor.state` arrives, SAFE_STOP whenever the cell is latched, DEGRADED/FAULT from its
  own subsystem-failure bookkeeping (never from the cell's state).

**Modified:** `edge/src/msfc/core/errors.py` (added `OrchestrationError`, following the existing
pattern). No P1-P5 source files or firmware C files touched.

**Two real bugs caught and fixed before finalizing (same discipline as D-039/D-044/D-049/D-055/
D-056):**
1. `CellIdentity` originally had one `device_id` shared between the Cell Controller's own topics
   (`conveyor/*`) and the Edge Server's own heartbeat topic (`system/*`) — two different devices
   per MQTT_CONTRACT.md. Caught while wiring `send_heartbeat()`; fixed by splitting into
   `cell_device_id`/`edge_device_id` (D-058).
2. The first draft of scenarios 12/13 called `MachineHealthMonitor.ingest()` directly and
   expected `CellRuntime.process_sensors()` to notice — wrong assumption, since
   `process_sensors()` only reads through configured `SensorSource` objects. Fixed the TEST
   DESIGN (not production code) to use `FixedSequenceSensorSource`/a failing sensor stub through
   the real public entry point (D-061).

**Contract conflicts explicitly preserved, not resolved (per the PO's "resolve with
justification OR document as unresolved" rule):** D-051/Q-19 (health schema state/sensor-type
conflict) and D-048/Q-18 (OEE metrics clamping) remain open. `msfc.services` does not publish
`oee.state.metrics`/`health.state`/`health.telemetry.features` over MQTT this round — those
topics are still `status="draft"` in `contracts/mqtt/topics.toml` — and observes OEE/health via
direct in-process calls only (D-060).

**Test:** 9 new unit test files + 2 new integration test files, **96 new tests** (74 unit:
`test_services_platform_model.py` 11, `test_services_codec.py` 11, `test_services_timing.py` 5,
`test_services_vision_pipeline.py` 5, `test_services_safety_gate.py` 7,
`test_services_health_pipeline.py` 5, `test_services_pipeline.py` 11, `test_services_runtime.py`
8, `test_services_fixtures.py` 11 [26 reusable fixtures]; 22 integration:
`tests/integration/test_services_scenarios.py` 20 named deterministic scenarios,
`tests/integration/test_services_full_stack_integration.py` 2 [success path + failure path]).
Full regression: **808 passed, 1 skipped** (up from 712+1 — net +96, zero broken). Firmware C
untouched, re-confirmed 262/262.

**Deferred / out of scope, matching the D-040/D-048/D-050/D-060 pattern:** MQTT publishing of
OEE/health data; a persistent storage backend (still in-memory, unchanged from P4/P5); real
Edge device deployment; a dashboard (explicitly prohibited as new scope this round).

See [PHASE6_COMPLETION_REPORT.md](PHASE6_COMPLETION_REPORT.md) for the full gate report.

### Added — Phase 5: Software-only Machine Health / Anomaly Detection / Predictive Maintenance (2026-09-18)

PO directive "START PHASE 5 — SOFTWARE-ONLY MACHINE HEALTH / ANOMALY DETECTION / PREDICTIVE
MAINTENANCE", after approving Phase 4's close. Build the machine-health domain model,
deterministic anomaly detection, and a predictive-model *abstraction* (explicitly not a
trained model — there is no real machine dataset) entirely in software, using deterministic
simulation. Still no ESP-IDF/Mosquitto install, no hardware/sensor purchase, no Phase 6, no
real predictive-maintenance accuracy claim.

- **Extends `edge/src/msfc/analytics/`** (12 new modules) rather than creating a new
  top-level package — `ARCHITECTURE.md` section 7.2 already assigns this one Layer-7 package
  to both OEE (Phase 4) *and* health analysis (Phase 5), and the pre-declared layer rules have
  no separate "health" entry. Building a new package would have been exactly the
  "duplicate/conflicting" structure the PO's directive warned against.
  - `health_models.py`: `SensorMeasurement`, `SensorType` (8 values), `SensorQuality` (8
    values), `FeatureSet`, `AnomalySeverity`, `AnomalyResult`, `HealthState` (5 values:
    HEALTHY/WARNING/ANOMALY/CRITICAL/UNKNOWN), `HealthScore`, `HealthEvent`.
  - `sensors.py`: `SensorSource` protocol + `FixedSequenceSensorSource` — the same
    Mock-then-Protocol-then-real pattern already used twice (`OcrEngine`/`InferenceEngine`),
    reused rather than reinvented.
  - `quality.py`: deterministic quality assessment (MISSING/INVALID/STALE/FUTURE_TIMESTAMP/
    DUPLICATE/INVALID_UNIT/UNAVAILABLE/OK) — a bad reading is always recorded with an honest
    tag, never silently treated as valid.
  - `features.py`: min/max/mean/median/std-dev/variance/range/rate-of-change/moving-average/
    RMS, computed only over OK-quality measurements.
  - `baseline.py`: `HealthBaseline` — configurable expected range + optional reference
    mean/std-dev, never a hard-coded value for any real machine (none exists yet).
  - `anomaly.py`: threshold/deviation, trend, and sensor-quality detectors, plus
    `combine_anomalies()` (always the MAXIMUM severity present, never an average or vote).
  - `health_score.py`: a documented, explicitly-not-calibrated 0.0-1.0 score.
  - `health_events.py` / `health_monitor.py`: the same "factory functions + a monitor that
    consumes pre-built events" pattern as P4's `events.py`/`session.py`.
  - `predictive.py`: `PredictiveHealthModel` protocol, `ModelInputContract`, and
    `RuleBasedReferenceModel` — a deterministic reference implementation built from the same
    rule-based anomaly detection the rest of the package uses, **not a trained model of any
    kind**; `PredictiveHealthResult.validated_on_real_data` is always `False` for it.
  - `health_repository.py`: in-memory sensor-history storage only, same reasoning as P4.17/D-050.
  - `evaluation.py`: precision/recall/F1/FPR/FNR/MAE/RMSE/detection-delay as a framework,
    verified only against hand-computed numbers — never run against the synthetic fixtures and
    reported as a real accuracy figure. ROC-AUC/PR-AUC deliberately not implemented (no real
    scored classifier exists yet to evaluate — D-053).
  - `health_simulate.py`: the 15 named scenarios, no randomness at all.
  - `health_p4_bridge.py`: the *one*, opt-in bridge from a health event to a P4 `MachineEvent`
    — only `MACHINE_HEALTH_CRITICAL` becomes an observational FAULT marker; WARNING/ANOMALY
    never touch P4 at all (P5.17: not every anomaly is downtime). Documents the distinction
    between HEALTH ANOMALY, MACHINE FAULT, DOWNTIME, and EMERGENCY STOP (D-054).
- **A real conflict between phases, handled per instruction**: this round's explicit 5-value
  `HealthState` and 8-value `SensorType` disagree with the Phase-0 draft schemas
  (`health_state.v1.json`: 4 values, no ANOMALY; `health_features.v1.json`: 3 sensor types).
  Neither draft schema was edited (both unused by any running code); the conflict is recorded
  as D-051 for the founder to resolve when those schemas are finalized.
- **Two real bugs caught and fixed before writing the test suite, not after** (same discipline
  as D-039/D-044/D-049): a manual run of all 15 scenarios showed every "spike" scenario
  (temperature/current/vibration) falsely reporting HEALTHY — averaging a brief spike together
  with several normal readings diluted it below any reasonable threshold. Fixed by checking the
  window's most extreme value instead of its mean (D-055). The same run showed a single shared
  threshold set couldn't sensibly cover sensors of very different natural scale (a few degC vs
  a few mm/s vs a few A); fixed by keying `AnomalyThresholds` per `sensor_id`, mirroring how
  `baselines` already worked (D-056).
- **Test:** 14 new unit files + 1 new integration file, **143 tests** — 10+4+16+10+10+16+6+9+
  10+9+5+12+5+19 across the unit files (see TEST_REPORT.md for the full breakdown) plus 2
  integration tests proving the health-to-P4 bridge against the real, unmodified P4
  `ProductionSession`. Full suite: **712 passed, 1 skipped** (569 + 143, zero existing tests
  broken). Firmware C untouched — still 262/262.
- **`msfc.core.errors.HealthError`** added following the exact existing pattern — the only
  change to any file outside `msfc.analytics` and its tests.
- **New doc:** `PHASE5_COMPLETION_REPORT.md`.
- **Deferred, documented not invented:** publishing `health.state`/`health.telemetry.features`
  over real MQTT, and an `msfc.storage`-backed sensor-history repository, both wait for
  `msfc.services` to exist, matching the D-040/D-048/D-050 pattern established in earlier
  rounds.

### Added — Phase 4: Software-only OEE / Machine Monitoring (2026-09-18)

PO directive "START PHASE 4 — SOFTWARE-ONLY OEE / MACHINE MONITORING", after approving
Phase 3's close. Build the OEE/machine-monitoring domain model and a host-testable pipeline
entirely in software, using deterministic simulation — no real sensors, ESP32, PLC, motor,
encoder, camera, or MQTT broker. Still no ESP-IDF/Mosquitto install, no hardware purchase, no
Phase 5, no predictive maintenance, no OEE-overrides-safety behavior (architecturally
impossible, not just disciplined against, per the layer dependency rules).

- **`edge/src/msfc/analytics/`** (new package, Layer 7, pre-declared since Phase 0 in both
  `ARCHITECTURE.md` and `test_layer_dependencies.py` as depending only on `core`+`domain` —
  meaning it cannot import `msfc.sim`, `msfc.decision`, or the firmware, so it is
  architecturally incapable of commanding anything safety-relevant):
  - **Maximal reuse of existing P1 concepts, not new competing ones** (the PO's explicit
    priority): machine state is `msfc.domain.enums.MachineState` (the same 9-value enum P1/P2
    already use, not a new enum); production counts are `msfc.domain.state.Counters`
    (detected/passed/rejected/no_decision) reused directly rather than re-invented.
  - `models.py`: `OeeResult`, `DowntimeCategory`, `DowntimeInterval`, `CycleStatistics`,
    `MachineStatus`.
  - `events.py`: `MachineEvent`/`MachineEventType` (machine_start/stop, cycle_start/complete,
    product_good/defect, downtime_start/end, fault/fault_clear, emergency_stop, reset) plus
    factory functions that build these from the *existing, unmodified* `StateChangedEvent`,
    `ProductDetectedEvent`, `ProductSortedEvent`, and `FaultReport` — proven against the real
    dataclasses (not stand-ins) in a new integration test.
  - `calculations.py`: Availability/Performance/Quality/OEE as pure functions, each raising
    `OeeError` rather than silently returning a misleading number for invalid input (zero/
    negative planned time, zero run time, out-of-range counts). Performance/OEE are **not**
    clamped to 1.0 internally — a real cycle faster than the configured "ideal" is a valid
    result, not a bug.
  - `session.py`: `ProductionSession`, the package's one stateful object — processes a
    `MachineEvent` stream deterministically, accumulating counts, downtime intervals (split
    by category), and cycle-time statistics (min/max/average/slow-cycle/incomplete-cycle
    counts). Every boundary (planned production time, ideal cycle time, slow-cycle threshold)
    is a `SessionConfig` field, never a hard-coded real shift.
  - `monitor.py`: `MachineMonitor`, wrapping one session to expose current status/OEE snapshot
    independent of physical hardware — "Mock Machine Events -> MachineMonitor -> OEE Engine ->
    OEE Result" today, the same interface for real ESP32/PLC events later.
  - `repository.py`: `OeeSnapshotRepository` protocol + `InMemoryOeeSnapshotRepository` — no
    production database, per the explicit "keep it lightweight" instruction.
  - `simulate.py`: the 10 named scenarios (normal production, normal cycles, planned/
    unplanned downtime, machine fault, emergency stop, defect production, mixed GOOD/DEFECT,
    slow cycles, multiple sessions), each sized so its OEE numbers are hand-checkable.
- **Three real design questions resolved and recorded, not silently chosen** (D-045 through
  D-050, DECISIONS.md): (1) `RawVerdict.UNCERTAIN` never reaches this layer at all — msfc.decision
  already resolves it into a final GOOD/DEFECT before a product is ever sorted, so the OEE
  layer only ever sees `SortAction.PASSED`/`REJECTED`; (2) MAINTENANCE is a downtime-category
  tag, not a new `MachineState` value, since no state alone can say "this idle time was
  scheduled"; (3) planned/maintenance downtime is excluded from the Availability
  *denominator* itself (classical Nakajima OEE), while unplanned/fault/e-stop/idle downtime is
  subtracted from the *numerator* — demonstrated by two identically-shaped scenarios
  (`scenario_planned_downtime` reads OEE=1.0, `scenario_unplanned_downtime` reads a reduced
  availability) that differ only in downtime category.
- **A genuine schema conflict found between phases, handled per instruction ("stop, document,
  don't silently rewrite a previous phase")**: `contracts/schemas/oee_metrics.v1.json` (a
  Phase-0 draft, still unused by any running code) caps `performance`/`oee` at 1.0, but the
  correct calculation can honestly exceed 1.0. The schema file was left untouched; a
  `to_oee_metrics_v1_payload()` helper clamps only at that one wire-payload boundary, keeping
  the underlying `OeeResult` unaltered. Flagged for the founder as Q-18.
- **Two real bugs caught and fixed before writing tests, not after** (same discipline as
  D-039/D-044 in earlier rounds): a manual run of all 10 scenarios before writing the test
  suite showed `scenario_normal_production` failing with "run_time_ms must be > 0" — the
  default BOOT initial state opens a downtime interval that nothing in a pure-production
  scenario ever closes; fixed by starting production-focused scenarios in RUNNING (the boot
  sequence itself is already covered by P1/P2). The same run exposed that a transition between
  two *different* non-production states (e.g. ESTOP -> IDLE during recovery) wasn't closing
  and reopening the downtime interval with the new state's category — fixed in
  `from_state_changed()` to emit both a `downtime_end` and a `downtime_start` in that case.
- **Test:** 7 new unit files + 1 integration file, **99 tests** — `test_analytics_models.py`
  (10), `test_analytics_events.py` (14), `test_analytics_calculations.py` (25),
  `test_analytics_session.py` (22), `test_analytics_monitor.py` (5),
  `test_analytics_repository.py` (5), `test_analytics_fixtures.py` (17, covering all 10 P4.13
  scenarios and the 15 P4.14 fixtures), `tests/integration/test_analytics_domain_integration.py`
  (1, a realistic production run expressed entirely in real `msfc.domain` event types). Full
  suite: **569 passed, 1 skipped** (470 + 99, zero existing tests broken). Firmware C
  untouched — still 262/262.
- **`msfc.core.errors.OeeError`** added following the exact existing pattern
  (`VisionError`/`DecisionError`/`SimulationError`/`OcrError`) — the only change to any file
  outside the new `msfc.analytics` package and its tests.
- **New doc:** `PHASE4_COMPLETION_REPORT.md`.
- **Deferred, documented not invented:** an `msfc.storage`-backed (e.g. SQLite) repository
  implementation is out of scope — `msfc.analytics` cannot depend on `msfc.storage` per the
  pre-declared layer rules; wiring the two together belongs to `msfc.services`, which doesn't
  exist yet (D-050). Publishing `oee.state.metrics` over real MQTT likewise waits for
  `msfc.services` (D-040/D-048 pattern, Q-17/Q-18).

### Added — Phase 3: Software-only OCR / Expiry / Label Verification (2026-09-18)

PO directive "START PHASE 3 — SOFTWARE-ONLY OCR / EXPIRY / LABEL VERIFICATION", after
approving Phase 2's close. Build the OCR/expiry/label domain model and a host-testable
pipeline entirely in software, integrate with the existing decision layer without modifying
it, using only synthetic images and mocks. Still no ESP-IDF/Mosquitto install, no hardware
purchase, no Phase 4, no change to AI model behavior.

- **`edge/src/msfc/ocr/`** (new package, Layer 3, sibling of `msfc.vision` — already
  pre-declared in `test_layer_dependencies.py` since Phase 0 as depending only on
  `core`+`domain`, so no test file needed changing to accept it):
  - `models.py`: `OcrOutput`, `BoundingBox`, `DateCandidate`, `DateExtractionResult`,
    `DetectedField`, `OcrValidationResult`, and `OcrReasonCode` — exactly the 6 codes
    `docs/REQUIREMENTS.md`'s FR-OCR-04 already specified in Phase 0 (OK, EXPIRED,
    FORMAT_INVALID, UNREADABLE, LABEL_MISSING, LABEL_MISALIGNED), no ad-hoc codes added.
  - `engine.py`: `OcrEngine` protocol (mirrors `msfc.vision.InferenceEngine`'s shape),
    `MockOcrEngine` (fixed response), `FixtureOcrEngine` (deterministic, driven by explicit
    `set_next_output()` calls — the same state-driven pattern
    `tests/integration/test_full_pipeline_mvp.py`'s `_OracleVisionEngine` already uses).
  - `preprocess.py`: grayscale, resize, contrast, denoise, adaptive threshold, ROI crop, skew
    estimation and deskew — its own small `RoiConfig`, deliberately not importing
    `msfc.vision`'s near-identical one (the pre-declared layer rule forbids `ocr` depending on
    `vision`; a small duplication is the accepted cost of keeping that boundary — D-041).
  - `text.py`: whitespace/case normalization (unconditional) plus date extraction across
    exactly the 5 formats named (DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD, YYYY-MM-DD, MM/YYYY).
    OCR digit-confusion correction (O/o->0, I/l/i->1, S/s->5, B->8) is scoped **only** to
    substrings that already look date-shaped, never applied to arbitrary text, so a garbled
    label can't be silently turned into a fabricated valid date.
  - `validate.py`: `LabelValidationConfig` (required substrings, product-id regex, max skew,
    min confidence — never one hard-coded real product) and `validate_label()`, resolving
    every finer-grained condition (missing/ambiguous/impossible-calendar date, wrong product
    id, misalignment) down to one of the 6 FR-OCR-04 codes, with an explicit `ambiguous` flag
    kept alongside so classification can treat it as uncertain rather than a defect.
  - `classify.py`: GOOD/DEFECT/UNCERTAIN per exactly the PO's rules — UNREADABLE and ambiguous
    results are always UNCERTAIN, confidence below threshold forces UNCERTAIN regardless of
    reason, never GOOD/DEFECT for something the pipeline isn't sure about. Wraps a result into
    the *same* `msfc.domain.InspectionResult` type vision produces.
  - `pipeline.py`: the full P3.9 flow (preprocess -> engine -> normalize -> extract/validate ->
    classify -> InspectionResult), with a broken OCR engine or empty/malformed output resolving
    deterministically to UNREADABLE/UNCERTAIN instead of crashing, while a genuine caller
    misconfiguration (bad ROI) still raises.
  - `synthetic.py`: 12 deterministic fixtures — exactly the scenarios the founder named (valid
    expiry, expired, impossible date, missing expiry, wrong product id, valid product+expiry,
    low confidence, ambiguous OCR, a non-default date format, OCR noise, empty result,
    malformed result) — each a real rendered image (`cv2.putText`, 0 VND, no internet) whose
    ground truth is read by `FixtureOcrEngine`, not analyzed from pixels (same synthetic-only
    discipline as `msfc.vision.synthetic`, D-026).
- **Decision-layer integration required zero changes to `msfc.decision`**: `DecisionEngine`
  already accepted any number of inspection channels and combined them "any DEFECT wins" —
  its own docstring already said "OCR joins in Phase 3." Proven by a new integration test
  combining a vision channel and an OCR channel for the same product, including the case
  vision alone would pass but OCR's expired-label DEFECT still wins.
- **One real bug caught and fixed before writing tests, not after:** the first
  `FixtureOcrEngine` design looked up ground truth by `id(image)`; since
  `run_ocr_pipeline()` always calls `preprocess()` (which returns a new array) before
  `engine.read()`, that lookup could never succeed — a manual smoke run of all 12 fixtures
  showed 11/12 silently resolving to UNREADABLE. Fixed by switching to the explicit,
  precedented `set_next_output()` pattern (D-044).
- **Test:** 9 new files, **103 tests** — `test_ocr_models.py` (8), `test_ocr_engine.py` (6),
  `test_ocr_preprocess.py` (17), `test_ocr_text.py` (17), `test_ocr_validate.py` (17),
  `test_ocr_classify.py` (11), `test_ocr_pipeline.py` (7), `test_ocr_fixtures.py` (15,
  parametrized over the 12 scenarios), `tests/integration/test_ocr_decision_integration.py`
  (5). Full suite: **470 passed, 1 skipped** (367 + 103, zero existing tests broken).
- **`msfc.core.errors.OcrError`** added following the exact existing pattern
  (`VisionError`/`DecisionError`/`SimulationError`) — the only change to any file outside the
  new `msfc.ocr` package and its tests.
- **New doc:** `PHASE3_COMPLETION_REPORT.md`.
- **Deferred, documented not invented:** merging the new label-check vocabulary into the MQTT
  contract (`label_result.v1`, currently a draft topic) waits for `msfc.services` to exist
  (D-040/Q-17) — out of scope for a software-only OCR round with no broker wiring yet.

### Added — Phase 2: Software-only Safety & Interlock (2026-09-18)

PO directive "START PHASE 2 — SOFTWARE-ONLY SAFETY & INTERLOCK": build the safety/interlock
architecture entirely in software, reusing Phase 1's C firmware wherever possible, with an
explicit rule that a software E-STOP simulation is never to be claimed as physical E-stop
validation. Still no ESP-IDF/Mosquitto install, no hardware purchase, no Phase 3.

- **`firmware/cell_controller/components/core_logic/safety_interlock.h/.c`** (new, purely
  additive — `cell_sm.c`, `fault_manager.c`, `watchdog.c`, `cmd_handler.c`, `hal_interface.h`
  and `hal_host_mock.c` from Phase 1 were **not modified**): wraps the existing state machine,
  fault manager, watchdog and command dispatcher into one supervisor exposing the six
  PO-named safety states (SAFE_IDLE, READY, RUNNING, FAULT, ESTOP, RECOVERY) as a view derived
  from `cell_sm_t`'s existing 9 states (mapping and rationale: D-038) — plus one genuinely new
  concept, RECOVERY, an explicit gate between an accepted RESET and
  `safety_interlock_confirm_recovery()` that re-checks every interlock condition before
  allowing motion commands again (P2.8: "avoid automatic recovery where it could violate
  safety assumptions").
- **8-condition interlock matrix** (P2.3): E-STOP, safety fault, communication loss, invalid
  command, motor fault, sensor fault, system not ready, recovery not completed — each with a
  deterministic accept/reject outcome, reusing `cmd_handler_dispatch()`'s existing rules for
  the ones P1 already covered and adding only the ones it didn't (motor/sensor fault, a
  specific comm-loss reason, the recovery gate).
- **Comm-loss / watchdog integration (P2.5/P2.6) — one real bug caught before it shipped:**
  the design first reused P1's `watchdog_check()` directly, but that function latches
  `expired` permanently after the first timeout (correct for a one-shot device-reset
  watchdog, wrong for comm loss, which must self-clear once heartbeats resume). Caught while
  designing the "communication recovery" and "repeated timeout" scenarios, before writing the
  tests — fixed by reading `watchdog_t`'s existing `last_feed_mono_ms`/`timeout_ms` fields
  directly for a live, self-clearing freshness check, instead of modifying `watchdog.c` (which
  is correct for its original P1 caller and remains untouched). See D-039.
- **Software E-STOP (P2.2):** forces the safety state to ESTOP immediately, inhibits all
  motion/actuator commands (`REJECT_ESTOP_LATCHED`, reused from P1's `cmd_handler`), rejects
  new RUN commands, and requires an explicit RESET-then-confirm sequence to recover.
  **Documented in the module's own header, not just this changelog: this is a software
  simulation, not physical Emergency Stop validation** — the mandatory hardware E-stop channel
  (SAF-01, IF-HW-01: NC contact, wire-cut = active) is a separate, physical safety function
  that doesn't depend on any code running at all, and remains unverified until real hardware
  exists.
- **Safe state (P2.4):** no new code — reuses P1's `safety_supervisor.c` unchanged, which
  already guarantees motor/relay/pusher are off in every state except RUNNING.
- **Software safety simulator (P2.9):** `test_safety_scenarios.c` runs the exact 12 scenarios
  named in the PO's directive (normal startup, READY→RUNNING, RUNNING→E-STOP, E-STOP reset,
  RUNNING→comm loss, comm recovery, RUNNING→motor fault, RUNNING→sensor fault, invalid
  command, FAULT→recovery, watchdog timeout, repeated fault), each asserting one deterministic
  expected result.
- **Test:** 4 new files, **131 checks, 0 failed** (`test_safety_interlock_core.c` 34,
  `test_safety_interlock_comm_loss.c` 43, `test_safety_interlock_recovery.c` 27,
  `test_safety_scenarios.c` 27). Combined with Phase 1's unchanged 131: **262/262 PASS**,
  `-std=c99 -Wall -Wextra -Werror`, zero warnings. Full Python regression run once at the gate:
  **367 passed, 1 skipped**, unchanged (no Python file touched this round).
- **Deferred, documented not invented (D-040):** the new interlock reject reasons
  (motor/sensor fault, recovery-not-complete) exist only in the C firmware for now, not yet in
  `msfc.domain.enums.RejectReason` or the `cmd_ack.v1` JSON Schema — merging them is a contract
  -layer change larger than this round's "software-only safety/interlock" scope, deferred to
  when P1.10 needs to send them over real MQTT.
- **New doc:** `PHASE2_COMPLETION_REPORT.md`.

### Added — Phase 1 software-first, round 3: Close Phase 1 Software Gate, P1.5 core_logic (2026-09-18)

PO directive "Close Phase 1 Software Gate": prioritize P1.5, check the ESP-IDF/gcc/Mosquitto
environment first, implement what's possible without hardware, don't fake a DONE. Still no
procurement/hardware/Phase 2.

- **Environment check found `gcc` already installed** (MSYS2 UCRT64,
  `C:\msys64\ucrt64\bin\gcc.exe` 16.1.0) but not on PATH — `tools/check_env.py` and `which gcc`
  both report it MISSING because they only check PATH. Verified by compiling and running a
  throwaway C program with the path prefixed. No system-wide PATH change was made (that's a
  system-settings change outside this project's automated authority); the build script
  prefixes PATH for its own invocation only. `idf.py` (ESP-IDF SDK) and `mosquitto` are
  genuinely absent from this machine — confirmed by checking common install locations, not
  just PATH.
- **`firmware/cell_controller/components/core_logic/`** (new, C99, zero ESP-IDF dependency per
  the architecture's own rule 1, so it builds and runs on the host): `cell_sm` (9-state machine
  mirroring `msfc.domain.enums.MachineState`, ESTOP > SAFE_STOP > FAULT priority),
  `fault_manager` (firmware-local fault subset, codes cross-checked against
  `msfc.domain.faults.FAULT_CATALOG`), `debounce`, `safety_supervisor` (the one place allowed
  to decide `hal_outputs_t` — motor/relay/pusher are off in every state except RUNNING,
  regardless of what's requested), `cmd_handler` (START/STOP/RESET/SET_SPEED/PUSHER_TEST ->
  ACCEPTED/REJECTED with reason codes matching `msfc.domain.enums.RejectReason`), `watchdog`
  (pure timeout tracker), `logger`, and `comm_link.h` (a function-pointer interface boundary
  only — no real MQTT client, since that needs esp-mqtt/ESP-IDF and there's no hardware to run
  it on).
- **`firmware/cell_controller/components/hal/`**: `hal_interface.h` implementing
  `docs/HARDWARE_INTERFACE.md` section 4's contract exactly, except `esp_err_t` ->
  `hal_status_t` (a neutral status type, since this header must not pull in ESP-IDF types
  either); `hal_host_mock.c/.h` for scripted host testing.
  `hal_esp32` (real hardware, P1.10) will implement the same three functions later.
- **`firmware/cell_controller/test_host/`**: 7 test files + `build_and_run.sh` — **131 checks,
  0 failed**, built with `-std=c99 -Wall -Wextra -Werror` (zero warnings). Not vendored Unity
  (adding a new third-party dependency wasn't approved this round) — a small custom assert
  harness structured closely enough to swap in real Unity later without much rework.
- **Honest scope limit, not a gap:** `idf.py build` (compiling for the actual ESP32 chip)
  remains **BLOCKED** — the ESP-IDF SDK itself is still missing, `gcc` alone doesn't unblock
  it. P1.5 is therefore reported as DONE for its host-testable `core_logic` half only, not as a
  whole. `product_tracker`/`heartbeat_monitor`/`timing_stats` were left for later — they weren't
  in this round's priority list.
- **No procurement attempted for Mosquitto or ESP-IDF**: both require downloading and running
  an installer, which this project's automation treats as requiring the founder's own action;
  short install commands are provided in PROJECT_STATUS.md's blocker section instead. The
  broker-dependent integration test continues to skip honestly (1 skipped, unchanged).
- **Docs:** PROJECT_STATUS.md, TASKS.md, TEST_REPORT.md, DECISIONS.md (D-036 gcc-found,
  D-037 P1.5 split into host-testable-done vs. chip-build-still-blocked) updated; no new
  documentation files.

### Added — Phase 1 software-first, round 2: P1.3 CNN/ONNX training scaffold (2026-09-18)

PO directive "Phase 1 — Software Gate / AI Completion": complete P1.3's deferred CNN/ONNX
piece (D-033), still no procurement/hardware/Phase 2. Adds 17 tests (367 passed, 1 skipped
total, up from 350+1 — no existing test broken).

- **`msfc.vision.training`** (new, not imported by `msfc.vision.__init__` — requires `torch`):
  `TrainingConfig`, `CapDataset` (reuses the exact same `preprocess()` production inference
  uses), `split_by_session()` (requires >=3 sessions, never silently falls back to an
  index-based split — DATASET_SPEC.md section 6), `TinyCapCNN` (3 conv blocks +
  `AdaptiveAvgPool2d`, spatial-size-agnostic), `train_smoke_test()` (selects the best epoch by
  validation F1, saves a checkpoint), `export_onnx()` (legacy `dynamo=False` exporter — the new
  default needs the optional `onnxscript` package this project doesn't otherwise use; verified
  round-trip max abs diff ~3.7e-9 against PyTorch before writing the real module).
- **`msfc.vision.onnx_backend`** (new, requires `onnxruntime`): `OnnxInferenceEngine`
  implements the exact `InferenceEngine` protocol, so it is a drop-in replacement for
  `ClassicCvBaseline` in the existing `postprocess()`/`DecisionEngine` pipeline — proven by a
  dedicated test that runs an ONNX-exported model through both unmodified.
- **Honest finding, not hidden:** trained on a 36-image synthetic dataset (3 sessions x 12
  images, 2-epoch smoke test — deliberately short, per the founder's explicit "don't train
  long, don't over-optimize" instruction), `TinyCapCNN` predicts every image as GOOD
  (accuracy=0.5, F1(DEFECT)=0.0 on the held-out test session) — the same failure mode already
  logged for `ClassicCvBaseline` as risk R-28. Confirmed this is a dataset/training-budget
  limitation, not a wiring bug: the ONNX Runtime output matches the PyTorch model to <1e-4, and
  the full `postprocess()`→`DecisionEngine` path runs correctly on this model's output. Logged
  as decision D-035; no threshold was tuned and no extra training was added to force a
  different result. See `ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/model_card.md`.
- **Persisted smoke-test artifact** (not committed to git, per the existing
  `ai/models/README.md` convention): `ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/` —
  `checkpoint.pt`, `model.onnx`, `metrics.json`, `config.toml`, `checksum.txt`, `model_card.md`.
- **P1.5 re-confirmed BLOCKED** (not re-attempted): `firmware/cell_controller/` still contains
  only `README.md` — no C code was written or claimed to exist; still needs ESP-IDF + MSYS2 gcc
  (B4), which this round did not install.
- **New tests:** `edge/tests/unit/test_vision_training_smoke.py` (12),
  `edge/tests/unit/test_vision_onnx_inference_smoke.py` (5).
- **No new dependencies:** `torch`, `torchvision`, `onnxruntime`, `onnx` were already installed
  from the previous round.

### Added — Phase 1 software-first: P1.1–P1.7 + pipeline MVP (2026-09-18)

PO approved continuing P1.1→P1.7 by software/mock only (no procurement, no Phase 2), with an
explicit STOP after completion. This adds 351 tests (350 passed, 1 honestly skipped — no
broker installed) across six new packages, all under `edge/src/msfc/`.

- **`msfc.domain`** (P1.1, 80 tests): pure dataclasses/enums mirroring every contract schema —
  `enums.py`, `faults.py` (19-code catalog with severity/latching derived from
  SAFETY_CONCEPT.md), `events.py`, `inspection.py`, `commands.py`, `state.py`
  (`CellStateSnapshot` enforces SAF-10/SF-07 — pusher-retracted/relay-open outside
  STARTING/RUNNING/STOPPING — as a data-level invariant, not just a runtime check).
- **`msfc.contracts`** (P1.7, 45 tests): `ContractRegistry` (loads `topics.toml`, compiles
  topic-pattern regexes, `format_topic`/`match_topic`, caches JSON Schemas), `build_envelope`
  + `SeqCounter`, `PayloadValidator` (`jsonschema.Draft202012Validator`, rejects
  shape/schema-mismatch/data errors with the topic named). A dead `name`-placeholder
  parameter present in an early draft was removed once tests showed no real topic uses it.
- **`msfc.comm`** (P1.7, 53 tests): `MessageBus` protocol, `InMemoryBus` (synchronous,
  MQTT-retain-accurate, wildcard-matching), `compile_topic_filter` (`+`/`#`), `DedupeFilter`
  (bounded, by device+boot+seq), `ReconnectBackoff`, `MqttBus` (paho-mqtt wrapper, dependency-
  injectable client so tests never touch a real socket; one optional integration test against
  a real broker that self-skips honestly when Mosquitto is absent).
- **`msfc.vision`** (P1.2 + P1.3-classical, 65 tests): `FrameSource` protocol with four real
  implementations — `SyntheticFrameSource`, `ImageFolderFrameSource` (tested against real
  PNGs written by the test itself), `VideoFileFrameSource` (tested against a real MP4 written
  via `cv2.VideoWriter`), `UsbCameraFrameSource` (failure path only — no camera exists);
  `synthetic.py` generates labelled "bottle cap" images with three hand-designed defect types
  (`MARK` easy, `STICKER_MISSING` medium, `SCRATCH` hard); `RoiConfig`/`preprocess`;
  `ClassicCvBaseline` (mean-abs-diff from an averaged GOOD template); `Thresholds`/
  `postprocess` (GOOD/DEFECT/UNCERTAIN); `evaluate()` (accuracy/precision/recall/F1/confusion/
  per-sub-label recall/FP-FN ids/latency percentiles, every report tagged `data_source` so a
  synthetic result can never be read as a real-product claim).
- **`msfc.decision`** (P1.4, 20 tests): `DecisionPolicy` + `DecisionEngine.decide()` — any
  DEFECT channel wins (fail-closed), UNCERTAIN resolves per policy (default DEFECT),
  `DECISION_LATE` flagged past a configurable deadline; `to_verdict_command()`.
- **`msfc.sim`** (P1.6, 38 tests): `SimCellController` — the "ESP32 mock" the founder asked
  for. Full state machine (BOOT→SELF_TEST→IDLE→STARTING→RUNNING→STOPPING plus SAFE_STOP/
  FAULT/ESTOP), product FIFO with GOOD/DEFECT routing and fail-closed NO_DECISION rejection,
  heartbeat-loss fail-safe (F010), E-stop with hardwired-equivalent immediate cutoff and
  forbidden remote reset (F001), queue overflow (F031), empty-queue tracking mismatch (F030),
  late-verdict (F032) and no-decision (F033) reporting — driven by one explicit, always-
  forward device clock (an early draft mistakenly used an incoming message's own `mono_ms`,
  which is the sender's clock, not this device's — corrected before writing tests, per
  ARCHITECTURE.md section 5.1). Speaks the real contract over any `MessageBus`, including
  direct MQTT-envelope delivery, not just direct Python calls.
- **Pipeline MVP integration test** (`tests/integration/test_full_pipeline_mvp.py`, 6 tests):
  wires FrameSource→preprocess→InferenceEngine→postprocess→DecisionEngine→SimCellController
  end to end over a real `InMemoryBus`, exactly matching the founder's pipeline diagram.
  Discovered and honestly reported that `ClassicCvBaseline`, calibrated against the synthetic
  generator's default ±8px position jitter, barely separates GOOD from DEFECT in absolute
  terms (measured: mean diff ≈ 21.9 for GOOD vs 21.9–23.2 for DEFECT) — logged as a real
  model limitation (risk R-28), not hidden; wiring tests isolate this from routing-correctness
  assertions using a deterministic label-aware stub engine, while one dedicated test still
  exercises the real baseline for interface compliance.
- **New docs:** `docs/HARDWARE_MASTER_BOM.md`, `docs/HARDWARE_INTERFACE.md`,
  `docs/DATASET_SPEC.md`; `docs/PHASE1_PLAN.md` v2.0 (P1.1–P1.12 split, AC-SW-01..07 gate).
- **Deferred, not forgotten:** P1.3's CNN/ONNX training smoke-test scaffold (torch/onnxruntime
  already installed) and P1.5's real C firmware (blocked on installing ESP-IDF/MSYS2 gcc —
  not requested for this round). Both tracked as open items in TASKS.md/PROJECT_STATUS.md.
- **New dependencies (free, justified):** `jsonschema` (payload validation), `onnxruntime`
  (installed for the deferred ONNX backend).

### Changed — PO UPDATE: hardware baseline = NONE (2026-09-18)

- **`HARDWARE_MASTER_BOM.md` (mới):** BOM đầy đủ cho toàn bộ S1 — 60 hạng mục trong 10 nhóm (compute, motion, sensors, safety, power, cơ khí, chiếu sáng, dây/đầu nối, dataset, dụng cụ), mỗi hạng mục có: chức năng cần thiết, số lượng, min spec, recommended, phương án giá thấp, giá ước tính, lý do, phase cần, mô phỏng được không, thay thế được không, rủi ro. Kèm 4 bảng so sánh phương án (động cơ, cảm biến, servo, camera) theo cost/performance/difficulty/reliability/expandability, 3 mức chi phí (MVP / S1 / OPTIONAL UPGRADE), 6 wave mua, bảng phase ↔ linh kiện, danh sách mô phỏng được vs bắt buộc hardware thật, và checklist kiểm tra hàng khi về.
- **`docs/HARDWARE_INTERFACE.md` (mới, P1.8):** 15 tín hiệu logic (hướng, mức tích cực, yêu cầu thời gian, hành vi khi lỗi, cách mô phỏng), yêu cầu điện, suy ra thông số phần cứng tối thiểu từ yêu cầu hệ thống, **HAL API** (hợp đồng giữa `core_logic` và phần cứng), 3 lớp hiện thực (esp32 / host mock / simulator), tham số cần hiệu chuẩn, test nghiệm thu từng interface.
- **`docs/DATASET_SPEC.md` (mới):** chọn sản phẩm mẫu giá thấp (nắp chai), 2 class + 3 sub-label lỗi tự tạo, kích thước dataset MVP (600 ảnh, khuyến nghị 1.000), cách chụp, chiếu sáng, khoảng cách camera, annotation, chia tập **theo phiên chụp**, tiêu chí báo cáo, dataset OCR Phase 3, và danh sách cần mua (0–40k).
- **`docs/PHASE1_PLAN.md` → v2.0:** Phase 1 chia thành **P1.1–P1.12**; P1.1–P1.8 làm bằng software/design/mock với 0đ phần cứng; thêm cổng **AC-SW-01..07** làm điều kiện để chuyển sang procurement; giữ nguyên AC-P1-01..11 cho phần cứng thật.
- **`HARDWARE_BOM.md`:** rút gọn thành bản tóm tắt theo phase và chi phí, trỏ về Master BOM; bỏ mọi giả định "đã có".
- **`docs/HARDWARE_INVENTORY.md`:** ghi nhận HARDWARE = NONE, liệt kê tài nguyên thực có (laptop/GPU/Python), 6 quyết định PO cần chọn thay cho việc khai báo thiết bị, và 6 việc làm được ngay với 0đ.
- **`DECISIONS.md`:** thêm D-019..D-028 (hardware = NONE; software-first; **không đưa AI inference lên ESP32 ở Phase 1**; mua theo wave; E-stop chỉ mua ở W2; sản phẩm mẫu nắp chai; dataset chia theo phiên; dữ liệu synthetic không dùng cho acceptance; cổng AC-SW; không mua hardware công nghiệp đắt tiền) và cập nhật bảng câu hỏi chờ PO.
- **`docs/RISK_REGISTER.md`:** đóng R-03, thêm R-21..R-26 (giả định sai về phần cứng, thời gian giao hàng, mua sai linh kiện, mô hình synthetic không dùng được, chi phí mua lẻ, thiếu dụng cụ đo).
- **`TASKS.md`, `PROJECT_STATUS.md`:** cập nhật theo cấu trúc P1.1–P1.12 và 5 blocker mới.

### Added — Phase 0: Project Foundation (2026-09-17/18)

**Tài liệu**
- `docs/PROJECT_CHARTER.md`: mục đích, vai trò PO/Claude Inc, phạm vi S1, 7 ràng buộc, giới hạn của Claude Inc.
- `docs/REQUIREMENTS.md`: 15 yêu cầu an toàn (SAF-01..15), yêu cầu chức năng cho 9 nhóm (CNV, VIS, DEC, SVS, OCR, OEE, HLT, COM, SRV/DB/DSH/OPS/AIP/EXT), NFR, 20 tiêu chí chấp nhận cuối (ACC-01..20).
- `ARCHITECTURE.md`: kiến trúc 9 layer, 2 node chính + 2 node tương lai, máy trạng thái Cell Controller, luồng kiểm tra sản phẩm, luồng an toàn, ngân sách thời gian, cấu trúc package + quy tắc phụ thuộc, 11 interface.
- `docs/SAFETY_CONCEPT.md`: 8 mối nguy, 8 chức năng an toàn (SF-01..08), kiến trúc 2 kênh, ma trận reset, bảng mã lỗi (F001..F070, E1xx), nguyên tắc đấu dây an toàn.
- `docs/MQTT_CONTRACT.md`: ngữ pháp topic, envelope, chính sách QoS/retain, danh mục 25 topic, ngữ nghĩa lệnh/ack, heartbeat, trạng thái lỗi, quy tắc phiên bản, bảo mật.
- `docs/adr/0001..0013`: 13 quyết định kiến trúc, mỗi ADR có so sánh phương án (chi phí / độ phức tạp / độ tin cậy).
- `docs/QA_PLAN.md`: 10 mức test, 17 test an toàn, 12 test lỗi, PT/LT/VT/MT, điều kiện vào–ra từng phase, ma trận truy vết.
- `docs/CODING_STANDARDS.md`, `docs/GIT_STRATEGY.md`, `docs/CONFIGURATION.md`, `docs/LOGGING.md`.
- `docs/RISK_REGISTER.md`: 20 rủi ro có xác suất/tác động/dấu hiệu sớm/biện pháp.
- `docs/HARDWARE_INVENTORY.md` (checklist cho PO + bằng chứng audit máy), `HARDWARE_BOM.md` (BOM theo phase, nhãn REQUIRED/OPTIONAL/FUTURE), `hardware/PIN_MAPPING_DRAFT.md`.
- `docs/PHASE1_PLAN.md`: MVP, 5 milestone, 18 task, 11 acceptance criteria, 5 blocker, điểm dừng cho việc tay của PO.
- `ROADMAP.md` (Phase 0–7), `TASKS.md`, `DECISIONS.md` (18 quyết định + 9 câu hỏi chờ PO), `PROJECT_STATUS.md`, `TEST_REPORT.md`, `README.md`.

**Contract**
- `contracts/mqtt/topics.toml`: registry 25 topic (publisher, subscriber, QoS, retain, schema, rate, phase, status) — nguồn sự thật duy nhất cho topic.
- `contracts/schemas/*.json`: 23 JSON Schema (envelope + payload cho Phase 1–2, bản draft cho Phase 3–5).

**Code (nền tảng, không có dependency runtime)**
- `edge/src/msfc/core/config.py`: cấu hình phân lớp `default.toml` → `site.toml` → biến môi trường, dataclass bất biến, kiểm tra nghiêm ngặt (khóa lạ là lỗi, kiểm tra dải giá trị).
- `edge/src/msfc/core/logging_setup.py`: console cho người + JSON lines cho máy, trường ngữ cảnh, xoay vòng file, idempotent.
- `edge/src/msfc/core/errors.py`: cây exception (`MsfcError`, `ConfigError`, `ContractError`, `PayloadInvalidError`).
- `config/default.toml`, `config/site.example.toml`, `edge/pyproject.toml`.
- `tools/check_env.py`: kiểm tra môi trường phát triển theo phase.
- `firmware/cell_controller/README.md`: kiến trúc module firmware (chưa có code).

**Test (43 case, tất cả pass)**
- `edge/tests/unit/test_config.py` (20), `test_logging_setup.py` (8), `test_layer_dependencies.py` (2).
- `edge/tests/contract/test_contract_files.py` (13): ngữ pháp topic, QoS/retain, schema, đồng bộ tài liệu, kênh an toàn được đánh dấu.

### Notes
- Chưa có phần cứng nào được lắp hoặc kiểm chứng; chưa mua gì.
- Chưa có commit git nào (PO quyết định thời điểm commit — ADR-0013).
- Mọi ADR ở trạng thái PROPOSED, chờ PO duyệt Phase 0.
