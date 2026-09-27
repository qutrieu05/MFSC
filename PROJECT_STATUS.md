# Project Status — MSFC

**Cập nhật:** 2026-09-19 (lần 12 — Official Web Dashboard DONE) · **Trạng thái:** Phase 0-6 **SOFTWARE COMPLETE** + **OFFICIAL WEB DASHBOARD COMPLETE**, các mục hardware/vật lý/OCR/OEE/health/predictive-maintenance thật vẫn **PENDING** — ⏳ **STOP theo yêu cầu PO, chờ duyệt bước tiếp theo**

> 🔔 **Bối cảnh:** Sau khi Phase 6 (Edge AI Platform / Final Software Integration) DONE, PO chỉ thị xây **"S1 — OFFICIAL WEB DASHBOARD"**: giao diện web chính thức (không phải demo dùng rồi bỏ) hiển thị Vision/OCR/Decision/Safety/OEE/Machine Health/Event Log/Diagnostics, có control demo, hoàn toàn bằng software/mô phỏng — **không phải Phase 7** (PO chỉ thị rõ "Do NOT create Phase 7"), không mua hardware, không cài Mosquitto/ESP-IDF, không phá vỡ an toàn P2/P6. Báo cáo này là kết quả của vòng đó; Phase 0-6's kết quả giữ nguyên không đổi.

## 0. Trạng thái theo 11 mức + Dashboard (chuẩn hóa theo yêu cầu PO)

| Mức | Trạng thái | Bằng chứng |
|---|---|---|
| **SOFTWARE LOGIC** | ✅ **COMPLETE** | Phase 1-5 (không đổi) + Phase 6 (`msfc.services`) + Official Dashboard (`msfc.dashboard`) |
| **OFFICIAL WEB DASHBOARD** | ✅ **COMPLETE** | FastAPI backend + HTML/CSS/JS frontend, 8/8 mục thông tin, demo controls + full demo, 51 test mới, xác minh trực quan qua trình duyệt thật — xem [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md) |
| **HOST VALIDATION** | ✅ **COMPLETE** | Python: **859 passed/1 skipped** (808 + 51 Dashboard mới). Firmware: 262/262 check PASS (không đổi, không cần sửa). Không regression |
| **ESP32 TARGET BUILD** | ⏳ **PENDING** | Không đổi — thiếu ESP-IDF SDK |
| **REAL HARDWARE VALIDATION** | ⏳ **PENDING** | HARDWARE = NONE; chưa qua P1.9 (procurement, chưa duyệt) |
| **REAL EDGE DEPLOYMENT** | ⏳ **PENDING** | Chưa deploy lên bất kỳ thiết bị Edge thật nào (Jetson/ESP32-S3/khác) — chỉ chạy trên máy phát triển (host). Yêu cầu để triển khai: xem PHASE6_COMPLETION_REPORT.md mục "Edge Deployment Readiness" |
| **REAL AI DATASET VALIDATION** | ⏳ **PENDING** | Không đổi từ Phase 1 — dataset vẫn tổng hợp (0đ), chưa có ảnh sản phẩm thật |
| **REAL OCR VALIDATION** | ⏳ **PENDING** | Không đổi từ Phase 3 — chưa cài OCR engine thật, chưa thử ảnh nhãn thật |
| **REAL OEE VALIDATION** | ⏳ **PENDING** | Không đổi từ Phase 4 — chưa chạy trên dây chuyền thật |
| **REAL MACHINE-HEALTH VALIDATION** | ⏳ **PENDING** | Không đổi từ Phase 5 — chỉ chạy trên sự kiện cảm biến tổng hợp/mock |
| **REAL PREDICTIVE-MAINTENANCE VALIDATION** | ⏳ **PENDING** | Không đổi từ Phase 5 — `RuleBasedReferenceModel` không phải mô hình đã huấn luyện, `validated_on_real_data` luôn `False` |
| **PHYSICAL E-STOP VALIDATION** | ⏳ **PENDING** | Không đổi từ Phase 1/2 — chưa có nút E-stop vật lý |

**Các mục PENDING không phải là thất bại** — đều bị chặn bởi thứ bên ngoài phạm vi software (SDK chưa cài, hardware chưa mua, chưa có máy/cảm biến/nút bấm thật, chưa có dữ liệu suy giảm thật để huấn luyện/hiệu chỉnh).

**⚠️ Nhắc lại theo đúng chỉ thị PO:** Phase 6 chứng minh **kiến trúc orchestration/runtime hoạt động đúng, độc lập phần cứng, và có thể thay thế sang phần cứng thật mà không sửa `msfc.services`** — **không phải** bằng chứng vận hành thật trên máy/cảm biến/camera/mạng MQTT thật. `msfc.services` **không có khả năng** ghi đè an toàn/interlock của P2 — không chỉ vì kỷ luật lập trình mà vì luật layer (`test_layer_dependencies.py`) không cho package này import `msfc.sim`/firmware trực tiếp; nó chỉ nói chuyện với Cell Controller qua `MessageBus`.

---

## 1. Tóm tắt

