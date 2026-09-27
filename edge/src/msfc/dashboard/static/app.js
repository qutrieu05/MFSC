// S1 Mini Smart Factory Cell -- Official Dashboard frontend.
// Plain JS, no build step, no framework (section 3: "avoid unnecessary infrastructure").
// Every value rendered here comes from a fetch()/WebSocket message against the real backend
// API (msfc.dashboard.api) -- nothing in this file invents a verdict, an OEE number, or a
// health state (section 2/8: "do not independently calculate authoritative ... in the UI").

const API = "/api";
let ws = null;
let activeTab = "overview";

// ---------------------------------------------------------------- utilities
function fmtPct(x) {
  if (x === null || x === undefined) return "—";
  return (x * 100).toFixed(1) + "%";
}
function fmtNum(x, digits = 2) {
  if (x === null || x === undefined) return "—";
  return Number(x).toFixed(digits);
}
function stateClass(value) {
  if (!value) return "state-unknown";
  return "state-" + String(value).toLowerCase();
}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
async function api(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { const body = await res.json(); detail = body.detail || body.error || detail; } catch (e) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}
async function post(path) {
  return api(path, { method: "POST" });
}

// ---------------------------------------------------------------- tabs
function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      document.getElementById("panel-" + tab).classList.add("active");
      activeTab = tab;
      loadActiveTab();
    });
  });
}

function loadActiveTab() {
  switch (activeTab) {
    case "overview": return refreshOverview();
    case "production": return refreshProduction();
    case "vision-ocr": return refreshVisionOcr();
    case "safety": return refreshSafety();
    case "health": return refreshHealth();
    case "oee": return refreshOee();
    case "events": return refreshEvents();
    case "diagnostics": return refreshDiagnostics();
  }
}

// ---------------------------------------------------------------- header badges
function updateHeaderBadges(system, safety) {
  const rt = document.getElementById("badge-runtime");
  rt.textContent = "RUNTIME: " + (system.runtime_state || "UNKNOWN");
  rt.className = "badge " + (
    system.runtime_state === "RUNNING" ? "badge-running" :
    system.runtime_state === "FAULT" ? "badge-fault" :
    system.runtime_state === "SAFE_STOP" ? "badge-estop" : "badge-unknown"
  );

  const mc = document.getElementById("badge-machine");
  mc.textContent = "CELL: " + (system.machine_state || "UNKNOWN");
  mc.className = "badge " + (
    system.machine_state === "ESTOP" ? "badge-estop" :
    system.machine_state === "FAULT" || system.machine_state === "SAFE_STOP" ? "badge-fault" :
    system.machine_state === "RUNNING" ? "badge-running" : "badge-unknown"
  );
}

// ---------------------------------------------------------------- pipeline rendering (shared by Overview + Vision&OCR)
function renderPipeline(container, pipeline) {
  container.innerHTML = "";
  if (!pipeline.product_id) {
    container.appendChild(el("div", "section-note", "No product processed yet in this session."));
    return;
  }
  const labels = { vision: "Vision", ocr: "OCR", decision: "Decision", safety: "Safety Gate" };
  pipeline.stages.forEach((stage, i) => {
    if (i > 0) container.appendChild(el("div", "pipeline-arrow", "→"));
    const box = el("div", "pipeline-stage" + (stage.available ? "" : " stage-unavailable"));
    box.appendChild(el("div", "stage-name", labels[stage.stage] || stage.stage));
    box.appendChild(el("div", "stage-value " + stateClass(stage.verdict), stage.available ? (stage.verdict || "—") : "N/A"));
    if (stage.confidence !== null && stage.confidence !== undefined) {
      box.appendChild(el("div", "stage-sub", "confidence " + fmtNum(stage.confidence)));
    }
    if (stage.reason_codes && stage.reason_codes.length) {
      box.appendChild(el("div", "stage-sub", stage.reason_codes.join(", ")));
    }
    container.appendChild(box);
  });
}

