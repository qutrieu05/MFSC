# Tasks — MSFC

**Trạng thái hợp lệ:** `BACKLOG` · `READY` · `IN_PROGRESS` · `BLOCKED` · `TESTING` · `DONE`
**Nguồn sự thật:** trạng thái task cũng được ghi trong workspace riêng của Claude Inc (`company project`); file này là **bản báo cáo cho người đọc**. Nếu lệch, lấy bản ghi có bằng chứng (artifact + test) làm chuẩn.

**Phase 1 = SOFTWARE-FIRST COMPLETE** (PO approved 2026-09-18) — 5 mức trạng thái (software logic / host validation / ESP32 target build / real hardware validation / real AI validation) xem [PROJECT_STATUS.md](PROJECT_STATUS.md#0-trạng-thái-phase-1-theo-5-mức-chuẩn-hóa-theo-yêu-cầu-po) mục 0. Tổng kết đầy đủ: [PHASE1_COMPLETION_REPORT.md](PHASE1_COMPLETION_REPORT.md).

---

## Phase 0 — Project Foundation

| ID | Task | Phụ thuộc | Trạng thái |
|---|---|---|---|
| P0-01 | Audit repo + môi trường, tạo cấu trúc repo, Git strategy | – | DONE |
| P0-02 | Project Charter | P0-01 | DONE |
| P0-03 | System Requirements (SRS) gồm yêu cầu an toàn | P0-02 | DONE |
| P0-04 | Architecture + Safety Concept + 13 ADR | P0-03 | DONE |
| P0-05 | MQTT contract v0.1 (registry + 23 schema + tài liệu) | P0-04 | DONE |
| P0-06 | Hardware inventory checklist + BOM sơ bộ + pin map DRAFT | P0-04 | DONE |
| P0-07 | Roadmap + Risk Register + TASKS + PROJECT_STATUS | P0-04 | DONE |
| P0-08 | Coding standards + Git strategy + QA plan + cấu trúc test | P0-04 | DONE |
| P0-09 | Configuration system + logging system (code + 28 unit test) | P0-08 | DONE |
| P0-10 | Test cấu trúc layer + test contract (15 test) + `tools/check_env.py` | P0-09, P0-05 | DONE |
| P0-11 | Phase 1 plan + MVP + acceptance criteria | P0-06, P0-07 | DONE |

### Chi tiết Phase 0

**P0-01 — Audit + cấu trúc repo + Git**
- *Objective:* có repo sạch, tách khỏi tài liệu nghiên cứu, biết chính xác môi trường đang có gì.
- *Implementation:* `git init -b main`; `.gitignore`, `.gitattributes`, `.editorconfig`; audit bằng lệnh (`python`, `pytest`, `git`, `nvidia-smi`, cổng COM, camera).
- *Acceptance:* repo tồn tại; kết quả audit được ghi lại; không commit dữ liệu/bí mật.
- *Test:* `git rev-parse --show-toplevel`; `python tools/check_env.py`.
- *Evidence:* [docs/HARDWARE_INVENTORY.md](docs/HARDWARE_INVENTORY.md) mục 1; [docs/GIT_STRATEGY.md](docs/GIT_STRATEGY.md).

**P0-02 — Project Charter** → [docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md). *Acceptance:* mục tiêu, vai trò, phạm vi, ràng buộc, giới hạn của Claude Inc được ghi rõ.

**P0-03 — Requirements** → [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md). *Acceptance:* 15 yêu cầu an toàn (SAF-01..15) + yêu cầu chức năng theo 9 nhóm + NFR + 20 tiêu chí ACC, mỗi yêu cầu có ID, mức ưu tiên, phase, cách kiểm chứng.

**P0-04 — Architecture + Safety + ADR** → [ARCHITECTURE.md](ARCHITECTURE.md), [docs/SAFETY_CONCEPT.md](docs/SAFETY_CONCEPT.md), [docs/adr/](docs/adr/). *Acceptance:* 9 layer có interface; máy trạng thái; ngân sách thời gian; 8 chức năng an toàn + bảng mã lỗi + ma trận reset; 13 ADR có phương án so sánh (chi phí/độ phức tạp/độ tin cậy).

**P0-05 — MQTT contract** → [contracts/mqtt/topics.toml](contracts/mqtt/topics.toml), [contracts/schemas/](contracts/schemas/), [docs/MQTT_CONTRACT.md](docs/MQTT_CONTRACT.md). *Acceptance:* 25 topic có publisher/subscriber/QoS/retain/schema/rate/phase; envelope chung; quy tắc lỗi và phiên bản. *Test:* `edge/tests/contract/test_contract_files.py` (13 test, pass).

**P0-06 — Hardware** → [docs/HARDWARE_INVENTORY.md](docs/HARDWARE_INVENTORY.md), [HARDWARE_BOM.md](HARDWARE_BOM.md), [hardware/PIN_MAPPING_DRAFT.md](hardware/PIN_MAPPING_DRAFT.md). *Acceptance:* mọi hạng mục có nhãn REQUIRED/OPTIONAL/FUTURE + phương án rẻ hơn + lý do; **chưa yêu cầu mua gì**.

**P0-07 — Quản lý dự án** → [ROADMAP.md](ROADMAP.md), [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md), TASKS.md, [PROJECT_STATUS.md](PROJECT_STATUS.md). *Acceptance:* 20 rủi ro có dấu hiệu sớm + biện pháp; roadmap có acceptance từng phase.

**P0-08 — Chuẩn và QA** → [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md), [docs/QA_PLAN.md](docs/QA_PLAN.md). *Acceptance:* 10 mức test; 17 test an toàn; 12 test lỗi; điều kiện vào/ra từng phase; ma trận truy vết.

**P0-09 — Config + Logging**
- *Implementation:* `edge/src/msfc/core/{config,logging_setup,errors}.py`, `config/default.toml`, `config/site.example.toml`.
- *Acceptance:* cấu hình phân lớp (default → site → env), **khóa lạ bị từ chối**, giá trị ngoài dải báo lỗi có tên khóa; log JSONL + console có ngữ cảnh; `configure_logging` idempotent.
- *Test:* `test_config.py` (20 case) + `test_logging_setup.py` (8 case) — pass.

**P0-10 — Bảo vệ kiến trúc + contract**
- *Implementation:* `test_layer_dependencies.py` (đọc AST, kiểm tra quy tắc import), `test_contract_files.py`, `tools/check_env.py`.
- *Acceptance:* thêm package mới mà không khai báo trong quy tắc → test fail; lệnh cấm retain cho `cmd` được kiểm tra; tài liệu contract phải chứa mọi topic key.
- *Test:* 43/43 test pass (`cd edge && python -m pytest`).

**P0-11 — Phase 1 plan** → [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md). *Acceptance:* MVP hẹp, 5 milestone, 18 task, 11 acceptance criteria đo được, 5 blocker, điểm dừng cho việc tay của PO.

---

## Phase 1 — Conveyor + Basic Vision Control (kế hoạch v2.0, hardware = NONE)

> Cấu trúc 12 phần theo chỉ thị PO ngày 2026-09-18. Chi tiết: [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md) v2.0.
> **P1.1 → P1.8 làm hoàn toàn trên laptop, 0đ phần cứng.** Chưa task nào được bắt đầu.

| ID | Task | Phụ thuộc | Cần HW | Cần cài (miễn phí) | Trạng thái |
|---|---|---|:-:|---|---|
| **P1.1** | Software Architecture: `msfc.domain` (dataclass thuần), khung package theo layer, hoàn thiện quy tắc phụ thuộc | B1 | – | – | ✅ **DONE** |
| **P1.2** | Camera Simulation / Test Input: `FrameSource` (ảnh tổng hợp, thư mục ảnh, video, camera USB), ring buffer timestamp, sinh ảnh synthetic | P1.1 | – | numpy, opencv | ✅ **DONE** |
| **P1.3** | AI Baseline: baseline cổ điển + khung đánh giá offline (accuracy/precision/recall/FP/FN/confusion) + pipeline huấn luyện CNN (chạy sau khi có dataset thật) | P1.2 | – | onnxruntime (+torch khi train) | ✅ **DONE (cổ điển + CNN/ONNX smoke test)** — xem chi tiết dưới; giới hạn AI thật vẫn còn, xem PROJECT_STATUS.md mục 1c |
| **P1.4** | Decision Engine: luật, mã lý do, chính sách `UNCERTAIN`/`NO_DECISION`, nhật ký quyết định | P1.1 | – | – | ✅ **DONE** |
| **P1.5** | ESP32 Firmware Architecture: `core_logic` C99 (cell_sm, safety_supervisor, fault_manager, debounce, cmd_handler, watchdog, logger) + HAL boundary + test host | B1 | – | gcc (đã có, xem dưới) | 🟡 **host-testable core_logic DONE** (131/131 check pass) — **build thật cho chip ESP32 vẫn BLOCKED** (thiếu ESP-IDF SDK, B4) |
| **P1.6** | Firmware Simulator / Mock: `msfc.sim` mô phỏng đầy đủ hành vi cell gồm fail-safe, đồng hồ ảo | P1.1, P1.7 | – | – | ✅ **DONE** |
| **P1.7** | Communication Contract runtime: registry loader, envelope codec, validate schema, `MessageBus` + `InMemoryBus` + `MqttBus`, chống trùng, backoff | P1.1 | – | Mosquitto, paho-mqtt, jsonschema | ✅ **DONE** |
| **P1.8** | Hardware Interface Definition | Phase 0 | – | – | ✅ **DONE** ([docs/HARDWARE_INTERFACE.md](docs/HARDWARE_INTERFACE.md)) |
| — | **Pipeline MVP end-to-end** (P1.2+P1.4+P1.6+P1.7 nối lại, integration test) | P1.2, P1.4, P1.6, P1.7 | – | – | ✅ **DONE** |
| **P1.9** | Hardware Procurement: wave W1 → W2 → W3 + kiểm tra hàng về | AC-SW-07, B2, B3 | 🛒 | – | 🚫 **NOT STARTED** — PO yêu cầu STOP trước bước này |
| **P1.10** | Real Hardware Integration: nạp firmware, `hardware/WIRING_GUIDE.md`, test từng tín hiệu HAL, đổi `hal_host_mock` → `hal_esp32`, lắp băng tải | P1.9, P1.5 | ✅ | – | BACKLOG |
| **P1.11** | Timing Calibration + dataset thật: đo tốc độ đai, khoảng cách, trễ gạt, phân bố độ trễ MQTT, chốt `heartbeat_timeout_ms`; thu 600–1.000 ảnh, huấn luyện mô hình v1 | P1.10 | ✅ | – | BACKLOG |
| **P1.12** | Full System Test: AC-P1-01..11, ST/FT/PT/LT, báo cáo Phase 1 | P1.11 | ✅ | – | BACKLOG |

**Cổng nghiệm thu software (trước khi mua):** AC-SW-01..07 trong [PHASE1_PLAN.md](docs/PHASE1_PLAN.md) mục 3.

### Chi tiết P1.1 — Software Architecture ✅ DONE (2026-09-18)

- *Implementation:* `edge/src/msfc/domain/` — 8 module: `enums.py` (9 enum, gồm `MachineState` khớp `cell_state.v1`, `NON_PRODUCTION_STATES`/`LATCHED_STATES`), `faults.py` (catalog 19 mã lỗi F001–F070 + E101–E103, mỗi mã có `severity` và `latching` suy từ [SAFETY_CONCEPT.md](docs/SAFETY_CONCEPT.md) mục 5), `_validators.py`, `events.py` (`ProductDetectedEvent`, `ProductSortedEvent` với `margin_ms`/`latency_detect_to_verdict_ms` tính sẵn, `StateChangedEvent`), `inspection.py` (`InspectionResult`, `DecisionRecord`, `ModelInfo`), `commands.py` (`VerdictCommand`, `ControlCommand`, `CommandAck`), `state.py` (`CellStateSnapshot` — **tự kiểm tra bất biến SAF-10/SF-07 ngay ở tầng dữ liệu**: relay đóng hoặc pusher không thu chỉ hợp lệ ở STARTING/RUNNING/STOPPING, `Counters`, `FaultReport`).
- *Acceptance:* mọi dataclass là `frozen=True, slots=True`; validate trong `__post_init__` ném `DomainError` nêu rõ trường sai (khớp phong cách `ConfigError`); enum dùng `str, Enum` để `json.dumps` ra đúng giá trị theo schema (đã viết test xác nhận cơ chế này); `msfc.core` được thêm `DomainError`, `VisionError`, `DecisionError`, `SimulationError`, và `PayloadInvalidError` nhận `topic` để phục vụ P1.7.
- *Test:* 4 file, **80 test case mới** (`test_domain_enums_faults.py` 16, `test_domain_events.py` 17, `test_domain_inspection_commands.py` 17, `test_domain_state.py` 30) — **PASS**.
- *Kết quả chạy:* `cd edge && python -m pytest` → **123 passed** (43 Phase 0 + 80 domain), exit code 0.
- *Blocker:* không.

### Chi tiết P1.7 — Communication Contract runtime ✅ DONE (2026-09-18)

- *Implementation:* `edge/src/msfc/contracts/` (`registry.py` — `ContractRegistry` đọc `topics.toml`, biên dịch regex cho từng pattern, `format_topic`/`match_topic`, cache schema; `envelope.py` — `build_envelope`, `SeqCounter`; `validation.py` — `PayloadValidator` dùng `jsonschema.Draft202012Validator`) và `edge/src/msfc/comm/` (`bus.py` — `MessageBus` Protocol + `InMemoryBus` đồng bộ, khớp semantics retain thật; `topic_match.py` — biên dịch filter MQTT `+`/`#`; `dedupe.py` — `DedupeFilter` theo (device_id, boot_id, seq), có giới hạn bộ nhớ; `backoff.py` — `ReconnectBackoff` mũ có trần; `mqtt_bus.py` — `MqttBus` bọc paho-mqtt, **client injectable** qua `client_factory` để test không cần broker thật).
- *Phát hiện khi test (đã sửa):* thiết kế ban đầu của `format_topic`/`match_topic` có tham số `name` cho một placeholder `{name}` tổng quát — **không có topic nào trong registry thật dùng cơ chế này** (mỗi sự kiện có key và pattern riêng, tên đã cố định trong pattern). Đã bỏ tham số `name` khỏi API để tránh code chết, theo đúng nguyên tắc "không thêm phức tạp không cần thiết".
- *Acceptance:* payload sai (thiếu trường, sai enum, sai schema cho topic, sai `device_id`) bị từ chối bằng `PayloadInvalidError` nêu rõ topic + lý do (FR-COM-06); `cmd/*` không bao giờ retain, `state`/`status` luôn retain, `heartbeat` luôn QoS 0 — kiểm tra lại bằng test runtime (không chỉ test file tĩnh của Phase 0); `MqttBus` tự kết nối lại có backoff khi `connect()` thất bại, dừng sau `max_connect_attempts` nếu đặt; JSON lỗi hoặc handler lỗi ở tầng nhận **không làm crash** vòng lặp mạng.
- *Test:* 6 file mới, **99 test case** (`test_contracts_registry.py` 19, `test_contracts_envelope.py` 13, `test_contracts_validation.py` 13, `test_comm_topic_match.py` 13, `test_comm_bus.py` 9, `test_comm_dedupe.py` 8, `test_comm_backoff.py` 8, `test_comm_mqtt_bus.py` 15) — tất cả dùng `FakeMqttClient` tự viết, **không cần broker thật**. Thêm 1 integration test tùy chọn (`tests/integration/test_mqtt_bus_real_broker.py`) tự `SKIP` khi chưa cài Mosquitto (đúng blocker B4), không bao giờ báo PASS giả.
- *Kết quả chạy:* `cd edge && python -m pytest` → **221 passed, 1 skipped**, exit code 0.
- *Blocker:* MQTT thật (MT-02..05 trên broker) vẫn **NOT RUN** cho tới khi cài Mosquitto (B4) — đã có test tự động sẵn sàng chạy ngay khi đó.

### Chi tiết P1.2 + P1.3 (phần cổ điển) — Camera Simulation + AI Baseline ✅ DONE (2026-09-18)

- *Implementation:* `edge/src/msfc/vision/` (Layer 3, chỉ phụ thuộc `core`+`domain`): `frame.py` (`Frame`, `FrameSource` Protocol); `synthetic.py` (sinh ảnh "nắp chai" tổng hợp 128×128, 3 loại lỗi tự tạo theo [DATASET_SPEC](docs/DATASET_SPEC.md): `MARK` dễ, `STICKER_MISSING` trung bình, `SCRATCH` khó — cố ý để báo cáo recall trung thực); `sources.py` (`SyntheticFrameSource`, `ImageFolderFrameSource`, `VideoFileFrameSource`, `UsbCameraFrameSource`); `preprocess.py` (`RoiConfig`, crop+resize); `inference.py` (`InferenceEngine` Protocol, `InferenceOutput`); `baseline.py` (`ClassicCvBaseline` — khoảng cách tới ảnh mẫu GOOD trung bình, ánh xạ sigmoid quanh ngưỡng); `postprocess.py` (`Thresholds`, GOOD/DEFECT/UNCERTAIN); `evaluation.py` (`evaluate()` — accuracy/precision/recall/F1/confusion/recall theo từng loại lỗi/FP-FN theo ID/độ trễ p50-p95, gắn nhãn `data_source` để không nhầm kết quả tổng hợp với thật, theo D-026).
- *Kiểm chứng thật, không giả lập:* `ImageFolderFrameSource` và `VideoFileFrameSource` được test bằng **ảnh PNG và video MP4 thật** ghi ra bằng `cv2.imwrite`/`cv2.VideoWriter` trong lúc test (đã xác nhận môi trường ghi/đọc video hoạt động), không chỉ mock. `UsbCameraFrameSource` chỉ test được đường lỗi (không có camera thật — hardware = NONE); đường thành công để dành P1.11.
- *Acceptance:* pipeline `FrameSource → preprocess → InferenceEngine → postprocess → InspectionResult` chạy được hoàn toàn trên ảnh tổng hợp; `evaluate()` cho ra đủ số liệu VT-01 (đã kiểm tra: recall(MARK) ≥ recall(SCRATCH) đúng như thiết kế "dễ/khó"); mọi kết quả gắn `data_source="synthetic"`.
- *Test:* 5 file mới, **65 test case** (`test_vision_synthetic.py` 14, `test_vision_sources.py` 17, `test_vision_preprocess.py` 9, `test_vision_baseline_postprocess.py` 15, `test_vision_evaluation.py` 10).
- *Kết quả chạy:* `cd edge && python -m pytest` → **286 passed, 1 skipped**, exit code 0.
- *Lỗi tự phát hiện và sửa qua test (2 việc):* (1) test đầu tiên cho "MARK dễ nhận ra hơn" dùng ngưỡng tuyệt đối sai (đường viền chỉ chiếm phần nhỏ ảnh 128×128 nên diff trung bình nhỏ hơn dự đoán) — sửa thành so sánh tương đối với "sàn nhiễu" thay vì số tuyệt đối; (2) test `uncertain_policy` ban đầu giả định băng UNCERTAIN rộng sẽ luôn bắt được điểm số baseline thật, nhưng baseline lại rất tự tin (bão hòa sigmoid) nên không rơi vào băng — sửa bằng một `InferenceEngine` giả cố định điểm số đúng ngay ngưỡng để cô lập đúng thứ cần test (logic `uncertain_policy` của `evaluate()`, không phải hành vi ngẫu nhiên của baseline).
- *Còn lại của P1.3 lúc đó (nay đã làm — xem mục dưới):* pipeline huấn luyện CNN nhỏ trên dữ liệu tổng hợp (smoke test) + xuất ONNX + `OnnxInferenceEngine`.
- *Blocker:* không (với phần đã làm).

### Chi tiết P1.3 (phần CNN/ONNX) — CNN training scaffold + ONNX inference ✅ DONE (2026-09-18, D-035)

- *Implementation:* `edge/src/msfc/vision/training.py` (không import từ `msfc.vision.__init__` — cần `torch`, các module khác không cần): `TrainingConfig`, `CapDataset` (dùng lại đúng `preprocess()` production dùng), `split_by_session()` (bắt buộc ≥3 session, không bao giờ âm thầm rơi về chia ngẫu nhiên theo index — đúng DATASET_SPEC.md mục 6), `TinyCapCNN` (3 conv block + `AdaptiveAvgPool2d` nên không phụ thuộc kích thước ảnh vào), `train_smoke_test()` (chọn epoch tốt nhất theo F1 trên tập val, lưu checkpoint), `export_onnx()`. `edge/src/msfc/vision/onnx_backend.py` (cũng không import từ `__init__` — cần `onnxruntime`): `OnnxInferenceEngine` cài đúng interface `InferenceEngine` (`.name`, `.version`, `.predict()`) nên **cắm thẳng vào `postprocess()`/`DecisionEngine` hiện có, không sửa gì ở hai nơi đó** (đúng mục tiêu ADR-0010).
- *Quyết định kỹ thuật khi export ONNX:* `torch.onnx.export` mặc định (dynamo) của PyTorch 2.13 cần thêm gói `onnxscript` (chưa cài); dùng lại exporter legacy (`dynamo=False`, chỉ cần gói `onnx` đã cài) — xác nhận bằng script thử độc lập trước khi viết code thật: sai lệch tối đa giữa PyTorch và ONNX Runtime trên cùng input ≈ 3,7e-9.
- *Test:* 2 file mới, **17 test case** — `test_vision_training_smoke.py` (12: `split_by_session` 3 case, `CapDataset`/`TinyCapCNN` 3 case, `TrainingConfig` validate 1 case, `train_smoke_test` end-to-end + reproducibility 2 case, `load_checkpoint` round-trip + missing-file 2 case, empty-samples 1 case) và `test_vision_onnx_inference_smoke.py` (5: construction/reject-missing-file, `predict()` hợp lệ, reject sai shape, **cắm vào `postprocess()`+`DecisionEngine` thật không sửa gì** — bằng chứng chính cho D-035, cross-check số ONNX Runtime khớp PyTorch trong 1e-4).
- *Kết quả chạy:* `cd edge && python -m pytest tests/unit/test_vision_training_smoke.py tests/unit/test_vision_onnx_inference_smoke.py -v` → **17 passed** (~23–25 s, CPU). `cd edge && python -m pytest` (toàn bộ) → **367 passed, 1 skipped** (tăng từ 350+1 — không có test nào cũ bị hỏng).
- *Artifact huấn luyện (bằng chứng cụ thể, không chỉ chạy trong `tmp_path` của pytest):* `ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/` — `checkpoint.pt` + `model.onnx` (không commit git, theo `ai/models/README.md`), `metrics.json`, `config.toml`, `checksum.txt`, `model_card.md`. Dataset: 3 phiên tổng hợp × 12 ảnh = 36 ảnh, `data_source=synthetic`.
- **Phát hiện trung thực (không che giấu, đúng chỉ thị PO):** giống hệt `ClassicCvBaseline` (R-28), `TinyCapCNN` sau 2 epoch trên 12 ảnh train **dự đoán mọi ảnh là GOOD** — accuracy=0.5, F1(DEFECT)=0.0, confusion `tp=0, fp=0, tn=6, fn=6` trên tập test (12 ảnh, phiên s03). Đây **không phải lỗi wiring** (đã xác nhận bằng cross-check ONNX khớp PyTorch, và pipeline `postprocess→DecisionEngine` chạy đúng với input này) mà là hệ quả của dataset tổng hợp quá nhỏ/quá khó (cùng nguyên nhân với R-28: nhiễu nền + lệch vị trí ngẫu nhiên) kết hợp với việc **cố tình không train lâu hơn** theo đúng chỉ thị PO. Chi tiết: [model_card.md](ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/model_card.md), quyết định D-035.
- *Blocker:* không (cho mục tiêu "chứng minh pipeline chạy end-to-end" — mục tiêu đã đạt). Độ chính xác AI thật vẫn cần dataset thật ở P1.11 (đã biết trước).

### Chi tiết P1.4 — Decision Engine ✅ DONE (2026-09-18)

- *Implementation:* `edge/src/msfc/decision/` (Layer 4, chỉ phụ thuộc `core`+`domain`): `policy.py` (`DecisionPolicy` — `uncertain_verdict` mặc định DEFECT theo FR-DEC-04, `deadline_ms`, `rules_version`); `engine.py` (`DecisionEngine.decide()` — luật "bất kỳ kênh nào DEFECT thì thắng" (fail-closed), UNCERTAIN theo policy, gắn `DECISION_LATE` khi vượt deadline; `to_verdict_command()` chuyển `DecisionRecord` thành `VerdictCommand`).
- *Acceptance:* `decision_id` suy trực tiếp từ `product_id` (không cần bộ đếm riêng, vì `product_id` đã duy nhất); mọi nhánh luật có test riêng (all-GOOD, any-DEFECT-thắng, UNCERTAIN theo 2 policy, DEFECT thắng cả UNCERTAIN); `late` tính đúng tại biên (`== deadline` không phải late, `> deadline` mới late).
- *Test:* 1 file mới, **20 test case** (`test_decision_engine.py`).
- *Lỗi tự phát hiện và sửa:* thông điệp lỗi thực tế của `DecisionError` khi đồng hồ lùi là "must not be before" chứ không chứa từ "backwards" như test ban đầu giả định — sửa lại regex test cho khớp thông điệp thật thay vì đổi thông điệp lỗi (thông điệp hiện tại đã đủ rõ ràng).
- *Kết quả chạy:* `cd edge && python -m pytest` → **306 passed, 1 skipped**.
- *Blocker:* không.

### Chi tiết P1.6 — Cell Controller Simulator ("ESP32 mock") ✅ DONE (2026-09-18)

- *Implementation:* `edge/src/msfc/sim/` (Layer N1-as-software; phụ thuộc `core`+`domain`+`contracts`+`comm` — package DUY NHẤT ngoài `services` được phép biết MQTT tồn tại, vì nhiệm vụ của nó chính là **đóng vai một thiết bị nói MQTT**): `codec.py` (domain → dict cho 5 loại message: product_detected, product_sorted, state_changed, fault, cell_state); `engine.py` (`SimCellController` — máy trạng thái đầy đủ BOOT→SELF_TEST→IDLE→STARTING→RUNNING→STOPPING cộng SAFE_STOP/FAULT/ESTOP; **một đồng hồ đơn (`self._now_mono_ms`), luôn tiến, không bao giờ dùng `mono_ms` của gói tin đến làm giờ của chính mình** — đúng nguyên tắc ARCHITECTURE.md "mono_ms giữa các thiết bị không so sánh được"; FIFO theo dõi sản phẩm; định tuyến PASSED/REJECTED; 8 mã lỗi F001/F010/F030/F031/F032/F033 + ma trận reset theo SAFETY_CONCEPT; E-stop và nút RESET là **lệnh gọi trực tiếp** (mô phỏng input phần cứng IF-HW-01/02), không phải qua MQTT — remote reset qua MQTT luôn bị từ chối khi ESTOP).
- *Quyết định thiết kế quan trọng phát hiện khi viết code (không phải khi test):* thiết kế nháp đầu tiên định lấy `now` từ `envelope["mono_ms"]` của gói tin MQTT đến (heartbeat/verdict/control) để làm mốc thời gian xử lý — **đây là lỗi khái niệm nghiêm trọng** vì `mono_ms` là đồng hồ của **bên gửi** (ví dụ edge01), hoàn toàn không thể so sánh với đồng hồ của Cell Controller. Đã sửa **trước khi viết test**: các handler MQTT dùng `self._now_mono_ms` (đồng hồ riêng của sim, chỉ tiến qua `tick()`/các lệnh có `now_mono_ms` tường minh), khớp đúng nguyên tắc đã ghi trong ARCHITECTURE.md mục 5.1 và ADR-0005.
- *Acceptance:* boot vào IDLE với động cơ tắt/relay hở/pusher thu (SAF-02/05/06); start/stop/set_speed/pusher_test đúng theo bảng trạng thái; mất heartbeat quá hạn → FAULT + cắt hết + không tự chạy lại; E-stop cắt ngay lập tức và **remote reset luôn bị từ chối** trong khi ESTOP; reset (local và remote) chỉ thành công khi nguyên nhân đã hết; hàng đợi tràn → F031; S2 rỗng → F030; không có verdict → REJECTED (mặc định) + F033; verdict trễ → F032; mọi message publish tự validate lại bằng `PayloadValidator` trước khi ra khỏi hệ thống.
- *Test:* 1 file mới, **38 test case** (`test_sim_cell_controller.py`), gồm cả đường đi qua MQTT thật (publish envelope lên `InMemoryBus`, không chỉ gọi hàm Python trực tiếp) và một test "mọi message đã publish đều hợp lệ theo đúng schema của nó".
- *Lỗi tự phát hiện và sửa qua test (2 việc, cả hai là lỗi trong TEST chứ không phải trong sim):* (1) một test gọi `detect_product` rồi `receive_verdict` với timestamp **lùi lại** — vi phạm chính quy tắc "một đồng hồ, luôn tiến" mà sim cố tình thực thi nghiêm ngặt; sửa bằng cách sắp lại thứ tự sự kiện trong test theo đúng trình tự thời gian thực; (2) một test heartbeat quên gửi heartbeat ban đầu trước nhịp `tick` đầu tiên, khiến sim hợp lý vào FAULT ngay (đúng thiết kế fail-safe) — sửa test để gửi heartbeat mồi trước, đúng với thực tế Edge Server phát heartbeat 5 Hz liên tục trước cả khi có lệnh START.
- *Kết quả chạy:* `cd edge && python -m pytest` → **344 passed, 1 skipped**.
- *Blocker:* không.

### Chi tiết Pipeline MVP end-to-end (P1.2+P1.4+P1.6+P1.7 nối lại) ✅ DONE (2026-09-18)

- *Implementation:* `edge/tests/integration/test_full_pipeline_mvp.py` — nối `FrameSource`/ảnh tổng hợp → tiền xử lý → `InferenceEngine` → `postprocess` → `DecisionEngine` → `VerdictCommand` → `SimCellController` → kết quả PASSED/REJECTED, đúng sơ đồ pipeline MVP trong chỉ thị của PO. **Chưa có `msfc.services`** (thuộc P1.14, ngoài phạm vi lượt này) nên một class `_Pipeline` nhỏ trong chính file test đóng vai trò điều phối tạm thời.
- *Phát hiện quan trọng (đã báo cáo trung thực, không che giấu — đúng nguyên tắc ADR-0010):* khi nối `ClassicCvBaseline` thật vào pipeline, phát hiện bộ phân loại **hầu như không phân biệt được GOOD và DEFECT** trên dữ liệu tổng hợp mặc định (đo thực nghiệm: điểm khác biệt trung bình so với ảnh mẫu ≈ 21,9 cho GOOD so với 21,9–23,2 cho DEFECT — gần như trùng nhau). Nguyên nhân: độ lệch vị trí ngẫu nhiên (±8 px) khi lấy trung bình nhiều ảnh mẫu làm mờ template, cộng với nhiễu cảm biến (std=3/kênh màu) lớn hơn tín hiệu lỗi thật. Đây là **giới hạn thật của cách tiếp cận "khoảng cách tới template trung bình"**, không phải lỗi nối dây. Xử lý: các test đo **độ đúng của luồng dữ liệu** (routing/tracking/fault handling) dùng một `_OracleVisionEngine` xác định (biết trước nhãn), tách bạch khỏi vấn đề độ chính xác mô hình; giữ lại **một test riêng** chạy `ClassicCvBaseline` thật để chứng minh nó khớp đúng interface `InferenceEngine` trong toàn bộ pipeline (không khẳng định độ chính xác). Đã ghi vào [RISK_REGISTER.md](docs/RISK_REGISTER.md) (R-28) và cần xử lý trước khi dùng cho dataset thật ở P1.11 (P1.11 dùng dataset thật, không phải dữ liệu tổng hợp, nên đây không chặn P1.11 nhưng chặn việc tin tưởng baseline hiện tại nếu áp dụng nguyên trạng).
- *Acceptance:* verdict GOOD → PASSED, DEFECT → REJECTED trong 100% trường hợp thử; `margin_ms > 0` mọi sản phẩm; `product_id` tăng dần liên tục; không có verdict → REJECTED + F033; mất heartbeat giữa lúc chạy → FAULT + cắt hết, phục hồi được sau khi heartbeat trở lại và có lệnh reset; toàn bộ message trong một lượt chạy nhiều sản phẩm đều hợp lệ theo schema.
- *Test:* 1 file mới, **6 test case**.
- *Kết quả chạy:* `cd edge && python -m pytest` → **350 passed, 1 skipped**, exit code 0.
- *Blocker:* không (cho phần wiring). Độ chính xác AI thật vẫn cần dataset thật + hiệu chỉnh lại ở P1.11 (đã biết trước, không phải phát hiện mới ở đó).

### Chi tiết P1.5 — Firmware core_logic (host-testable) 🟡 DONE một phần (2026-09-18, D-036/D-037)

- *Kiểm tra môi trường trước tiên (theo chỉ thị PO):* `idf.py` — **MISSING**, không có `IDF_PATH`, không có thư mục `Espressif`/`esp` nào trên máy. `gcc` — `tools/check_env.py` báo MISSING (không có trên PATH), nhưng kiểm tra trực tiếp phát hiện **MSYS2 UCRT64 đã cài sẵn** (`C:\msys64\ucrt64\bin\gcc.exe`, phiên bản 16.1.0) — chỉ cần thêm vào PATH để dùng, xác nhận bằng cách biên dịch+chạy một chương trình C thử nghiệm thành công. `cmake`/`ninja`/`make` — không tìm thấy trong MSYS2 UCRT64 (không cần cho phần này vì gọi `gcc` trực tiếp, không qua build system).
- *Quyết định:* không sửa PATH hệ thống (ngoài thẩm quyền Claude Inc — xem D-036); dùng `PATH="/c/msys64/ucrt64/bin:$PATH"` chỉ trong phạm vi script build. Vì `idf.py` vẫn thiếu, **không build được firmware thật cho chip ESP32** — chỉ implement + build + test phần `core_logic` không phụ thuộc ESP-IDF (đúng README rule 1, đúng phạm vi PO liệt kê: state machine, command parser, communication interface boundary, motor/servo command interface, fault handling, safe state, watchdog abstraction, logging, HAL boundary).
- *Implementation (`firmware/cell_controller/components/`):*
  - `core_logic/cell_sm.c/.h` — máy trạng thái 9 trạng thái (khớp `msfc.domain.enums.MachineState`), ưu tiên ESTOP > SAFE_STOP > FAULT > lệnh tường minh (khớp HARDWARE_INTERFACE.md).
  - `core_logic/fault_manager.c/.h` — tập con mã lỗi firmware tự phát hiện được (F001, F010, F050, F051 — khớp chuỗi mã với `msfc.domain.faults.FAULT_CATALOG`), latch/ack.
  - `core_logic/debounce.c/.h` — lọc chống dội cho IF-HW-02/03.
  - `core_logic/safety_supervisor.c/.h` — nơi DUY NHẤT quyết định `hal_outputs_t` (CODING_STANDARDS rule 4): ngoài `RUNNING` thì motor/relay/pusher luôn tắt (SF-07/SF-10) bất kể giá trị yêu cầu.
  - `core_logic/cmd_handler.c/.h` — parser lệnh START/STOP/RESET/SET_SPEED/PUSHER_TEST → ACCEPTED/REJECTED + `reject_reason_t` khớp `msfc.domain.enums.RejectReason`.
  - `core_logic/watchdog.c/.h` — bộ đếm timeout thuần logic (SF-06), dùng chung được trên host và ESP32 sau này (không cần hal_host_mock riêng).
  - `core_logic/logger.c/.h` — logger có mức, chỉ dùng `<stdio.h>`.
  - `core_logic/comm_link.h` — **chỉ là interface** (struct con trỏ hàm) cho boundary giao tiếp; **chưa nối esp-mqtt thật** (cần ESP-IDF, ngoài phạm vi vì hardware=NONE) — đây là "communication interface" theo đúng nghĩa PO yêu cầu (ranh giới kiến trúc, không phải MQTT client chạy được).
  - `hal/hal_interface.h` — đúng hợp đồng `hal_inputs_t`/`hal_outputs_t`/`hal_inputs_read`/`hal_outputs_write`/`hal_selftest` từ [docs/HARDWARE_INTERFACE.md](docs/HARDWARE_INTERFACE.md) mục 4, chỉ đổi `esp_err_t` → `hal_status_t` (kiểu trung lập, vì `core_logic` không được phụ thuộc ESP-IDF — tín hiệu logic giữ nguyên 100%).
  - `hal/hal_host_mock.c/.h` — HAL giả cho test host (bơm input theo kịch bản, đọc lại output đã ghi).
- *Test (`test_host/`, 7 file, chạy bằng `bash firmware/cell_controller/test_host/build_and_run.sh`):* **131/131 check PASS**, biên dịch với `-std=c99 -Wall -Wextra -Werror` (0 warning) — `test_cell_sm.c` (25, gồm ưu tiên ESTOP đè FAULT+SAFE_STOP cùng lúc), `test_fault_manager.c` (15, gồm đối chiếu chuỗi mã lỗi với Python), `test_debounce.c` (9), `test_safety_supervisor.c` (42, gồm mọi trạng thái ngoài RUNNING đều tắt output kể cả khi yêu cầu bật), `test_cmd_handler.c` (15), `test_watchdog.c` (15), `test_hal_boundary_integration.c` (10 — mô phỏng dây E-stop bị đứt qua `hal_host_mock`, xác nhận motor/relay tắt trong đúng 1 chu kỳ, tương tự `tests/integration/test_full_pipeline_mvp.py` bên Python).
- *Không dùng Unity thật* (ADR-0006 có nhắc tới Unity) — dùng một harness assert tối thiểu tự viết (`test_util.h`, không thêm dependency ngoài chưa được duyệt); cấu trúc đủ giống Unity để đổi sau này không tốn nhiều công.
- *Chưa làm (nằm ngoài 10 ưu tiên PO liệt kê lượt này, để BACKLOG):* `product_tracker` (FIFO S1→S2), `heartbeat_monitor`, `timing_stats` — 3 module này thuộc P1-06/P1-07 trong kế hoạch gốc của README, không nằm trong danh sách ưu tiên PO đưa ra cho lượt "Close Phase 1 Software Gate".
- *Kết quả:* **P1.5 KHÔNG đánh dấu DONE toàn bộ** — chỉ phần `core_logic` host-testable DONE. Build thật cho chip ESP32 (`idf.py build`) **vẫn BLOCKED** vì thiếu ESP-IDF SDK. Không giả vờ đã build cho ESP32.
- *Blocker còn lại:* cài ESP-IDF 5.x (miễn phí, cần PO thao tác — xem báo cáo lượt này để lấy command).

## Phase 2 — Software-only Safety & Interlock (2026-09-18)

> Chỉ thị PO: "PO APPROVAL — START PHASE 2 — SOFTWARE-ONLY SAFETY & INTERLOCK". Hardware = NONE, procurement chưa duyệt — toàn bộ Phase 2 chạy trên host, không phần cứng. **SOFTWARE E-STOP SIMULATION != PHYSICAL E-STOP VALIDATION** (nhắc lại theo đúng yêu cầu PO — không claim tương đương E-stop vật lý).

| ID | Task | Trạng thái |
|---|---|---|
| P2.1 | Safety State Machine (SAFE_IDLE/READY/RUNNING/FAULT/ESTOP/RECOVERY — view suy ra từ `cell_sm`) | ✅ **DONE** |
| P2.2 | Software E-STOP event: chặn lệnh mới, chặn actuator, cần reset+confirm để phục hồi, quan sát được | ✅ **DONE** |
| P2.3 | Interlock matrix (8 điều kiện: ESTOP, safety fault, comm loss, invalid command, motor fault, sensor fault, not ready, recovery not completed) | ✅ **DONE** |
| P2.4 | Safe state: motor stop + actuator an toàn + không lệnh chuyển động mới khi vi phạm an toàn | ✅ **DONE** (tái dùng `safety_supervisor.c` P1, không sửa) |
| P2.5 | Communication loss simulation (normal/timeout/disconnect/recovery) | ✅ **DONE** |
| P2.6 | Watchdog integration (bình thường/mất nhịp/timeout/phục hồi/lặp lại) | ✅ **DONE** (tái dùng `watchdog.c` P1, xem D-039 cho lý do không dùng `watchdog_check()` trực tiếp) |
| P2.7 | Invalid/malformed command handling | ✅ **DONE** |
| P2.8 | Deterministic fault recovery rules (không tự động phục hồi) | ✅ **DONE** |
| P2.9 | Software safety simulator — 12 kịch bản PO liệt kê | ✅ **DONE** |
| P2.10 | Testing (unit/integration, targeted trước, full suite tại gate) | ✅ **DONE** |
| P2.11 | Documentation | ✅ **DONE** (mục này) |

### Chi tiết Phase 2 — `safety_interlock.h/.c` ✅ DONE (2026-09-18)

- *Nguyên tắc thiết kế:* **thuần cộng thêm (additive)** — không sửa một dòng nào trong `cell_sm.c`, `fault_manager.c`, `watchdog.c`, `cmd_handler.c`, `hal_interface.h`, `hal_host_mock.c` (P1). Toàn bộ Phase 2 nằm trong 2 file mới: `firmware/cell_controller/components/core_logic/safety_interlock.h/.c`.
- *P2.1 — Safety state view:* `safety_state_t` (6 giá trị PO đặt tên) suy ra từ `cell_sm_t.state` (9 trạng thái, không đổi) qua `safety_interlock_state()`. Ánh xạ và lý do: xem **D-038**. `RECOVERY` là khái niệm mới thật sự (cờ `recovery_pending`), không có trong P1.
- *P2.2 — Software E-STOP:* `safety_interlock_update(..., estop_active, ...)` → `cell_sm` chuyển ESTOP ngay (ưu tiên cao nhất, logic P1 không đổi); `safety_interlock_dispatch()` chặn mọi lệnh chuyển động (START/SET_SPEED/PUSHER_TEST) qua `cmd_handler`'s `REJECT_ESTOP_LATCHED` (P1, không đổi); phục hồi cần RESET (chấp nhận khi hết ESTOP) **rồi** `safety_interlock_confirm_recovery()` — không tự động. Trạng thái quan sát được qua `safety_interlock_state()` + `safety_state_name()`. **Ghi rõ trong header:** đây là mô phỏng phần mềm, KHÔNG phải xác nhận E-stop vật lý (kênh cứng SAF-01/IF-HW-01 tách biệt hoàn toàn, không phụ thuộc code).
- *P2.3 — Interlock matrix (8 điều kiện):* ESTOP (cell_sm), safety fault (`fault_manager` — F050 self-test-failed tái dùng), comm loss (watchdog, D-039), invalid command (`cmd_handler`'s `REJECT_INVALID_PARAMS`, tái dùng), motor fault (mới, `interlock_reject_t`), sensor fault (mới), system not ready (`cmd_handler`'s `REJECT_NOT_IDLE`, tái dùng), recovery not completed (mới, cờ `recovery_pending`). Lý do không thêm mã lỗi catalog mới cho motor/sensor fault (không sửa `msfc.domain.faults`/`fault_manager.c`): **D-040**.
- *P2.4 — Safe state:* tái dùng nguyên vẹn `safety_supervisor.c` (P1) — nơi DUY NHẤT quyết định `hal_outputs_t`, đã đảm bảo motor/relay/pusher tắt ngoài RUNNING từ P1. Phase 2 không cần sửa gì ở đây; chỉ đảm bảo `safety_interlock` không cho phép trạng thái RUNNING xảy ra khi có interlock vi phạm.
- *P2.5/P2.6 — Comm loss + watchdog:* `safety_interlock_t` bọc một `watchdog_t` (P1, không sửa), cho vào qua `safety_interlock_feed_comm_heartbeat()`. Chi tiết kỹ thuật quan trọng: **không** dùng `watchdog_check()` của P1 (chốt vĩnh viễn) — xem D-039.
- *P2.7 — Invalid/malformed command:* unknown command (giá trị `cmd_action_t` ngoài dải — `default:` của `cmd_handler` xử lý), invalid parameter (`SET_SPEED` ngoài 0–100), lệnh chuyển động khi ESTOP/FAULT, lệnh trước READY, invalid state transition (`STOP` khi đang IDLE) — toàn bộ có `interlock_ack_t` xác định (result + lý do).
- *P2.8 — Deterministic recovery:* mỗi loại lỗi (ESTOP, motor fault, sensor fault, self-test failure, comm loss) có bảng trigger→state→blocked→reset condition→recovery condition→final state riêng, kiểm bằng test (`test_safety_interlock_recovery.c`). "Không tự động phục hồi": `safety_interlock_confirm_recovery()` re-check toàn bộ điều kiện tại thời điểm gọi — nếu có điều kiện mới xuất hiện giữa RESET và confirm, confirm thất bại (test `test_confirm_recovery_blocked_by_new_condition`).
- *P2.9 — Simulator:* `test_safety_scenarios.c` — đúng 12 kịch bản PO liệt kê, mỗi kịch bản in tên + assert kết quả xác định.
- *Test:* 4 file mới, **131 check PASS** (`test_safety_interlock_core.c` 34, `test_safety_interlock_comm_loss.c` 43, `test_safety_interlock_recovery.c` 27, `test_safety_scenarios.c` 27). Cộng 131 check P1 = **262/262 PASS**, `-std=c99 -Wall -Wextra -Werror` không warning.
- *Kết quả Python (regression, không đổi code):* `cd edge && python -m pytest` → **367 passed, 1 skipped** — không có gì hỏng.
- *Blocker:* không, cho phạm vi software-only. ESP32 target build, real hardware validation, physical E-stop validation đều **PENDING** — xem [PHASE2_COMPLETION_REPORT.md](PHASE2_COMPLETION_REPORT.md).

## Phase 3 — Software-only OCR / Expiry / Label Verification (2026-09-18)

> Chỉ thị PO: "START PHASE 3 — SOFTWARE-ONLY OCR / EXPIRY / LABEL VERIFICATION". Hardware = NONE, procurement chưa duyệt — toàn bộ Phase 3 chạy trên host bằng ảnh tổng hợp, không camera thật, không dịch vụ OCR thật.

| ID | Task | Trạng thái |
|---|---|---|
| P3.1 | OCR domain model | ✅ **DONE** |
| P3.2 | OCR engine abstraction (Mock OCR → cùng interface → Real OCR sau này) | ✅ **DONE** |
| P3.3 | Image preprocessing (grayscale/resize/contrast/threshold/denoise/crop/deskew) | ✅ **DONE** |
| P3.4 | Text normalization | ✅ **DONE** |
| P3.5 | Date extraction (5 định dạng: DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD, YYYY-MM-DD, MM/YYYY) | ✅ **DONE** |
| P3.6 | Date validation (cú pháp, lịch, so với ngày tham chiếu, thiếu, mơ hồ, không tồn tại) | ✅ **DONE** |
| P3.7 | Label/product validation (cấu hình được, không hard-code sản phẩm cụ thể) | ✅ **DONE** |
| P3.8 | Result classification (GOOD/DEFECT/UNCERTAIN) | ✅ **DONE** |
| P3.9 | Decision Engine integration (không sửa `msfc.decision`) | ✅ **DONE** |
| P3.10 | Test fixtures (12 kịch bản PO liệt kê) | ✅ **DONE** |
| P3.11 | Simulation (end-to-end: ảnh → tiền xử lý → Mock OCR → chuẩn hóa → trích xuất → kiểm tra → phân loại → quyết định) | ✅ **DONE** |
| P3.12 | Error handling (engine lỗi, output dị dạng, không có text, confidence/date không hợp lệ, preprocessing lỗi) | ✅ **DONE** |
| P3.13 | Testing (targeted trước, full regression tại gate) | ✅ **DONE** |
| P3.14 | Documentation | ✅ **DONE** (mục này) |

### Chi tiết Phase 3 — `msfc.ocr` ✅ DONE (2026-09-18)

- *Nguyên tắc thiết kế:* `msfc.ocr` là package **mới**, Layer 3, anh em cùng cấp với `msfc.vision` — `edge/tests/unit/test_layer_dependencies.py` (Phase 0) đã khai báo sẵn `"ocr": {"core", "domain"}` từ trước, nên package mới **tự động đúng luật layer**, không cần sửa test đó. Không sửa bất kỳ file P1/P2 nào ngoài việc thêm `OcrError` vào `msfc/core/errors.py` (theo đúng pattern `VisionError`/`DecisionError`/`SimulationError` đã có).
- *P3.1 — Domain model (`ocr/models.py`):* `BoundingBox`, `OcrOutput`, `OcrReasonCode` (đúng 6 mã FR-OCR-04 từ Phase 0 — docs/REQUIREMENTS.md, không thêm mã mới — D-042), `DetectedField`, `DateCandidate`, `DateExtractionResult`, `OcrValidationResult`.
- *P3.2 — Engine abstraction (`ocr/engine.py`):* `OcrEngine` Protocol (khớp hình dạng `msfc.vision.InferenceEngine`), `MockOcrEngine` (output cố định), `FixtureOcrEngine` (điều khiển tường minh qua `set_next_output()`, tái dùng đúng pattern `_OracleVisionEngine` của P1 — **một lỗi thật đã bắt được trước khi viết test**: thiết kế đầu tiên tra `id(image)` bị vỡ vì `preprocess()` luôn trả mảng mới — D-044).
- *P3.3 — Preprocessing (`ocr/preprocess.py`):* `RoiConfig` riêng (không import `msfc.vision`, D-041), `crop_roi`/`resize`/`to_grayscale`/`adjust_contrast`/`denoise`/`adaptive_threshold`/`estimate_skew_deg`/`deskew`, `preprocess()` gộp theo `PreprocessConfig` (mỗi bước tùy chọn).
- *P3.4/P3.5 — Text + date extraction (`ocr/text.py`):* `normalize_text` chỉ làm sạch không tranh cãi (khoảng trắng, hoa/thường); sửa nhầm lẫn ký tự OCR (O→0, I/l→1, S→5, B→8) **chỉ trong phạm vi chuỗi đã có hình dạng ngày tháng**, không áp dụng toàn văn bản (đúng "không tự sửa văn bản không chắc chắn thành ngày hợp lệ"). Đúng 5 định dạng PO liệt kê, thử theo thứ tự cố định.
- *P3.6/P3.7 — Validation (`ocr/validate.py`):* `LabelValidationConfig` (required_substrings, expected_product_id_pattern, max_skew_deg, min_confidence — không hard-code sản phẩm cụ thể); `validate_label()` theo thứ tự ưu tiên cố định: rỗng→UNREADABLE, lệch góc→LABEL_MISALIGNED, thiếu field bắt buộc→LABEL_MISSING, không thấy ngày/mơ hồ/không hợp lệ lịch→FORMAT_INVALID (mơ hồ còn gắn cờ `ambiguous=True` riêng), hết hạn→EXPIRED, còn lại→OK.
- *P3.8/P3.9 — Classify + Decision integration (`ocr/classify.py`):* `classify()` — UNREADABLE và `ambiguous=True` luôn → UNCERTAIN (không ép về GOOD/DEFECT); confidence dưới ngưỡng → UNCERTAIN bất kể reason; OK → GOOD; 4 reason còn lại → DEFECT. `to_inspection_result()` bọc thành đúng `msfc.domain.InspectionResult` — **cắm thẳng vào `msfc.decision.DecisionEngine.decide()` hiện có, không sửa gì** (đã có sẵn thiết kế đa kênh từ P1, comment trong `engine.py` đã ghi "OCR joins in Phase 3" từ Phase 0).
- *P3.10/P3.11 — Fixtures + simulation (`ocr/synthetic.py`):* đúng 12 kịch bản PO liệt kê, ảnh render pixel thật (`cv2.putText`) nhưng `FixtureOcrEngine` đọc ground-truth từ metadata, không phân tích pixel (D-043, giống D-026 cho vision). LABEL_MISALIGNED không nằm trong 12 kịch bản PO liệt kê — được test riêng bằng unit test tường minh (`test_ocr_validate.py`).
- *P3.12 — Error handling (`ocr/pipeline.py`):* `run_ocr_pipeline()` — lỗi OCR engine (exception) → UNREADABLE xác định, không crash; lỗi cấu hình preprocessing (ROI sai) → raise `OcrError` (lỗi của người gọi, không phải nội dung OCR, không nên nuốt lặng lẽ).
- *Test:* 9 file mới, **103 test case** (`test_ocr_models.py` 8, `test_ocr_engine.py` 6, `test_ocr_preprocess.py` 17, `test_ocr_text.py` 17, `test_ocr_validate.py` 17, `test_ocr_classify.py` 11, `test_ocr_pipeline.py` 7, `test_ocr_fixtures.py` 15, `tests/integration/test_ocr_decision_integration.py` 5).
- *Kết quả chạy:* `cd edge && python -m pytest` → **470 passed, 1 skipped** (tăng đúng 103 từ 367+1; **0 test cũ hỏng**). `test_layer_dependencies.py` xác nhận `msfc.ocr` đúng luật layer.
- *Blocker:* không, cho phạm vi software-only. Chưa validate OCR trên ảnh camera/sản phẩm thật — xem [PHASE3_COMPLETION_REPORT.md](PHASE3_COMPLETION_REPORT.md).

## Phase 4 — Software-only OEE / Machine Monitoring (2026-09-18)

> Chỉ thị PO: "START PHASE 4 — SOFTWARE-ONLY OEE / MACHINE MONITORING". Hardware = NONE, procurement chưa duyệt — toàn bộ chạy bằng simulation/sự kiện tổng hợp, không cảm biến/ESP32/PLC/camera/MQTT broker thật. **P2 an toàn/interlock vẫn có thẩm quyền tối cao — OEE chỉ quan sát, không bao giờ ghi đè.**

| ID | Task | Trạng thái |
|---|---|---|
| P4.1 | OEE domain model | ✅ **DONE** |
| P4.2 | Machine state model (tái dùng `MachineState` P1, không tạo enum mới) | ✅ **DONE** |
| P4.3 | Machine event model | ✅ **DONE** |
| P4.4 | Downtime model (phân loại + quy tắc tường minh) | ✅ **DONE** |
| P4.5 | Availability | ✅ **DONE** |
| P4.6 | Performance | ✅ **DONE** |
| P4.7 | Quality (UNCERTAIN đã ghi quyết định — D-045) | ✅ **DONE** |
| P4.8 | OEE calculation | ✅ **DONE** |
| P4.9 | Shift / production session | ✅ **DONE** |
| P4.10 | Cycle-time monitoring | ✅ **DONE** |
| P4.11 | Machine monitoring layer | ✅ **DONE** |
| P4.12 | Fault/downtime reasoning (OEE quan sát, không can thiệp an toàn) | ✅ **DONE** (đảm bảo bằng kiến trúc layer, không chỉ kỷ luật code) |
| P4.13 | Simulation engine (10 kịch bản PO liệt kê) | ✅ **DONE** |
| P4.14 | Test fixtures (15 kịch bản PO liệt kê) | ✅ **DONE** |
| P4.15 | Edge cases | ✅ **DONE** |
| P4.16 | Decision/architecture integration | ✅ **DONE** |
| P4.17 | Data storage abstraction | ✅ **DONE** (interface + in-memory only) |
| P4.18 | MQTT compatibility (schema draft có sẵn, không cài broker) | ✅ **DONE** |
| P4.19 | Dashboard compatibility (không xây dashboard) | ✅ **DONE** (chỉ expose model sạch) |
| P4.20 | Testing | ✅ **DONE** |
| P4.21 | Documentation | ✅ **DONE** (mục này) |
| P4.22 | Code quality | ✅ **DONE** |

### Chi tiết Phase 4 — `msfc.analytics` ✅ DONE (2026-09-18)

- *Kiểm tra trước khi viết code (rule 1, P4.16):* `ARCHITECTURE.md` đã khai báo sẵn `msfc.analytics` (Layer 7, "tính OEE, phân tích sức khỏe", phụ thuộc `core`+`domain`) và `edge/tests/unit/test_layer_dependencies.py` (P0) đã có sẵn `"analytics": {"core", "domain"}` — package mới tự động đúng luật, không cần sửa test đó. `docs/REQUIREMENTS.md` đã có sẵn FR-OEE-01..05 (mô hình trạng thái máy RUNNING/IDLE/STOPPED/SAFE_STOP/FAULT, đếm tổng/GOOD/DEFECT, downtime có/không kế hoạch, Availability/Performance/Quality/OEE theo cửa sổ/ca). `contracts/schemas/oee_metrics.v1.json` đã có sẵn (DRAFT, Phase 0) với 4 trường `availability/performance/quality/oee` — dùng làm hình dạng payload tham chiếu.
- *Tái dùng tối đa (P4.16, "reuse compatible interfaces"):* **không tạo enum trạng thái máy mới** — dùng thẳng `msfc.domain.enums.MachineState` (9 giá trị, P1) + `NON_PRODUCTION_STATES` có sẵn để suy ra downtime. **Không tạo bộ đếm mới** — dùng thẳng `msfc.domain.state.Counters` (detected/passed/rejected/no_decision, P1) làm nguồn sự thật cho total/good/defect count. Factory function xây `MachineEvent` từ đúng `StateChangedEvent`/`ProductDetectedEvent`/`ProductSortedEvent`/`FaultReport` (P1, không sửa) — xác nhận bằng test tích hợp dùng đúng các dataclass đó, không phải double tự chế.
- *Implementation (`edge/src/msfc/analytics/`):* `models.py` (P4.1/P4.4/P4.10/P4.11: `OeeResult`, `DowntimeCategory`, `DowntimeInterval`, `CycleStatistics`, `MachineStatus`), `events.py` (P4.3: `MachineEvent`, `MachineEventType`, 4 factory function), `calculations.py` (P4.5-P4.8: hàm thuần, không state), `session.py` (P4.9: `ProductionSession` — đối tượng có trạng thái duy nhất trong package), `monitor.py` (P4.11: `MachineMonitor`), `repository.py` (P4.17), `simulate.py` (P4.13: 10 kịch bản).
- *P4.7/D-045 — UNCERTAIN không tới được OEE:* đọc lại kiến trúc P1 thay vì tự chọn — `DecisionEngine` đã giải quyết UNCERTAIN thành GOOD/DEFECT theo `DecisionPolicy` **trước khi** sort; `SortAction` chỉ có PASSED/REJECTED. Ghi quyết định thay vì âm thầm chọn (đúng chỉ thị P4.7).
- *P4.4/D-047/D-049 — diễn giải OEE quan trọng, ghi rõ:* STARTING/STOPPING tính là run time (không downtime); PLANNED/MAINTENANCE bị **loại khỏi mẫu số** Availability (đúng định nghĩa Nakajima kinh điển) thay vì trừ vào tử số như UNPLANNED/FAULT/EMERGENCY_STOP/IDLE — minh chứng bằng 2 kịch bản cùng hình dạng khác category (`scenario_planned_downtime` OEE=1.0 vs `scenario_unplanned_downtime` OEE giảm).
- *D-046 — MAINTENANCE:* không thêm giá trị mới vào `MachineState` (P1) — chỉ là nhãn `DowntimeCategory.MAINTENANCE` gán tường minh qua `MachineEvent.category`.
- *D-048 — xung đột phát hiện giữa các phase, không tự sửa lặng lẽ:* `oee_metrics.v1.json` (draft, P0) giới hạn performance/oee tối đa 1.0, nhưng phép tính thật có thể vượt 1.0 (chu kỳ thực nhanh hơn ideal cấu hình — không phải lỗi). Không sửa file schema; chỉ clamp tại đúng một hàm chuyển đổi payload (`to_oee_metrics_v1_payload()`), số liệu gốc (`OeeResult`) giữ nguyên. Đã ghi Q-18 chờ PO.
- *D-050 — layer boundary:* `OeeSnapshotRepository`/`InMemoryOeeSnapshotRepository` (P4.17) nằm trong `msfc.analytics` chứ không phải `msfc.storage` (dù đã khai báo sẵn từ P0) vì `test_layer_dependencies.py` không cho `analytics` phụ thuộc `storage` — không tự ý nới luật layer.
- *P4.12 — an toàn tối cao của P2:* `msfc.analytics` **không thể** import `msfc.sim`/`msfc.decision`/firmware (luật layer chỉ cho `core`+`domain`) — đây là **bảo đảm kiến trúc**, không chỉ kỷ luật lập trình. Không có hàm nào trong package gửi lệnh hay đổi trạng thái an toàn.
- *Một lỗi thiết kế thật bắt được trước khi viết test đầy đủ (giống phong cách D-039/D-044 ở các phase trước):* kịch bản đầu tiên cho `scenario_normal_production` gây lỗi `run_time_ms must be > 0` — nguyên nhân: trạng thái khởi tạo mặc định là BOOT (downtime theo `DEFAULT_STATE_CATEGORY`) không bao giờ đóng lại vì kịch bản không phát sự kiện chuyển trạng thái nào. Phát hiện bằng script chạy thử cả 10 kịch bản trước khi viết test, sửa bằng cách khởi tạo session ở RUNNING cho các kịch bản tập trung vào sản xuất (đã biết trước qua P1/P2, không cần kiểm lại chuỗi boot). Một lỗi thứ hai (chuyển trạng thái giữa hai non-production states khác nhau, vd ESTOP→IDLE, không đóng/mở lại khoảng downtime đúng category) cũng bắt được cùng cách, sửa trong `from_state_changed()`.
- *Test:* 7 file unit mới, **98 test case mới** (`test_analytics_models.py` 10, `test_analytics_events.py` 14, `test_analytics_calculations.py` 25, `test_analytics_session.py` 22, `test_analytics_monitor.py` 5, `test_analytics_repository.py` 5, `test_analytics_fixtures.py` 17) + 1 file integration mới (`tests/integration/test_analytics_domain_integration.py`, 1 test, dùng đúng dataclass P1 thật) = **99 test mới**.
- *Kết quả chạy:* `cd edge && python -m pytest` → **569 passed, 1 skipped** (tăng đúng 99 từ 470+1; **0 test cũ hỏng**). Firmware C không đụng tới (không cần sửa) — vẫn 262/262.
- *Blocker:* không, cho phạm vi software-only. ESP32 target build, real hardware validation, physical E-stop validation, real OCR validation, real vision AI validation, real OEE validation đều **PENDING** — xem [PHASE4_COMPLETION_REPORT.md](PHASE4_COMPLETION_REPORT.md).

## Phase 5 — Software-only Machine Health / Anomaly Detection / Predictive Maintenance (2026-09-18)

> Chỉ thị PO: "START PHASE 5 — SOFTWARE-ONLY MACHINE HEALTH / ANOMALY DETECTION / PREDICTIVE MAINTENANCE". Hardware = NONE, không có dataset cảm biến máy thật — **KHÔNG claim độ chính xác predictive maintenance thật**. Tiếp tục nằm trong `msfc.analytics` (ARCHITECTURE.md đã gán package này cho cả OEE lẫn "phân tích sức khỏe", Phase 4+5, từ Phase 0).

| ID | Task | Trạng thái |
|---|---|---|
| P5.1 | Machine health domain model | ✅ **DONE** |
| P5.2 | Sensor abstraction (Mock → cùng interface → cảm biến thật sau này) | ✅ **DONE** |
| P5.3 | Sensor data quality | ✅ **DONE** |
| P5.4 | Feature extraction | ✅ **DONE** |
| P5.5 | Baseline model (cấu hình được, không hard-code máy thật) | ✅ **DONE** |
| P5.6 | Anomaly detection (threshold/deviation/trend/sensor-quality) | ✅ **DONE** |
| P5.7 | Health score (0.0–1.0, không claim sức khỏe vật lý thật) | ✅ **DONE** |
| P5.8 | Anomaly severity + kết hợp nhiều bất thường | ✅ **DONE** |
| P5.9 | Machine health event | ✅ **DONE** |
| P5.10 | Machine health monitor | ✅ **DONE** |
| P5.11/P5.12 | Predictive model abstraction + input contract (KHÔNG train gì) | ✅ **DONE** |
| P5.13/P5.14 | Simulation + fixtures (15 kịch bản PO liệt kê) | ✅ **DONE** |
| P5.15 | Edge cases | ✅ **DONE** |
| P5.16/P5.17 | Tích hợp P4 (chỉ CRITICAL → cầu nối tùy chọn, không tự động hóa) | ✅ **DONE** |
| P5.18 | MQTT contract compatibility (schema draft có sẵn, không cài broker) | ✅ **DONE** |
| P5.19 | Storage abstraction | ✅ **DONE** (interface + in-memory only) |
| P5.20 | Chuẩn bị dataset thật tương lai (tài liệu) | ✅ **DONE** (mục này + model_input_contract) |
| P5.21 | Evaluation framework (chỉ khung, không claim số liệu thật) | ✅ **DONE** |
| P5.22 | Error handling | ✅ **DONE** |
| P5.23 | Testing | ✅ **DONE** |
| P5.24 | Documentation | ✅ **DONE** (mục này) |
| P5.25 | Code quality | ✅ **DONE** |

### Chi tiết Phase 5 — machine health trong `msfc.analytics` ✅ DONE (2026-09-18)

- *Kiểm tra trước khi viết code (rule "Architecture Rule", P5):* `ARCHITECTURE.md` mục 7.2 đã gán `msfc.analytics` cho CẢ OEE (Phase 4) LẪN "phân tích sức khỏe" (Phase 5) từ Phase 0 — không tạo package `msfc.health` mới (sẽ là "duplicate/conflicting" đúng như PO cảnh báo tránh). `docs/REQUIREMENTS.md` đã có sẵn FR-HLT-01..07 (rung động/nhiệt độ/dòng điện, baseline, NORMAL/WARNING/CRITICAL, phát hiện bất thường thống kê, lỗi cảm biến, sự kiện sức khỏe, **"Không gọi là predictive maintenance AI khi chưa có dữ liệu suy giảm đủ tin cậy"** — đúng nguyên văn tinh thần chỉ thị PO lượt này). `contracts/schemas/health_state.v1.json` và `health_features.v1.json` (2 DRAFT có sẵn từ Phase 0) — xung đột với 5-state/8-sensor-type của chỉ thị lượt này được ghi rõ, không sửa 2 file (D-051).
- *Tái dùng (P5.16):* domain model mới hoàn toàn (chưa có khái niệm sức khỏe máy nào trước đó để tái dùng), nhưng cấu trúc/pattern tái dùng triệt để: `SensorSource`/`FixedSequenceSensorSource` giống hệt `OcrEngine`/`FixtureOcrEngine` (P3) và `_OracleVisionEngine` (P1); `MachineHealthMonitor.ingest()` nhận `SensorMeasurement` đã dựng sẵn, không tự xây, giống `ProductionSession.record_event()` (P4); `HealthEvent`/factory function giống hệt `MachineEvent`/factory (P4).
- *Implementation (`edge/src/msfc/analytics/`, 12 module mới):* `health_models.py` (P5.1), `sensors.py` (P5.2), `quality.py` (P5.3), `features.py` (P5.4), `baseline.py` (P5.5), `anomaly.py` (P5.6/P5.8), `health_score.py` (P5.7), `health_events.py` (P5.9), `health_monitor.py` (P5.10), `predictive.py` (P5.11/P5.12), `health_repository.py` (P5.19), `evaluation.py` (P5.21), `health_simulate.py` (P5.13), `health_p4_bridge.py` (P5.16/P5.17).
- *P5.7/D-052 — Health score:* 0.0 (tệ nhất) → 1.0 (tốt nhất), công thức phạt theo severity là xác định nhưng **tùy ý**, chưa hiệu chỉnh bằng dữ liệu thật — ghi rõ trong docstring, không claim gì hơn.
- *P5.11/P5.12 — Predictive model:* **KHÔNG train bất kỳ mô hình nào.** `RuleBasedReferenceModel` chỉ là implementation tham chiếu xác định, dùng lại đúng logic anomaly detection đã có — `validated_on_real_data` luôn `False`. `PredictiveHealthModel` Protocol cho phép thay bằng mô hình thật sau này mà không sửa `health_monitor.py`.
- *P5.16/P5.17/D-054 — Tích hợp P4, không tự động hóa:* phân biệt tường minh 4 khái niệm (HEALTH ANOMALY ≠ MACHINE FAULT ≠ DOWNTIME ≠ EMERGENCY STOP). Chỉ MỘT cầu nối tùy chọn (`bridge_critical_health_to_machine_event`), chỉ chuyển MACHINE_HEALTH_CRITICAL, KHÔNG tự động với WARNING/ANOMALY. Không có code path nào từ `msfc.analytics` vào `msfc.sim`/`msfc.decision`/firmware — **bảo đảm kiến trúc**, kiểm chứng bằng `test_layer_dependencies.py`, không chỉ kỷ luật code.
- *2 lỗi thiết kế thật bắt được trước khi viết test chính thức (D-055, D-056 — cùng kỷ luật D-039/D-044/D-049):*
  1. `detect_baseline_anomaly()` ban đầu dùng **trung bình (mean)** của cửa sổ làm giá trị đại diện — một đỉnh nhọn (spike) giữa 6 giá trị bình thường bị pha loãng dưới mọi ngưỡng hợp lý, khiến 3/3 kịch bản "spike" báo sai HEALTHY. Phát hiện bằng script chạy thử cả 15 kịch bản trước khi viết test (giống P1-P4). Sửa: dùng giá trị **cực trị** (max/min) của cửa sổ.
  2. `AnomalyThresholds` ban đầu dùng chung một bộ ngưỡng cho mọi cảm biến — không hợp lý vì thang đo khác nhau hoàn toàn (°C vs mm/s vs A). Sửa: `dict[str, AnomalyThresholds]` theo từng `sensor_id`, giống `baselines` đã có.
- *Test:* 14 file unit mới + 2 file integration mới, **143 test case mới** (`test_analytics_health_models.py` 10, `test_analytics_sensors.py` 4, `test_analytics_quality.py` 16, `test_analytics_features.py` 10, `test_analytics_baseline.py` 10, `test_analytics_anomaly.py` 16, `test_analytics_health_score.py` 6, `test_analytics_health_events.py` 9, `test_analytics_health_monitor.py` 10, `test_analytics_predictive.py` 9, `test_analytics_health_repository.py` 5, `test_analytics_evaluation.py` 12, `test_analytics_health_p4_bridge.py` 5, `test_analytics_health_fixtures.py` 19 = 141 unit; `tests/integration/test_analytics_health_p4_integration.py` 2).
- *Kết quả chạy:* `cd edge && python -m pytest` → **712 passed, 1 skipped** (tăng đúng 143 từ 569+1; **0 test cũ hỏng**). Firmware C không đụng tới — vẫn 262/262.
- *Blocker:* không, cho phạm vi software-only. Chưa validate machine health/predictive maintenance trên máy/cảm biến thật — xem [PHASE5_COMPLETION_REPORT.md](PHASE5_COMPLETION_REPORT.md).

## Phase 6 — Edge AI Platform / Final Software Integration (2026-09-19)

| # | Việc | Trạng thái |
|---|---|---|
| P6.1 | Platform domain model (`CellIdentity`, `RuntimeState`, `PipelineOutcome`, `ProductCycleTrace`, `SubsystemHealth`, `CellSnapshot`) | DONE |
| P6.2 | Pipeline orchestration (vision composition, per-product orchestration) | DONE |
| P6.3 | Runtime / Cell Runtime (`CellRuntime` — lifecycle, subscriptions, snapshot) | DONE |
| P6.4 | Safety authority preserved (courtesy safety gate only; Cell Controller vẫn 100% authoritative) | DONE |
| P6.5 | End-to-end decision flow + precedence (tái dùng luật đã có, không luật mới) | DONE |
| P6.6 | Event/contract unification (decode-side codec, tái dùng `MachineEvent`/`HealthEvent` có sẵn) | DONE |
| P6.7 | MQTT integration boundary (dùng `InMemoryBus`/`MqttBus` có sẵn, không transport mới) | DONE |
| P6.8 | Traceable data flow (`product_id` tái dùng làm correlation id) | DONE |
| P6.9 | Runtime modes (`RuntimeState`, tách bạch `MachineState`) | DONE |
| P6.10 | Subsystem failure handling (vision/OCR/sensor/malformed event/timeout) | DONE |
| P6.11 | Degraded mode (OEE/health không cấu hình ≠ lỗi; health CRITICAL không chặn sản xuất) | DONE |
| P6.12 | Host/simulation timing model (`StageTimer`/`TimingStats`) | DONE |
| P6.13 | Error/resource boundaries (`DedupeFilter` tái dùng, envelope không hợp lệ bị drop) | DONE |
| P6.14 | 20 kịch bản end-to-end xác định | DONE (20/20 PASS) |
| P6.15 | 20+ fixture tái sử dụng | DONE (26 fixtures) |
| P6.16 | Full integration test (success path + failure path) | DONE |
| P6.17 | Regression protection | DONE (808 passed, 1 skipped; 0 test cũ hỏng) |
| P6.18 | Layer/dependency test | DONE (PASS, không cần sửa `test_layer_dependencies.py` — `services` đã khai báo sẵn) |
| P6.19 | Future hardware replacement demonstrated (FrameSource/Transport/Controller/SensorSource qua interface có sẵn) | DONE (kiến trúc, chưa có phần cứng thật) |
| P6.20 | Model/inference/decision boundaries | DONE (không thay đổi, đã tách sẵn từ P1) |
| P6.21 | Edge deployment readiness | DONE (tài liệu, xem PHASE6_COMPLETION_REPORT.md) |
| P6.22 | Observability (logging có sẵn tái dùng, `TimingStats`, `SubsystemHealth`) | DONE |
| P6.23 | Storage boundary | DONE (không có DB sản xuất; OEE/health vẫn in-memory, giữ nguyên từ P4/P5) |
| P6.24 | Final software contract review | DONE (D-051/Q-19, D-048/Q-18 giữ nguyên CHƯA GIẢI QUYẾT, ghi rõ) |
| P6.25 | Documentation | DONE |

**Chi tiết Phase 6:**
- *Kiến trúc:* `msfc.services` (L6) đã được khai báo sẵn từ Phase 0 (ARCHITECTURE.md 7.1/7.2, `test_layer_dependencies.py`) — Phase 6 xây đúng vị trí đó, không tạo package mới, không sửa luật layer. `CellRuntime` không import `msfc.sim`; chỉ nói chuyện với Cell Controller qua `MessageBus`+`ContractRegistry`.
- *Module mới (10):* `edge/src/msfc/services/{__init__,platform_model,codec,timing,vision_pipeline,safety_gate,pipeline,health_pipeline,runtime}.py` (9 module + `__init__.py`).
- *Sửa đổi:* `edge/src/msfc/core/errors.py` (thêm `OrchestrationError`, đúng pattern có sẵn).
- *Quyết định chính:* D-057 (vị trí package) .. D-063 (vision pipeline đặt ở services, không sửa msfc.vision) — xem DECISIONS.md.
- *2 lỗi phát hiện và sửa trước khi chốt:* (1) `CellIdentity` gộp nhầm device_id của Cell Controller và của Edge Server thành một trường — sửa thành 2 trường `cell_device_id`/`edge_device_id` (D-058). (2) Test kịch bản 12/13 gọi thẳng `MachineHealthMonitor.ingest()` bỏ qua `CellRuntime.process_sensors()` — runtime không thấy được; sửa THIẾT KẾ TEST dùng đúng cổng vào công khai (`SensorSource`), không sửa code sản phẩm (D-061).
- *Test:* 11 file unit mới + 2 file integration mới, **96 test case mới** (`test_services_platform_model.py` 11, `test_services_codec.py` 11, `test_services_timing.py` 5, `test_services_vision_pipeline.py` 5, `test_services_safety_gate.py` 7, `test_services_health_pipeline.py` 5, `test_services_pipeline.py` 11, `test_services_runtime.py` 8, `test_services_fixtures.py` 11 = 74 unit; `tests/integration/test_services_scenarios.py` 20, `tests/integration/test_services_full_stack_integration.py` 2 = 22 integration).
- *Kết quả chạy:* `cd edge && python -m pytest` → **808 passed, 1 skipped** (tăng đúng 96 từ 712+1; **0 test cũ hỏng**). Firmware C không đụng tới — vẫn 262/262.
- *Blocker:* không, cho phạm vi software-only. OEE/health vẫn chưa publish qua MQTT thật (D-060, chờ Q-17/Q-18/Q-19). Chưa có ESP32/camera/cảm biến thật — xem [PHASE6_COMPLETION_REPORT.md](PHASE6_COMPLETION_REPORT.md).

## Official Dashboard — S1 Web Dashboard (2026-09-19)

**Không phải Phase 7** (theo đúng chỉ thị PO: "Do NOT create Phase 7 or invent a new project phase beyond this dashboard phase") — đây là phần bổ sung giao diện người dùng cho nền tảng phần mềm P1–P6 đã DONE, không phải một phase mới trong roadmap gốc.

| # | Việc | Trạng thái |
|---|---|---|
| 1 | Skill discovery (kiểm tra `skills/` trong repo) | DONE — không có `skills/`/`SKILL.md` nào trong repo; không có skill để dùng |
| 2 | Kiến trúc dashboard (Adapter/API trên `CellRuntime`) | DONE |
| 3 | Backend: FastAPI + Uvicorn (`msfc.dashboard`) | DONE |
| 4 | Frontend: HTML/CSS/JS thuần | DONE |
| 5 | Overview, Production, Vision & OCR, Safety, Machine Health, OEE, Event Log, Diagnostics | DONE (8/8) |
| 6 | Demo controls (START/STOP/RESET/SIMULATE ×7) | DONE |
| 7 | RUN FULL DEMO (14 bước) | DONE |
| 8 | Error handling (SYSTEM OFFLINE/UNKNOWN, không giả HEALTHY) | DONE |
| 9 | Test dashboard/backend (20 mục yêu cầu) | DONE (22 test, vượt yêu cầu) |
| 10 | Full Python regression | DONE (859 passed, 1 skipped) |
| 11 | Firmware regression | DONE (262/262, không đổi) |
| 12 | Xác minh trực quan qua trình duyệt thật | DONE (xem PHASE_DASHBOARD_COMPLETION_REPORT.md) |
| 13 | Tài liệu (ARCHITECTURE/USER_GUIDE/COMPLETION_REPORT) | DONE |

**Chi tiết:**
- *Skill discovery:* Đã kiểm tra toàn bộ repo (`find . -iname skills -type d`, `find . -iname SKILL.md`) — **không tìm thấy** thư mục `skills/` hay file `SKILL.md` nào. `.claude/company/` chỉ chứa metadata quản lý nội bộ (`project.json`), không phải skill. Kết luận: không có skill sẵn có để dùng; dashboard được thiết kế bằng kiến thức kỹ thuật trực tiếp (FastAPI/JS/CSS công nghiệp-tối-giản).
- *Kiến trúc:* `msfc.dashboard` (L8, khai báo sẵn từ Phase 0, ADR-0012) — `DemoSession` sở hữu một `SimCellController`+`CellRuntime`+`InMemoryBus` thật; `api.py` (FastAPI) chỉ đọc/điều khiển qua đó, không có logic nghiệp vụ riêng.
- *Mở rộng layer rule (D-065):* `ALLOWED["dashboard"]` thêm `services, analytics, sim, vision, ocr, decision` — lý do: dashboard không thể hiển thị dữ liệu CellRuntime/OEE/health hay dựng phiên demo nếu thiếu các quyền này (đúng mục 5 chỉ thị "Reuse: CellRuntime, SimCellController, InMemoryBus").
- *Mở rộng bồi thêm cho `CellRuntime` (D-066, KHÔNG sửa logic cũ):* `product_history()`, `event_log()`, property `ocr`/`vision` để đổi cấu hình giữa chu kỳ.
- *File mới:* `edge/src/msfc/dashboard/{__init__,dtos,session,api,__main__}.py` + `static/{index.html,styles.css,app.js}` (5 module Python + 3 file tĩnh) + `edge/run_dashboard.py` + `.claude/launch.json` + 4 file test (`test_dashboard_dtos.py`, `test_dashboard_session.py`, `test_dashboard_api.py`, `test_services_runtime_observability.py`) + 3 tài liệu (`OFFICIAL_DASHBOARD_ARCHITECTURE.md`, `OFFICIAL_DASHBOARD_USER_GUIDE.md`, `PHASE_DASHBOARD_COMPLETION_REPORT.md`).
- *Sửa đổi:* `edge/src/msfc/services/{platform_model,runtime,__init__}.py` (mở rộng bồi thêm), `edge/tests/unit/test_layer_dependencies.py` (mở rộng `ALLOWED["dashboard"]`), `edge/pyproject.toml` (thêm fastapi/uvicorn/httpx).
- *2 lỗi thật phát hiện và sửa trước khi chốt (D-067):* (1) `DemoSession._advance()` nhảy thời gian >1000ms trong một bước gây lỗi COMM_LOSS giả — sửa bằng cách chia nhỏ bước nhảy. (2) Giả định sai rằng "RECOVERY" trả sức khỏe về HEALTHY ngay lập tức — sửa bằng cách chủ động nhảy đồng hồ qua khỏi cửa sổ trung bình trước khi đẩy giá trị khỏe mạnh.
- *Xác minh trực quan:* Dashboard được chạy thật (`preview_start`) và thao tác trực tiếp qua trình duyệt (Claude Browser tool) — START, SIMULATE GOOD/DEFECT, E-STOP, RESET, RUN FULL DEMO, chuyển đủ 8 tab — tất cả hoạt động đúng, không lỗi console.
- *Test:* 4 file mới, **51 test case mới** (`test_services_runtime_observability.py` 7, `test_dashboard_dtos.py` 11, `test_dashboard_session.py` 11, `test_dashboard_api.py` 22).
- *Kết quả chạy:* `cd edge && python -m pytest` → **859 passed, 1 skipped** (tăng đúng 51 từ 808+1; **0 test cũ hỏng**). Firmware C không đụng tới — vẫn 262/262.
- *Blocker:* không, cho phạm vi software-only. Chưa deploy dashboard lên môi trường thật, chưa có phần cứng — xem [PHASE_DASHBOARD_COMPLETION_REPORT.md](PHASE_DASHBOARD_COMPLETION_REPORT.md).

## Phase 7

Chưa tạo task chi tiết (theo quy tắc: không tạo quá nhiều module cùng lúc). Mục tiêu và acceptance từng phase: [ROADMAP.md](ROADMAP.md).