| Hạng mục | Trạng thái |
|---|---|
| Repository | ✅ `D:\project\mini-smart-factory-cell`, git `main`, **chưa có commit** (PO quyết định thời điểm) |
| Tài liệu nền tảng (Phase 0) | ✅ Charter, Requirements, Architecture, Safety Concept, MQTT contract, 13 ADR, QA plan, Coding standards, Git strategy, Risk register, Roadmap |
| **Software Phase 1 (P1.1–P1.8)** | ✅ **8/9 phần DONE** — domain, contract runtime, vision (camera sim + AI baseline cổ điển + CNN/ONNX scaffold), decision engine, firmware core_logic (host-testable), ESP32 simulator/mock, pipeline MVP end-to-end |
| P1.5 (build thật cho chip ESP32) | 🟡 **core_logic host-testable DONE** (131/131 test); **build `idf.py` cho chip vẫn BLOCKED** — thiếu ESP-IDF SDK (không phải thiếu code hay gcc) |
| **Software Phase 2 (Safety & Interlock)** | ✅ **DONE** — `safety_interlock.h/.c`: safety state machine, software E-STOP, 8-condition interlock matrix, comm-loss/watchdog, invalid-command handling, deterministic recovery, 12-scenario simulator (262/262 firmware check PASS) |
| **Software Phase 3 (OCR/Expiry/Label)** | ✅ **DONE** — `msfc.ocr`: domain model, engine abstraction, preprocessing, normalize, date extraction (5 định dạng), date/label validation, GOOD/DEFECT/UNCERTAIN classification, tích hợp `DecisionEngine` không sửa, 12-scenario fixtures (103 test mới) |
| **Software Phase 4 (OEE/Machine Monitoring)** | ✅ **DONE** — `msfc.analytics`: OEE domain model, machine event model (tái dùng `MachineState`/`Counters` P1), Availability/Performance/Quality/OEE, production session, cycle-time monitoring, machine monitoring layer, 10-scenario simulation, in-memory repository (99 test mới) |
| **Software Phase 5 (Machine Health/Anomaly/Predictive Maintenance)** | ✅ **DONE** — `msfc.analytics` (mở rộng): sensor abstraction, data quality, feature extraction, baseline, anomaly detection, health score, health monitor, predictive-model abstraction (KHÔNG train gì), 15-scenario simulation (143 test mới) |
| **Software Phase 6 (Edge AI Platform / Final Software Integration)** | ✅ **DONE — FINAL SOFTWARE PHASE** — `msfc.services` (mới, L6 đã khai báo sẵn từ Phase 0): platform domain model, pipeline orchestration, Cell Runtime, safety gate (courtesy-only), event codec, timing model, health/OEE bridge; 20 kịch bản + full-stack integration (96 test mới, 808/808 PASS Python) |
| Contract | ✅ 25 topic + 23 JSON schema; **runtime đã chạy thật** qua `InMemoryBus` và `MqttBus` (client giả); `msfc.services` publish/consume verdict/heartbeat/state/fault/product/ack qua đúng registry — OEE/health vẫn chưa publish (D-060) |
| Phần cứng | ❌ **HARDWARE = NONE.** Chưa mua gì. BOM 60 hạng mục + 6 wave chờ duyệt |
| AI / dataset (vision) | 🟡 Baseline cổ điển **và** CNN/ONNX scaffold đều hoạt động đúng kỹ thuật; dataset vẫn là **tổng hợp** (0đ), chưa có ảnh thật; **cả hai đều có cùng giới hạn thật đã đo được** — xem mục 1c |
| OCR | 🟡 Pipeline hoạt động đúng kỹ thuật (12/12 kịch bản tổng hợp PASS); **chưa validate trên ảnh thật, chưa cài OCR engine thật** — xem mục 1e |
| OEE / machine monitoring | 🟡 Pipeline hoạt động đúng kỹ thuật (10/10 kịch bản + 15 fixture PASS); **chưa validate trên dây chuyền thật** — xem mục 1f |
| Machine health / predictive maintenance | 🟡 Pipeline hoạt động đúng kỹ thuật (15/15 kịch bản PASS); **KHÔNG mô hình nào đã huấn luyện, không claim độ chính xác thật** — xem mục 1g |
| Edge AI Cell Platform (orchestration/runtime) | 🟡 Pipeline hoạt động đúng kỹ thuật (20/20 kịch bản + full-stack integration PASS); **chưa deploy lên Edge device thật, chưa chạy với phần cứng thật** — xem mục 1h |
| **Official Web Dashboard** | ✅ **DONE** — `msfc.dashboard` (FastAPI + HTML/CSS/JS thuần): 8 mục thông tin, demo controls, full demo 14 bước, xác minh trực quan qua trình duyệt thật (51 test mới) — xem mục 1i |

## 1a. Kết quả test (bằng chứng chính)

**Python:** `cd edge && python -m pytest` → **859 passed, 1 skipped, exit code 0** (808 + 51 Dashboard mới; không có code P1/P2/P3/P4/P5 nào bị sửa; Phase 6 chỉ mở rộng bồi thêm — xem D-066)
**Firmware:** `bash firmware/cell_controller/test_host/build_and_run.sh` → **262 checks, 0 failed** (không đổi từ Phase 2, không cần sửa cho Phase 4/5/6/Dashboard), build `-Wall -Wextra -Werror` sạch

| Mức | Số test | File |
|---|---:|---|
| Unit — nền tảng Phase 0 (config, logging, layer rules) | 30 | `test_config.py`, `test_logging_setup.py`, `test_layer_dependencies.py` |
| Unit — contract tĩnh (Phase 0) | 13 | `tests/contract/test_contract_files.py` |
| Unit — domain (P1.1) | 80 | `test_domain_*.py` (4 file) |
| Unit — contract runtime (P1.7) | 45 | `test_contracts_*.py` (3 file) |
| Unit — comm/MQTT (P1.7) | 53 | `test_comm_*.py` (5 file) |
| Unit — vision (P1.2 + P1.3 cổ điển) | 65 | `test_vision_*.py` (5 file) |
| Unit — vision (P1.3 CNN/ONNX, mới) | 17 | `test_vision_training_smoke.py`, `test_vision_onnx_inference_smoke.py` |
| Unit — decision (P1.4) | 20 | `test_decision_engine.py` |
| Unit — simulator (P1.6) | 38 | `test_sim_cell_controller.py` |
| Integration — pipeline MVP end-to-end | 6 | `tests/integration/test_full_pipeline_mvp.py` |
| Integration — broker thật | 1 (**skip**, chưa cài Mosquitto — B4) | `tests/integration/test_mqtt_bus_real_broker.py` |
| Unit — OCR (P3.1–P3.8) | 98 | `test_ocr_*.py` (8 file) |
| Integration — OCR × DecisionEngine (P3.9) | 5 | `tests/integration/test_ocr_decision_integration.py` |
| Unit — OEE/analytics (P4.1–P4.15) | 98 | `test_analytics_*.py` (7 file) |
| Integration — analytics × domain thật (P4.16) | 1 | `tests/integration/test_analytics_domain_integration.py` |
| Unit — machine health (P5.1–P5.15, mới) | 141 | `test_analytics_health_*.py` + `test_analytics_sensors/quality/features/baseline/anomaly/predictive/evaluation.py` (14 file) |
| Integration — health × P4 thật (P5.16/P5.17, mới) | 2 | `tests/integration/test_analytics_health_p4_integration.py` |
| Unit — Edge AI Platform (P6.1–P6.13, mới) | 74 | `test_services_*.py` (9 file) |
| Integration — 20 kịch bản end-to-end (P6.14, mới) | 20 | `tests/integration/test_services_scenarios.py` |
| Integration — full-stack success/failure (P6.16, mới) | 2 | `tests/integration/test_services_full_stack_integration.py` |
| Unit — mở rộng bồi thêm CellRuntime cho Dashboard, mới | 7 | `test_services_runtime_observability.py` |
| Unit — Dashboard DTO/session, mới | 22 | `test_dashboard_dtos.py` (11), `test_dashboard_session.py` (11) |
| Integration — Dashboard API (20 mục yêu cầu + WebSocket + OpenAPI), mới | 22 | `tests/integration/test_dashboard_api.py` |

**Dependency mới duy nhất kể từ Phase 0 (Official Dashboard, D-064):** `fastapi`, `uvicorn` (runtime) + `httpx` (dev/test, cho `starlette.testclient`) — khai báo trong `edge/pyproject.toml`. `msfc.analytics`/`msfc.services` (Phase 4-6) vẫn không cần dependency runtime mới.

## 1b. Phase 1 software-first — kết quả từng phần