// ---------------------------------------------------------------- Overview
function applyOverview(data) {
  updateHeaderBadges(data.system, data.safety);

  document.getElementById("ov-total").textContent = data.production.total;
  document.getElementById("ov-good").textContent = data.production.good + " good";
  document.getElementById("ov-defect").textContent = data.production.defect + " defect";

  document.getElementById("ov-oee").textContent = data.oee.configured ? fmtPct(data.oee.oee) : "N/A";
  document.getElementById("ov-avail").textContent = data.oee.configured ? fmtPct(data.oee.availability) : "—";
  document.getElementById("ov-perf").textContent = data.oee.configured ? fmtPct(data.oee.performance) : "—";
  document.getElementById("ov-qual").textContent = data.oee.configured ? fmtPct(data.oee.quality) : "—";

  const healthPill = document.getElementById("ov-health");
  healthPill.textContent = data.health.health_state;
  healthPill.className = "state-pill " + stateClass(data.health.health_state);
  document.getElementById("ov-health-score").textContent = "score: " + fmtNum(data.health.health_score);

  const safetyPill = document.getElementById("ov-safety");
  safetyPill.textContent = data.safety.safety_level;
  safetyPill.className = "state-pill " + stateClass(data.safety.safety_level);
  document.getElementById("ov-safety-sub").textContent = "machine: " + (data.safety.machine_state || "UNKNOWN");

  renderPipeline(document.getElementById("ov-pipeline"), data.pipeline);

  const evList = document.getElementById("ov-events");
  evList.innerHTML = "";
  data.latest_events.slice(0, 8).forEach((ev) => evList.appendChild(renderEventRow(ev)));

  const sysTable = document.getElementById("ov-system");
  sysTable.innerHTML = "";
  [
    ["Cell ID", data.system.cell_id], ["Cell Device", data.system.cell_device_id],
    ["Edge Device", data.system.edge_device_id], ["Line", data.system.line_id],
    ["Contract Version", data.system.contract_version], ["Sim Clock (ms)", data.system.mono_ms],
  ].forEach(([k, v]) => sysTable.appendChild(kvRow(k, v)));
}