| # | Phần | Trạng thái | Chi tiết |
|---|---|---|---|
| P1.1 | Software Architecture (`msfc.domain`) | ✅ **DONE** | [TASKS.md](TASKS.md#chi-tiết-p11--software-architecture-done-2026-09-18) |
| P1.2 | Camera Simulation / Test Input | ✅ **DONE** | `msfc.vision`: 4 `FrameSource` (synthetic, folder — test bằng PNG thật, video — test bằng MP4 thật, USB — test đường lỗi) |
| P1.3 | AI Baseline | ✅ **DONE (cổ điển + CNN/ONNX)** | `ClassicCvBaseline` + `postprocess` + `evaluate` + `training.py`/`onnx_backend.py`; **giới hạn thật đã đo ở cả hai** — mục 1c |
| P1.4 | Decision Engine | ✅ **DONE** | [TASKS.md](TASKS.md#chi-tiết-p14--decision-engine-done-2026-09-18) |
| P1.5 | Firmware `core_logic` (C99, host-testable) | ✅ **DONE** (131/131 test) | `cell_sm`+`fault_manager`+`safety_supervisor`+`cmd_handler`+`watchdog`+`logger`+HAL boundary — xem TASKS.md |
| P1.5b | Build thật cho chip ESP32 (`idf.py build`) | 🚫 **Blocked** | Thiếu ESP-IDF SDK; `gcc` đã có (D-036), không còn là blocker |
| P1.6 | Firmware Simulator / Mock ("ESP32 mock") | ✅ **DONE** | [TASKS.md](TASKS.md#chi-tiết-p16--cell-controller-simulator-esp32-mock-done-2026-09-18) |
| P1.7 | Communication Contract runtime | ✅ **DONE** | `msfc.contracts` + `msfc.comm`; `MqttBus` test bằng client giả, không cần broker thật |
| — | **Pipeline MVP end-to-end** (nối P1.2+P1.4+P1.6+P1.7) | ✅ **DONE** | [TASKS.md](TASKS.md#chi-tiết-pipeline-mvp-end-to-end-p12p14p16p17-nối-lại-done-2026-09-18) |

**Vòng khép kín đã chứng minh chạy được (bằng dữ liệu tổng hợp), đúng sơ đồ PO yêu cầu:**
`Camera/Test Input → Vision/AI → Decision Engine → Command → ESP32 Mock → Motor/Servo Mock → GOOD/DEFECT result`

## 1c. Phát hiện quan trọng cần PO biết (không che giấu)

1. **`ClassicCvBaseline` gần như không phân biệt được GOOD/DEFECT trên dữ liệu tổng hợp mặc định.** Đo thực nghiệm: điểm khác biệt trung bình so với ảnh mẫu ≈ 21,9 cho sản phẩm tốt, 21,9–23,2 cho sản phẩm lỗi — gần như trùng nhau. Nguyên nhân: lấy trung bình nhiều ảnh có vị trí lệch ngẫu nhiên làm mờ ảnh mẫu, cộng nhiễu nền lớn hơn tín hiệu lỗi thật. **Đây là giới hạn thật của thuật toán, phát hiện được chính nhờ việc nối toàn bộ pipeline lại — không phải lỗi nối dây.** Đã ghi [RISK_REGISTER.md](docs/RISK_REGISTER.md) mục R-28. Không ảnh hưởng tới các test wiring (dùng một engine giả biết trước nhãn để tách bạch hai vấn đề), nhưng **cần xử lý trước khi tin dùng baseline này với dataset thật ở P1.11** (cố định vị trí sản phẩm bằng cơ khí, và/hoặc cải tiến thuật toán, và/hoặc chuyển sang CNN).
2. **CNN/ONNX training scaffold (P1.3) đã hoàn thành lượt này — và có cùng giới hạn với mục 1.** `msfc.vision.training` (dataset→CNN nhỏ→checkpoint) + `msfc.vision.onnx_backend` (`OnnxInferenceEngine`, cắm thẳng vào `postprocess()`/`DecisionEngine` không sửa gì) chạy đúng end-to-end — 17 test mới PASS, cross-check ONNX Runtime khớp PyTorch (<1e-4). Nhưng khi huấn luyện thật (2 epoch, smoke test, dataset tổng hợp 36 ảnh): **`TinyCapCNN` cũng dự đoán mọi ảnh là GOOD** — accuracy=0.5, F1(DEFECT)=0.0. Nguyên nhân giống R-28 (dataset tổng hợp quá nhỏ/khó) cộng với việc cố tình train rất ngắn theo đúng chỉ thị PO ("không train lâu, không over-optimize"). Đã ghi nhận trung thực, **không tinh chỉnh gì để "qua" kết quả** — xem D-035, [ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/model_card.md](ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/model_card.md).
3. **`torch.cuda.is_available()` = False** dù máy có RTX 3050 (driver 610.78). Bản `torch` hiện tại có vẻ không có CUDA. Không chặn lượt này (P1.3 chỉ chạy smoke-test rất nhỏ trên CPU, ~25s); cần xử lý trước P1.11 (huấn luyện thật). Ghi ở R-27.
4. **P1.5 tách làm hai phần lượt này.** Kiểm tra môi trường phát hiện `gcc` **thật ra đã có sẵn** (MSYS2 UCRT64, không nằm trong PATH — D-036), nên đã implement + build + test phần `core_logic` C99 không phụ thuộc ESP-IDF: 131/131 check PASS. Nhưng **build thật cho chip ESP32** (`idf.py build`) vẫn BLOCKED — không tìm thấy ESP-IDF SDK ở đâu trên máy. Không giả vờ đã build cho chip. Command cài ESP-IDF (PO tự chạy): xem mục "Blocker" bên dưới.
5. **Mosquitto vẫn MISSING**, xác nhận lại bằng kiểm tra trực tiếp (không chỉ dựa vào `check_env.py`) — không có ở Program Files, PATH, hay MSYS2. Không tự cài (cần tải file từ internet — ngoài thẩm quyền tự động của Claude Inc); 1 test tích hợp broker thật tiếp tục tự SKIP trung thực. Command cài đặt: xem mục "Blocker".

## 1d. Phase 2 — Safety & Interlock (2026-09-18)

**SOFTWARE-ONLY.** Toàn bộ mục này chạy trên host qua `hal_host_mock`, không phần cứng. **SOFTWARE E-STOP SIMULATION != PHYSICAL E-STOP VALIDATION** — kênh E-stop vật lý (NC contact, SAF-01/IF-HW-01) chưa tồn tại, chưa đo được, và không có tuyên bố nào ở đây thay thế việc đó.

| # | Hạng mục | Trạng thái | Chi tiết |
|---|---|---|---|
| P2.1 | Safety state machine (SAFE_IDLE/READY/RUNNING/FAULT/ESTOP/RECOVERY) | ✅ DONE | View suy ra từ `cell_sm` (P1) — D-038 |
| P2.2 | Software E-STOP event | ✅ DONE | Chặn lệnh mới + actuator; cần RESET + confirm để phục hồi |
| P2.3 | Interlock matrix (8 điều kiện) | ✅ DONE | ESTOP, safety fault, comm loss, invalid command, motor fault, sensor fault, not ready, recovery not completed |
| P2.4 | Safe state | ✅ DONE | Tái dùng `safety_supervisor.c` (P1), không sửa |
| P2.5 | Communication loss | ✅ DONE | normal/timeout/disconnect/recovery |
| P2.6 | Watchdog integration | ✅ DONE | Tái dùng `watchdog.c` (P1) — D-039 giải thích vì sao không dùng `watchdog_check()` trực tiếp |
| P2.7 | Invalid/malformed command | ✅ DONE | unknown command, invalid param, lệnh khi ESTOP/FAULT, lệnh trước READY, invalid transition |
| P2.8 | Deterministic fault recovery | ✅ DONE | Không tự động phục hồi — `confirm_recovery()` re-check toàn bộ điều kiện |
| P2.9 | Software safety simulator | ✅ DONE | Đúng 12 kịch bản PO liệt kê, `test_safety_scenarios.c` |

**File mới (100% cộng thêm, không sửa P1):** `firmware/cell_controller/components/core_logic/safety_interlock.h/.c` + 4 file test host. Chi tiết đầy đủ: [TASKS.md](TASKS.md#phase-2--software-only-safety--interlock-2026-09-18).

## 1e. Phase 3 — OCR / Expiry / Label Verification (2026-09-18)

**SOFTWARE-ONLY.** Toàn bộ ảnh là tổng hợp (0đ), không camera thật, không dịch vụ OCR thật. **Không claim độ chính xác OCR trên ảnh/sản phẩm thật.**

| # | Hạng mục | Trạng thái | Chi tiết |
|---|---|---|---|
| P3.1 | OCR domain model | ✅ DONE | `BoundingBox`, `OcrOutput`, `OcrReasonCode` (đúng 6 mã FR-OCR-04), `OcrValidationResult` |
| P3.2 | OCR engine abstraction | ✅ DONE | `MockOcrEngine`, `FixtureOcrEngine` — cùng interface cho OCR thật sau này |
| P3.3 | Preprocessing | ✅ DONE | grayscale/resize/contrast/denoise/threshold/crop/deskew, module hóa |
| P3.4/P3.5 | Normalize + date extraction | ✅ DONE | 5 định dạng PO liệt kê; sửa nhầm lẫn ký tự chỉ trong phạm vi chuỗi dạng ngày |
| P3.6/P3.7 | Date + label validation | ✅ DONE | Cấu hình được (`LabelValidationConfig`), không hard-code sản phẩm |
| P3.8 | Classification | ✅ DONE | GOOD/DEFECT/UNCERTAIN — không ép ambiguous/low-confidence thành GOOD/DEFECT |
| P3.9 | Decision integration | ✅ DONE | `to_inspection_result()` → `DecisionEngine.decide()` **không sửa gì** |
| P3.10/P3.11 | Fixtures + simulation | ✅ DONE | Đúng 12 kịch bản PO liệt kê, 12/12 PASS |
| P3.12 | Error handling | ✅ DONE | Engine lỗi → UNREADABLE xác định; config sai → `OcrError` |

**File mới (không sửa file P1/P2 nào ngoài thêm `OcrError` vào `msfc/core/errors.py`, theo đúng pattern đã có):** `edge/src/msfc/ocr/` (8 module) + 9 file test. 103 test mới. Chi tiết đầy đủ: [TASKS.md](TASKS.md#phase-3--software-only-ocr--expiry--label-verification-2026-09-18).

## 1f. Phase 4 — OEE / Machine Monitoring (2026-09-18)

**SOFTWARE-ONLY.** Toàn bộ sự kiện là mô phỏng/tổng hợp, không cảm biến/ESP32/PLC/camera/MQTT broker thật. **OEE chỉ quan sát — không bao giờ ghi đè an toàn/interlock của P2** (bảo đảm bằng luật layer, không chỉ kỷ luật code).

| # | Hạng mục | Trạng thái | Chi tiết |
|---|---|---|---|
| P4.1 | OEE domain model | ✅ DONE | `OeeResult`, `DowntimeInterval`, `CycleStatistics`, `MachineStatus` |
| P4.2 | Machine state model | ✅ DONE | Tái dùng `MachineState` (P1) — **không** tạo enum mới |
| P4.3 | Machine event model | ✅ DONE | `MachineEvent`, factory function từ đúng event P1 (`StateChangedEvent`...) |
| P4.4 | Downtime model | ✅ DONE | `DowntimeCategory`, quy tắc tường minh có thể override (`state_category`) |
| P4.5–P4.8 | Availability/Performance/Quality/OEE | ✅ DONE | Không clamp nội bộ (D-048); raise lỗi rõ ràng cho input không hợp lệ |
| P4.9 | Production session | ✅ DONE | `ProductionSession` — không hard-code ca làm việc thật |
| P4.10 | Cycle-time monitoring | ✅ DONE | min/max/average/slow-cycle/incomplete-cycle |
| P4.11 | Machine monitoring layer | ✅ DONE | `MachineMonitor` — độc lập phần cứng, cùng interface cho ESP32 thật sau này |
| P4.12 | Fault/downtime reasoning | ✅ DONE | Không thể import `msfc.sim`/`msfc.decision` (luật layer) — bảo đảm kiến trúc |
| P4.13/P4.14 | Simulation + fixtures | ✅ DONE | Đúng 10 kịch bản + 15 fixture PO liệt kê |
| P4.17 | Storage abstraction | ✅ DONE | Interface + in-memory only, không DB thật |

**File mới (không sửa file P1/P2/P3 nào ngoài thêm `OeeError` vào `msfc/core/errors.py`, theo đúng pattern đã có):** `edge/src/msfc/analytics/` (8 module) + 8 file test. 99 test mới. Chi tiết đầy đủ + các quyết định OEE quan trọng (D-045..D-050): [TASKS.md](TASKS.md#phase-4--software-only-oee--machine-monitoring-2026-09-18).

## 1g. Phase 5 — Machine Health / Anomaly Detection / Predictive Maintenance (2026-09-18)

**SOFTWARE-ONLY. KHÔNG claim độ chính xác predictive maintenance thật.** Toàn bộ cảm biến là mô phỏng/mock (`FixedSequenceSensorSource`), không cảm biến/máy/MQTT broker thật. **Machine health chỉ quan sát/chẩn đoán — không bao giờ ghi đè an toàn/interlock của P2** (bảo đảm bằng luật layer).

| # | Hạng mục | Trạng thái | Chi tiết |
|---|---|---|---|
| P5.1 | Machine health domain model | ✅ DONE | `SensorMeasurement`, `FeatureSet`, `AnomalyResult`, `HealthScore`, `HealthState` (5 giá trị, D-051) |
| P5.2 | Sensor abstraction | ✅ DONE | `SensorSource` Protocol, `FixedSequenceSensorSource` — cùng interface cho cảm biến thật sau này |
| P5.3 | Sensor data quality | ✅ DONE | 8 loại quality tường minh (MISSING/INVALID/STALE/FUTURE_TIMESTAMP/DUPLICATE/INVALID_UNIT/UNAVAILABLE/OK) |
| P5.4 | Feature extraction | ✅ DONE | min/max/mean/median/std/variance/range/rate_of_change/moving_average/RMS |
| P5.5 | Baseline model | ✅ DONE | `HealthBaseline` — cấu hình được, không hard-code máy thật |
| P5.6/P5.8 | Anomaly detection + severity | ✅ DONE | threshold/deviation/trend/sensor-quality; kết hợp = **luôn lấy severity cao nhất** |
| P5.7 | Health score | ✅ DONE | 0.0–1.0, công thức tài liệu hóa nhưng **tùy ý** (D-052), không claim sức khỏe vật lý thật |
| P5.9/P5.10 | Health event + monitor | ✅ DONE | `MachineHealthMonitor` — độc lập phần cứng |
| P5.11/P5.12 | Predictive model abstraction | ✅ DONE | `RuleBasedReferenceModel` — **KHÔNG train gì**, `validated_on_real_data` luôn `False` |
| P5.13/P5.14 | Simulation + fixtures | ✅ DONE | Đúng 15 kịch bản PO liệt kê, 15/15 PASS |
| P5.16/P5.17 | Tích hợp P4 | ✅ DONE | Chỉ MỘT cầu nối tùy chọn (CRITICAL → fault marker), không tự động hóa WARNING/ANOMALY (D-054) |
| P5.19 | Storage abstraction | ✅ DONE | Interface + in-memory only |
| P5.21 | Evaluation framework | ✅ DONE | precision/recall/F1/FPR/FNR/MAE/RMSE/detection delay — chỉ khung, không claim số liệu thật |

**File mới (không sửa file P1/P2/P3/P4 nào ngoài thêm `HealthError` vào `msfc/core/errors.py`, theo đúng pattern đã có):** 12 module mới trong `edge/src/msfc/analytics/` + 14 file test unit + 1 file integration. 143 test mới. **2 bug thiết kế thật bắt được trước khi viết test đầy đủ** (D-055 spike bị pha loãng bởi trung bình, D-056 ngưỡng dùng chung không hợp lý giữa các cảm biến khác thang đo). Chi tiết đầy đủ + các quyết định quan trọng (D-051..D-056): [TASKS.md](TASKS.md#phase-5--software-only-machine-health--anomaly-detection--predictive-maintenance-2026-09-18).

## 1h. Phase 6 — Edge AI Platform / Final Software Integration (2026-09-19)

**SOFTWARE-ONLY, FINAL SOFTWARE PHASE.** `msfc.services` (L6) — khai báo sẵn từ Phase 0, hoãn tới lượt này — hợp nhất `vision`/`ocr`/`decision`/`analytics` thành một orchestrator độc lập phần cứng duy nhất (`CellRuntime`), nói chuyện với Cell Controller (thật hoặc `msfc.sim`) **chỉ qua** `MessageBus`+`ContractRegistry` — không bao giờ import `msfc.sim` (luật layer chặn, không chỉ kỷ luật).

| # | Hạng mục | Trạng thái | Chi tiết |
|---|---|---|---|
| P6.1 | Platform domain model | ✅ DONE | `CellIdentity`, `RuntimeState`, `PipelineOutcome`, `ProductCycleTrace`, `SubsystemHealth`, `CellSnapshot` — tái dùng tối đa `MachineState`/`InspectionResult`/`DecisionRecord`/`MachineHealthSnapshot`/`MachineStatus` có sẵn |
| P6.2/P6.3 | Pipeline orchestration + Cell Runtime | ✅ DONE | `CellRuntime`: subscribe state/fault/product/ack, chạy vision→OCR→decision, publish verdict/heartbeat |
| P6.4 | Safety authority | ✅ DONE | `safety_gate` chỉ là kiểm tra lịch sự (defense-in-depth) — Cell Controller vẫn 100% cơ quan an toàn duy nhất (D-059) |
| P6.5 | End-to-end decision flow | ✅ DONE | Precedence tái dùng luật đã có: safety gate → vision/OCR fail-closed → DecisionEngine (không luật mới) |
| P6.6/P6.7/P6.8 | Event/contract unification, MQTT boundary, traceable data flow | ✅ DONE | Codec giải mã phía nhận (mirror của `msfc.sim.codec`); `InMemoryBus`/`MqttBus` có sẵn tái dùng; `product_id` là correlation id |
| P6.9 | Runtime modes | ✅ DONE | `RuntimeState` (INIT/READY/RUNNING/DEGRADED/FAULT/SAFE_STOP/SHUTDOWN) — khái niệm mới, tách bạch `MachineState` |
| P6.10/P6.11 | Subsystem failure + degraded mode | ✅ DONE | Vision/OCR/sensor lỗi → 1 kênh thiếu, không bao giờ verdict giả; health CRITICAL không chặn sản xuất (D-054 giữ nguyên) |
| P6.12/P6.13 | Timing model + error boundaries | ✅ DONE | `StageTimer`/`TimingStats` (HOST/SIMULATION ONLY, ghi rõ); `DedupeFilter` tái dùng cho duplicate event |
| P6.14/P6.15/P6.16 | 20 kịch bản + 26 fixture + full integration | ✅ DONE | 20/20 kịch bản PASS, full-stack success+failure path PASS (đối với `SimCellController` thật) |
| P6.17/P6.18 | Regression + layer test | ✅ DONE | 808 passed/1 skipped (712+96, 0 hỏng); layer test PASS không cần sửa |
| P6.19 | Hardware replacement demonstrated | ✅ DONE (kiến trúc) | FrameSource/Transport/Controller/SensorSource đều thay được qua interface, chưa có phần cứng thật để chứng minh runtime |
| P6.20/P6.21 | Model boundary + Edge deployment readiness | ✅ DONE | Không đổi từ P1 (đã tách sẵn); readiness ghi ở PHASE6_COMPLETION_REPORT.md |
| P6.22/P6.23 | Observability + storage boundary | ✅ DONE | Logging có sẵn tái dùng; không DB sản xuất, OEE/health vẫn in-memory |
| P6.24 | Final contract review | ✅ DONE | D-051/Q-19, D-048/Q-18 **giữ nguyên chưa giải quyết**, không âm thầm chọn (D-060) |

**File mới (không sửa `msfc.vision`/`msfc.ocr`/`msfc.decision`/`msfc.analytics`/`msfc.sim`/firmware — chỉ thêm `OrchestrationError` vào `msfc/core/errors.py`):** 9 module mới trong `edge/src/msfc/services/` + 9 file test unit + 2 file integration. **96 test mới.** **2 vấn đề thật phát hiện và sửa trước khi chốt** (D-058 gộp nhầm 2 device_id khác nhau thành một trường; D-061 thiết kế test ban đầu bỏ qua cổng vào công khai của runtime). Chi tiết đầy đủ + quyết định (D-057..D-063): [TASKS.md](TASKS.md#phase-6--edge-ai-platform--final-software-integration-2026-09-19), [PHASE6_COMPLETION_REPORT.md](PHASE6_COMPLETION_REPORT.md).

## 1i. Official Web Dashboard (2026-09-19)

**SOFTWARE SIMULATION, không phải Phase 7.** `msfc.dashboard` (L8, khai báo sẵn từ Phase 0, ADR-0012) — FastAPI backend (`DemoSession` sở hữu một `SimCellController`+`CellRuntime`+`InMemoryBus` thật) + frontend HTML/CSS/JS thuần. Dashboard không có logic nghiệp vụ riêng — mọi số liệu đọc thẳng từ `msfc.services`/`msfc.analytics`/`msfc.sim` đã kiểm chứng.

| # | Hạng mục | Trạng thái | Chi tiết |
|---|---|---|---|
| Skill discovery | Kiểm tra `skills/`/`SKILL.md` trong repo | ✅ DONE | Không tìm thấy — không có skill nào để dùng (xem TASKS.md) |
| Kiến trúc | Dashboard Adapter/API trên CellRuntime | ✅ DONE | `dtos.py` (view-model thuần) / `session.py` (sở hữu demo cell) / `api.py` (FastAPI routes) |
| 8 mục thông tin | Overview/Production/Vision&OCR/Safety/Health/OEE/Events/Diagnostics | ✅ DONE (8/8) | Vision/OCR/Decision/Safety hiển thị **tách biệt**, không gộp |
| Demo controls | START/STOP/RESET + 7 SIMULATE + RUN FULL DEMO | ✅ DONE | Mọi control đi qua đúng kiến trúc thật (`sim.detect_product()`, `sim.press_estop()`, `ControlCommand`...), không có "cửa sau" |
| Error handling | SYSTEM OFFLINE / UNKNOWN, không giả HEALTHY/SAFE | ✅ DONE | Test 13/14 chứng minh trực tiếp |
| Layer rule | Mở rộng `ALLOWED["dashboard"]` | ✅ DONE (D-065) | Thêm `services, analytics, sim, vision, ocr, decision` — lý do bắt buộc, ghi rõ trong DECISIONS.md |
| Mở rộng CellRuntime | `product_history()`, `event_log()`, property `ocr`/`vision` | ✅ DONE (D-066, bồi thêm, không sửa logic cũ) | 43 test Phase 6 cũ vẫn PASS không sửa |
| Test | 20 mục yêu cầu (mục 13 chỉ thị) | ✅ DONE (22 test, vượt yêu cầu) | `test_dashboard_api.py` — TestClient thật, không mock backend |
| Xác minh trực quan | Chạy dashboard thật + thao tác qua trình duyệt | ✅ DONE | Claude Browser tool: START/GOOD/DEFECT/E-STOP/RESET/RUN FULL DEMO/8 tab — không lỗi console |
| Regression | Toàn bộ Python + firmware | ✅ DONE | 859 passed/1 skipped (808+51, 0 hỏng); firmware 262/262 không đổi |

**File mới:** `edge/src/msfc/dashboard/{__init__,dtos,session,api,__main__}.py` + `static/{index.html,styles.css,app.js}` + `edge/run_dashboard.py` + `.claude/launch.json` + 4 file test (`test_services_runtime_observability.py`, `test_dashboard_dtos.py`, `test_dashboard_session.py`, `test_dashboard_api.py`) + 3 tài liệu (`OFFICIAL_DASHBOARD_ARCHITECTURE.md`, `OFFICIAL_DASHBOARD_USER_GUIDE.md`, `PHASE_DASHBOARD_COMPLETION_REPORT.md`). **Sửa đổi:** `edge/src/msfc/services/{platform_model,runtime,__init__}.py` (bồi thêm), `edge/tests/unit/test_layer_dependencies.py`, `edge/pyproject.toml` (dependency mới đầu tiên kể từ Phase 0: `fastapi`/`uvicorn`/`httpx`, D-064). **2 lỗi thật phát hiện và sửa trước khi chốt (D-067).** **51 test mới.** Chi tiết đầy đủ: [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md).

## 2. Đã giao (Phase 0 + Phase 1 software-first)

### Phase 0 (xem chi tiết ở CHANGELOG.md)

| # | Artifact |
|---|---|
| 1–16 | Charter, Requirements, Architecture, Safety Concept, MQTT contract, 13 ADR, QA plan, Coding/Git standards, Config+Logging (43 test), BOM, Roadmap/Tasks/Decisions/Risks, Phase1 plan, check_env.py, TEST_REPORT |

### Phase 1 software-first (lượt này, 2026-09-18)

| # | Artifact | Test |
|---|---|---:|
| 17 | `edge/src/msfc/domain/` (8 module) | 80 |
| 18 | `edge/src/msfc/contracts/` (registry, envelope, validation) | 45 |
| 19 | `edge/src/msfc/comm/` (bus, topic_match, dedupe, backoff, mqtt_bus) | 53 |
| 20 | `edge/src/msfc/vision/` (frame, synthetic, sources, preprocess, inference, baseline, postprocess, evaluation) | 65 |
| 21 | `edge/src/msfc/decision/` (policy, engine) | 20 |
| 22 | `edge/src/msfc/sim/` (codec, engine — Cell Controller simulator) | 38 |
| 23 | `edge/tests/integration/test_full_pipeline_mvp.py` | 6 |
| 24 | `docs/HARDWARE_MASTER_BOM.md`, `docs/HARDWARE_INTERFACE.md`, `docs/DATASET_SPEC.md`, `docs/PHASE1_PLAN.md` v2.0 | — |

### Phase 1 software-first, lượt 2 (2026-09-18) — P1.3 CNN/ONNX

| # | Artifact | Test |
|---|---|---:|
| 25 | `edge/src/msfc/vision/training.py`, `edge/src/msfc/vision/onnx_backend.py` | 17 |
| 26 | `ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/` (checkpoint, ONNX, metrics.json, config.toml, checksum.txt, model_card.md) | — (artifact, không phải test) |

### Phase 1 software-first, lượt 3 (2026-09-18) — Close Phase 1 Software Gate: P1.5

| # | Artifact | Test |
|---|---|---:|
| 27 | `firmware/cell_controller/components/core_logic/` (cell_sm, fault_manager, debounce, safety_supervisor, cmd_handler, watchdog, logger, comm_link.h) | — |
| 28 | `firmware/cell_controller/components/hal/` (hal_interface.h, hal_host_mock.c/.h) | — |
| 29 | `firmware/cell_controller/test_host/` (7 file test + `build_and_run.sh`) | 131 |

### Phase 2 — Software-only Safety & Interlock (2026-09-18)

| # | Artifact | Test |
|---|---|---:|
| 30 | `firmware/cell_controller/components/core_logic/safety_interlock.h/.c` (thuần cộng thêm, không sửa file P1 nào) | — |
| 31 | `firmware/cell_controller/test_host/test_safety_interlock_core.c` (P2.1/P2.2/P2.7) | 34 |
| 32 | `firmware/cell_controller/test_host/test_safety_interlock_comm_loss.c` (P2.5/P2.6) | 43 |
| 33 | `firmware/cell_controller/test_host/test_safety_interlock_recovery.c` (P2.8) | 27 |
| 34 | `firmware/cell_controller/test_host/test_safety_scenarios.c` (P2.9, 12 kịch bản) | 27 |

### Phase 3 — Software-only OCR / Expiry / Label Verification (2026-09-18)

| # | Artifact | Test |
|---|---|---:|
| 35 | `edge/src/msfc/ocr/` (models, engine, preprocess, text, validate, classify, pipeline, synthetic) | — |
| 36 | `edge/tests/unit/test_ocr_models.py`, `test_ocr_engine.py`, `test_ocr_preprocess.py`, `test_ocr_text.py` | 8+6+17+17 |
| 37 | `edge/tests/unit/test_ocr_validate.py`, `test_ocr_classify.py`, `test_ocr_pipeline.py`, `test_ocr_fixtures.py` | 17+11+7+15 |
| 38 | `edge/tests/integration/test_ocr_decision_integration.py` | 5 |

### Phase 4 — Software-only OEE / Machine Monitoring (2026-09-18)

| # | Artifact | Test |
|---|---|---:|
| 39 | `edge/src/msfc/analytics/` (models, events, calculations, session, monitor, repository, simulate) | — |
| 40 | `edge/tests/unit/test_analytics_models.py`, `test_analytics_events.py`, `test_analytics_calculations.py` | 10+14+25 |
| 41 | `edge/tests/unit/test_analytics_session.py`, `test_analytics_monitor.py`, `test_analytics_repository.py`, `test_analytics_fixtures.py` | 22+5+5+17 |
| 42 | `edge/tests/integration/test_analytics_domain_integration.py` | 1 |

### Phase 5 — Software-only Machine Health / Anomaly Detection / Predictive Maintenance (2026-09-18)

| # | Artifact | Test |
|---|---|---:|
| 43 | `edge/src/msfc/analytics/` (health_models, sensors, quality, features, baseline, anomaly, health_score) | — |
| 44 | `edge/src/msfc/analytics/` (health_events, health_monitor, predictive, health_repository, evaluation, health_simulate, health_p4_bridge) | — |
| 45 | `edge/tests/unit/test_analytics_health_models.py`, `test_analytics_sensors.py`, `test_analytics_quality.py`, `test_analytics_features.py` | 10+4+16+10 |
| 46 | `edge/tests/unit/test_analytics_baseline.py`, `test_analytics_anomaly.py`, `test_analytics_health_score.py`, `test_analytics_health_events.py` | 10+16+6+9 |
| 47 | `edge/tests/unit/test_analytics_health_monitor.py`, `test_analytics_predictive.py`, `test_analytics_health_repository.py`, `test_analytics_evaluation.py` | 10+9+5+12 |
| 48 | `edge/tests/unit/test_analytics_health_p4_bridge.py`, `test_analytics_health_fixtures.py` | 5+19 |
| 49 | `edge/tests/integration/test_analytics_health_p4_integration.py` | 2 |

### Phase 6 — Edge AI Platform / Final Software Integration (2026-09-19)

| # | Artifact | Test |
|---|---|---:|
| 50 | `edge/src/msfc/services/` (platform_model, codec, timing, vision_pipeline, safety_gate) | — |
| 51 | `edge/src/msfc/services/` (pipeline, health_pipeline, runtime, `__init__`) | — |
| 52 | `edge/tests/unit/test_services_platform_model.py`, `test_services_codec.py`, `test_services_timing.py` | 11+11+5 |
| 53 | `edge/tests/unit/test_services_vision_pipeline.py`, `test_services_safety_gate.py`, `test_services_health_pipeline.py` | 5+7+5 |
| 54 | `edge/tests/unit/test_services_pipeline.py`, `test_services_runtime.py`, `test_services_fixtures.py` | 11+8+11 |
| 55 | `edge/tests/integration/test_services_scenarios.py` (20 kịch bản) | 20 |
| 56 | `edge/tests/integration/test_services_full_stack_integration.py` (success + failure path) | 2 |

### Official Web Dashboard (2026-09-19)

| # | Artifact | Test |
|---|---|---:|
| 57 | `edge/src/msfc/dashboard/{__init__,dtos,session,api,__main__}.py` | — |
| 58 | `edge/src/msfc/dashboard/static/{index.html,styles.css,app.js}`, `edge/run_dashboard.py`, `.claude/launch.json` | — |
| 59 | `edge/src/msfc/services/{platform_model,runtime,__init__}.py` (mở rộng bồi thêm) | 7 (`test_services_runtime_observability.py`) |
| 60 | `edge/tests/unit/test_dashboard_dtos.py`, `test_dashboard_session.py` | 11+11 |
| 61 | `edge/tests/integration/test_dashboard_api.py` (20 mục yêu cầu + WebSocket + OpenAPI) | 22 |
| 62 | `OFFICIAL_DASHBOARD_ARCHITECTURE.md`, `OFFICIAL_DASHBOARD_USER_GUIDE.md`, `PHASE_DASHBOARD_COMPLETION_REPORT.md` | — |

## 3. Blocker hiện tại

| ID | Blocker | Cần ai | Chặn việc gì |
|---|---|---|---|
| B1 | Duyệt kết quả Phase 1–6 + Official Dashboard software scope + quyết định mới (xem DECISIONS.md) | **PO** | Tiếp tục sang P1.9 hoặc bước tiếp theo |
| B2 | Chọn phương án trong Master BOM + ngân sách tối đa | **PO** | Chốt wave W1 |
| B3 | Duyệt wave W1 (0,65–1,35 triệu) | **PO** | P1.9 → P1.10 |
| B4 | Cài **ESP-IDF 5.x** + **Mosquitto** (miễn phí; `gcc` đã có sẵn, không cần cài — D-036) | **PO** | P1.5b (build ESP32 thật), test MQTT trên broker thật (MT-02..05) |
| B5 | Gom 50–100 nắp chai làm sản phẩm mẫu (0đ) | **PO** | P1.11 dataset thật |
| B6 | Kênh E-stop vật lý (NC contact, SAF-01) — cần mua + lắp (wave W2, đã APPROVED về thiết kế — D-023) | **PO** | PHYSICAL E-STOP VALIDATION |

**Command cài đặt B4 (PO tự chạy, Claude Inc không tự cài phần mềm mới — ngoài thẩm quyền tự động):**
- **ESP-IDF 5.x (Windows):** dùng bộ cài chính thức — tải "ESP-IDF Tools Installer" tại `dl.espressif.com/dl/esp-idf` (chọn bản offline, có cả toolchain xtensa). Sau khi cài, mở "ESP-IDF 5.x CMD" từ Start Menu để có `idf.py` sẵn trong PATH của phiên đó.
- **Mosquitto (Windows):** `winget install EclipseMosquitto.Mosquitto` (nếu có `winget`), hoặc tải installer tại `mosquitto.org/download`.
- **gcc:** đã có sẵn tại `C:\msys64\ucrt64\bin\gcc.exe` — nếu PO muốn dùng trực tiếp trong terminal thường (không qua script), tự thêm `C:\msys64\ucrt64\bin` vào biến môi trường PATH của Windows (Claude Inc không tự sửa PATH hệ thống).

## 4. Rủi ro cần chú ý

🔴 R-01 Wi-Fi gây dừng oan · R-02 băng tải tự chế không ổn định · R-04 sụt áp reset ESP32 · R-05 dataset ít/thiên lệch · R-07 phạm vi phình to · R-10 nhầm lẫn "an toàn đạt chuẩn" · R-21..23, R-26 (hardware=NONE) · **R-28 baseline cổ điển VÀ CNN scaffold đều không phân biệt được lỗi trên dữ liệu tổng hợp mặc định (D-035)**.
**Rủi ro nhắc lại:** R-10 ("nhầm lẫn an toàn đạt chuẩn") áp dụng cho Phase 2 (software E-STOP ≠ vật lý), Phase 3 (OCR trên ảnh tổng hợp ≠ độ chính xác thật), Phase 4 (OEE trên sự kiện mô phỏng ≠ OEE dây chuyền thật), Phase 5 (machine health/predictive maintenance trên cảm biến mô phỏng ≠ độ chính xác thật, KHÔNG mô hình nào đã huấn luyện), Phase 6 (orchestration/runtime chạy đúng trên `SimCellController` mô phỏng ≠ bằng chứng vận hành trên phần cứng/mạng MQTT thật; `msfc.services` chỉ chứng minh kiến trúc CÓ THỂ thay sang phần cứng thật, không phải ĐÃ chạy trên phần cứng thật), **và** Official Dashboard (giao diện hiển thị đúng dữ liệu mô phỏng — không phải bằng chứng dashboard đã chạy với dữ liệu/người dùng thật, chưa có xác thực/nhiều người dùng) — xem cảnh báo ở mục 0.
Chi tiết: [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md).

## 5. Việc tiếp theo (chờ PO — đã STOP theo yêu cầu, chờ duyệt bước tiếp theo)

**Official Dashboard đã DONE (2026-09-19), chờ PO duyệt — không phải Phase 7 (PO chỉ thị rõ).** Các việc dưới đây chỉ mở khóa khi PO chủ động quyết định — Claude Inc không tự cài ESP-IDF/Mosquitto/OCR service, không tự mua hardware/cảm biến, không tự bắt đầu phase mới.

| # | Việc | Ai |
|---|---|---|
| 1 | Đọc [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md), duyệt hoặc yêu cầu sửa | **PO** |
| 2 | Chạy thử dashboard (`python edge/run_dashboard.py`), xem [OFFICIAL_DASHBOARD_USER_GUIDE.md](OFFICIAL_DASHBOARD_USER_GUIDE.md) | **PO** |
| 3 | Q-19 (D-051): sửa `health_state.v1`/`health_features.v1` (draft) cho khớp 5-state/8-sensor-type, hay giữ nguyên và thu hẹp khi publish thật? (vẫn CHỜ) | **PO** |
| 4 | Q-18 (D-048): sửa `oee_metrics.v1` (draft) bỏ giới hạn tối đa 1.0 cho performance/oee, hay giữ nguyên và luôn clamp khi publish? (vẫn CHỜ) | **PO** |
| 5 | Q-17 (D-040 cùng logic): hoàn thiện schema `label_result.v1` (draft) để publish qua MQTT thật? (vẫn CHỜ) | **PO** |
| 6 | Q-16 (D-040): hợp nhất `interlock_reject_t` mới vào contract layer ngay hay để tới P1.10? | **PO** |
| 7 | Quyết định Q-15: xử lý giới hạn chung của baseline+CNN trên dataset tổng hợp thế nào trước P1.11 | **PO** |
| 8 | Khi muốn mở khóa ESP32 TARGET BUILD / REAL HARDWARE / REAL EDGE DEPLOYMENT / PHYSICAL E-STOP / REAL OCR / REAL OEE / REAL MACHINE-HEALTH / REAL PREDICTIVE-MAINTENANCE VALIDATION: cài ESP-IDF (B4), chọn BOM + duyệt wave W1/W2 (B2/B3/B6), thu ảnh thật + cài OCR engine thật, lắp dây chuyền thật + cảm biến thật, chọn target Edge device | **PO** |
| 9 | Duyệt bắt đầu phase/bước tiếp theo (chưa duyệt) | **PO** |
| 10 | Sau khi PO chỉ đạo: tiếp tục theo hướng được chọn | Claude Inc |

## 6. Ghi chú trung thực

- **Chưa có phần cứng nào được kiểm chứng.** Toàn bộ kết quả trên là phần mềm chạy trên laptop với dữ liệu tổng hợp/giả lập.
- **Software E-STOP simulation (Phase 2) không phải xác nhận E-stop vật lý** — kênh cứng NC (SAF-01/IF-HW-01) chưa tồn tại, chưa mua, chưa đo.
- **Machine health/predictive maintenance (Phase 5) chạy trên cảm biến mô phỏng — `RuleBasedReferenceModel` KHÔNG phải mô hình đã huấn luyện, `validated_on_real_data` luôn `False`.** Không có dữ liệu suy giảm máy thật nào được dùng.
- **Kết quả OCR (Phase 3) chạy trên ảnh tổng hợp + Mock/Fixture OCR engine — không phải bằng chứng độ chính xác OCR trên ảnh/sản phẩm thật.** Không có OCR engine thật nào được cài (đúng rule 4 PO chỉ thị).
- **Kết quả OEE (Phase 4) chạy trên sự kiện máy tổng hợp/mô phỏng — không phải bằng chứng OEE của một dây chuyền vật lý thật.** `msfc.analytics` không có khả năng ghi đè an toàn P2 (bảo đảm bằng luật layer, không chỉ kỷ luật code).
- Kết quả trên `SyntheticFrameSource`/`_OracleVisionEngine`/`InMemoryBus`/`hal_host_mock`/`FixtureOcrEngine`/`msfc.analytics.simulate`/`msfc.sim.SimCellController` **không phải bằng chứng về độ chính xác AI/OCR/OEE hay độ tin cậy phần cứng thật** — chỉ chứng minh **kiến trúc và luồng dữ liệu (wiring)** đúng như thiết kế.
- **Edge AI Cell Platform (Phase 6) chạy hoàn toàn giữa `msfc.services` và `msfc.sim.SimCellController` mô phỏng, qua `InMemoryBus`** — chưa từng chạy với một broker MQTT thật, một ESP32 thật, hay bất kỳ tín hiệu vật lý nào. "Kiến trúc cho phép thay thế phần cứng" (P6.19) là một khẳng định về THIẾT KẾ (import boundary, interface), không phải một khẳng định rằng việc thay thế đó đã được thử.
- **Official Dashboard hiển thị đúng dữ liệu mô phỏng — không phải bằng chứng vận hành thật.** Chỉ chạy local (`127.0.0.1`), một phiên demo duy nhất, không xác thực người dùng — phù hợp cho demo sinh viên/giảng viên, không phải triển khai sản xuất nhiều người dùng.
- Giới hạn thật của `ClassicCvBaseline` (mục 1c) được báo cáo trung thực ngay khi phát hiện, không làm đẹp số liệu.
- Các mốc số (300 ms, deadline, ngưỡng…) vẫn là **mục tiêu ban đầu**, sẽ xác nhận lại khi có phần cứng thật.
- 8 "vai trò" trong các báo cáo trước và việc tự review code ở đây đều do **một assistant** thực hiện, không phải nhiều người độc lập.
- Tuân thủ đúng yêu cầu STOP của PO: **chưa chạm tới P1.9 (procurement) và chưa tự bắt đầu phase/bước tiếp theo nào.**
- **Phase 1 software scope đã được PO approve đóng** — [PHASE1_COMPLETION_REPORT.md](PHASE1_COMPLETION_REPORT.md). **Phase 2 (Safety & Interlock) đã được PO approve đóng** — [PHASE2_COMPLETION_REPORT.md](PHASE2_COMPLETION_REPORT.md), toàn bộ là code cộng thêm (`safety_interlock.h/.c`), không sửa file P1 nào. **Phase 3 (OCR/Expiry/Label) đã được PO approve đóng** — [PHASE3_COMPLETION_REPORT.md](PHASE3_COMPLETION_REPORT.md), toàn bộ là package mới `msfc.ocr/`, không sửa file P1/P2 nào ngoài thêm `OcrError` (theo đúng pattern có sẵn). **Phase 4 (OEE/Machine Monitoring) đã được PO approve đóng** — [PHASE4_COMPLETION_REPORT.md](PHASE4_COMPLETION_REPORT.md), toàn bộ là package mới `msfc.analytics/`, không sửa file P1/P2/P3 nào ngoài thêm `OeeError` (theo đúng pattern có sẵn). **Phase 5 (Machine Health/Anomaly/Predictive Maintenance) đã được PO approve đóng** — [PHASE5_COMPLETION_REPORT.md](PHASE5_COMPLETION_REPORT.md), mở rộng `msfc.analytics/` bằng 12 module mới, không sửa file P1/P2/P3/P4 nào ngoài thêm `HealthError` (theo đúng pattern có sẵn). **Phase 6 (Edge AI Platform / Final Software Integration) đã được PO approve đóng** — [PHASE6_COMPLETION_REPORT.md](PHASE6_COMPLETION_REPORT.md), package mới `msfc.services/` (9 module), không sửa file P1/P2/P3/P4/P5 nào ngoài thêm `OrchestrationError` (theo đúng pattern có sẵn). **Official Web Dashboard DONE lượt này** — [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md), package mới `msfc.dashboard/` (5 module + frontend tĩnh), mở rộng bồi thêm `msfc.services` (không sửa logic cũ); firmware C không cần sửa.