async function refreshOverview() {
  try { applyOverview(await api("/overview")); } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- Production
async function refreshProduction() {
  const filter = document.getElementById("prod-filter").value;
  try {
    const data = await api("/production?filter=" + encodeURIComponent(filter));
    document.getElementById("prod-summary").textContent =
      `total ${data.total} | good ${data.good} | defect ${data.defect} | uncertain ${data.uncertain_count} | passed ${data.passed} | rejected ${data.rejected}`;
    const tbody = document.querySelector("#prod-table tbody");
    tbody.innerHTML = "";
    data.history.forEach((r) => {
      const tr = document.createElement("tr");
      [r.product_id, r.detected_at_mono_ms, r.vision_verdict || "N/A", r.ocr_verdict || "N/A",
       r.outcome, r.controller_action || "pending", r.controller_reason || r.denial_reason || ""]
        .forEach((v) => tr.appendChild(el("td", null, String(v))));
      tbody.appendChild(tr);
    });
  } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- Vision & OCR
async function refreshVisionOcr() {
  try {
    const data = await api("/vision-ocr");
    renderPipeline(document.getElementById("pipeline-detail"), data);
  } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- Safety
async function refreshSafety() {
  try {
    const data = await api("/safety");
    const pill = document.getElementById("safety-level");
    pill.textContent = data.safety_level; pill.className = "state-pill " + stateClass(data.safety_level);
    document.getElementById("safety-machine-state").textContent = data.machine_state || "UNKNOWN";
    document.getElementById("safety-fault-count").textContent = data.active_faults.length;

    const table = document.getElementById("safety-detail");
    table.innerHTML = "";
    [
      ["Runtime State", data.runtime_state], ["Safety Relay Closed", String(data.safety_relay_closed)],
      ["Pusher State", data.pusher_state || "—"], ["Safety Vision Required", String(data.safety_vision_required)],
      ["Queue Length", data.queue_len ?? "—"], ["Active Faults", data.active_faults.join(", ") || "none"],
    ].forEach(([k, v]) => table.appendChild(kvRow(k, v)));
  } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- Machine Health
async function refreshHealth() {
  try {
    const data = await api("/health");
    const pill = document.getElementById("health-state");
    pill.textContent = data.health_state; pill.className = "state-pill " + stateClass(data.health_state);
    document.getElementById("health-score").textContent = fmtNum(data.health_score);
    document.getElementById("health-anomaly-count").textContent = data.active_anomalies.length;

    const sensorsBody = document.querySelector("#health-sensors-table tbody");
    sensorsBody.innerHTML = "";
    data.latest_readings.forEach((r) => {
      const tr = document.createElement("tr");
      [r.sensor_id, r.sensor_type, fmtNum(r.value, 1) + " " + r.unit, r.quality].forEach((v) => tr.appendChild(el("td", null, String(v))));
      sensorsBody.appendChild(tr);
    });

    const anomaliesBody = document.querySelector("#health-anomalies-table tbody");
    anomaliesBody.innerHTML = "";
    data.active_anomalies.forEach((a) => {
      const tr = document.createElement("tr");
      [a.sensor_id, a.severity, a.kind, a.reason].forEach((v) => tr.appendChild(el("td", null, String(v))));
      anomaliesBody.appendChild(tr);
    });
  } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- OEE
async function refreshOee() {
  try {
    const data = await api("/oee");
    document.getElementById("oee-avail").textContent = data.configured ? fmtPct(data.availability) : "N/A";
    document.getElementById("oee-perf").textContent = data.configured ? fmtPct(data.performance) : "N/A";
    document.getElementById("oee-qual").textContent = data.configured ? fmtPct(data.quality) : "N/A";
    document.getElementById("oee-oee").textContent = data.configured ? fmtPct(data.oee) : "N/A";

    const table = document.getElementById("oee-detail");
    table.innerHTML = "";
    [
      ["Total Count", data.total_count ?? "—"], ["Good Count", data.good_count ?? "—"],
      ["Defect Count", data.defect_count ?? "—"], ["Downtime (ms)", data.downtime_ms ?? "—"],
      ["Machine State", data.machine_state || "—"], ["Current Fault", data.current_fault || "none"],
      ["Cycle Count", data.cycle_count ?? "—"], ["Average Cycle (ms)", fmtNum(data.average_cycle_ms, 1)],
    ].forEach(([k, v]) => table.appendChild(kvRow(k, v)));
  } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- Events
function renderEventRow(ev) {
  const row = el("div", "event-row");
  row.appendChild(el("span", "ev-time", ev.mono_ms + "ms"));
  row.appendChild(el("span", "ev-sev sev-" + ev.severity, ev.severity));
  row.appendChild(el("span", "ev-cat", ev.category));
  row.appendChild(el("span", null, ev.message + (ev.product_id ? ` [${ev.product_id}]` : "")));
  return row;
}

async function refreshEvents() {
  try {
    const data = await api("/events?limit=200");
    const filter = document.getElementById("event-filter").value;
    const list = document.getElementById("event-list-full");
    list.innerHTML = "";
    data.filter((ev) => filter === "all" || ev.severity === filter)
        .forEach((ev) => list.appendChild(renderEventRow(ev)));
  } catch (e) { showOffline(e); }
}

// ---------------------------------------------------------------- Diagnostics
async function refreshDiagnostics() {
  try {
    const data = await api("/diagnostics");
    const table = document.getElementById("diag-runtime");
    table.innerHTML = "";
    [
      ["Mode", data.mode], ["Runtime State", data.runtime_state], ["Machine State", data.machine_state || "UNKNOWN"],
      ["Contract Version", data.contract_version], ["Cell ID", data.cell_id],
      ["Cell Device", data.cell_device_id], ["Edge Device", data.edge_device_id],
      ["Active Fault Codes", data.active_fault_codes.join(", ") || "none"],
    ].forEach(([k, v]) => table.appendChild(kvRow(k, v)));

    const body = document.querySelector("#diag-subsystems tbody");
    body.innerHTML = "";
    const all = new Set(["vision", "ocr", "health", "frame_source"]);
    data.degraded_subsystems.forEach((s) => all.add(s));
    all.forEach((name) => {
      const degraded = data.degraded_subsystems.includes(name);
      const tr = document.createElement("tr");
      tr.appendChild(el("td", null, name));
      tr.appendChild(el("td", degraded ? "sev-WARNING" : "sev-INFO", degraded ? "DEGRADED" : "OK"));
      tr.appendChild(el("td", null, degraded ? (data.degraded_reasons[name] || "") : ""));
      body.appendChild(tr);
    });
  } catch (e) { showOffline(e); }
}

function kvRow(k, v) {
  const tr = document.createElement("tr");
  tr.appendChild(el("td", null, k));
  tr.appendChild(el("td", null, String(v)));
  return tr;
}

function showOffline(err) {
  console.error(err);
  document.getElementById("control-feedback").textContent = "SYSTEM OFFLINE / DATA UNAVAILABLE: " + err.message;
}

// ---------------------------------------------------------------- controls
function setupControls() {
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const result = await post("/control/" + btn.dataset.action);
        document.getElementById("control-feedback").textContent = result.message;
        loadActiveTab();
      } catch (e) {
        showOffline(e);
      } finally {
        btn.disabled = false;
      }
    });
  });

  document.getElementById("run-full-demo").addEventListener("click", async () => {
    const btn = document.getElementById("run-full-demo");
    btn.disabled = true;
    document.getElementById("control-feedback").textContent = "Running full demo…";
    try {
      const summary = await post("/control/demo/full");
      showDemoSummary(summary);
      loadActiveTab();
    } catch (e) {
      showOffline(e);
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById("close-demo-summary").addEventListener("click", () => {
    document.getElementById("demo-summary-modal").classList.add("hidden");
  });

  document.getElementById("prod-filter").addEventListener("change", refreshProduction);
  document.getElementById("event-filter").addEventListener("change", refreshEvents);
}

function showDemoSummary(summary) {
  const table = document.getElementById("demo-summary-table");
  table.innerHTML = "";
  [
    ["Products Processed", summary.products_processed], ["Good", summary.good], ["Defect", summary.defect],
    ["Rejected", summary.rejected], ["OEE", summary.oee.configured ? fmtPct(summary.oee.oee) : "N/A"],
    ["Health State", summary.health_state],
    ["Safety Events", summary.safety_events.join("; ") || "none"],
    ["Faults", summary.faults.join("; ") || "none"],
    ["Final Machine State", summary.final_machine_state || "UNKNOWN"],
    ["Final Runtime State", summary.final_runtime_state],
  ].forEach(([k, v]) => table.appendChild(kvRow(k, v)));
  document.getElementById("demo-summary-modal").classList.remove("hidden");
}

// ---------------------------------------------------------------- WebSocket live updates
function connectWebSocket() {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${window.location.host}/ws/live`);
  const indicator = document.getElementById("ws-indicator");

  ws.onopen = () => indicator.classList.add("connected");
  ws.onclose = () => {
    indicator.classList.remove("connected");
    setTimeout(connectWebSocket, 2000); // reconnect -- backend restarts should not strand the UI
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (msg) => {
    try {
      const data = JSON.parse(msg.data);
      if (activeTab === "overview") applyOverview(data);
      else updateHeaderBadges(data.system, data.safety);
    } catch (e) { console.error(e); }
  };
}

// ---------------------------------------------------------------- boot
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupControls();
  connectWebSocket();
  refreshOverview();
});
