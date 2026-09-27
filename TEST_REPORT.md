# Test Report — MSFC

Quy tắc ([QA_PLAN](docs/QA_PLAN.md) mục 8): mỗi mục ghi **ID · ngày · môi trường · cách chạy · kết quả quan sát được · PASS/FAIL/NOT RUN · giới hạn**.
**"Chưa chạy" phải ghi NOT RUN.** Kết quả trên simulator phải ghi rõ là simulator.

---

## Phase 0 — 2026-09-17

### Môi trường

| Hạng mục | Giá trị |
|---|---|
| OS / CPU / RAM | Windows 11 Pro build 26200 · i5-12450H · 15,7 GB |
| GPU / driver | RTX 3050 Laptop 4096 MiB · 610.78 |
| Python / pytest | 3.11.9 · pytest 9.1.1 |
| Git | 2.55.0 · nhánh `main`, **chưa có commit** (PO quyết định thời điểm commit, ADR-0013) |
| Dependency runtime | **không có** (chỉ thư viện chuẩn) |
| Cấu hình dùng khi test | `config/default.toml` + file tạm trong `tmp_path` |

### Kết quả chạy test

**Lệnh:** `cd edge && python -m pytest`
**Kết quả quan sát được:** `43 passed in 0.25s`

| Mức | File | Số case | Kết quả | Yêu cầu được kiểm chứng |
|---|---|:-:|---|---|
| UT | `edge/tests/unit/test_config.py` | 20 | **PASS** | FR-OPS-02 (phân lớp cấu hình, khóa lạ bị từ chối, dải giá trị, biến môi trường, bất biến) |
| UT | `edge/tests/unit/test_logging_setup.py` | 8 | **PASS** | FR-OPS-01 (JSONL + ngữ cảnh, exception, mức log theo logger, idempotent, tạo thư mục) |
| UT | `edge/tests/unit/test_layer_dependencies.py` | 2 | **PASS** | NFR-MNT-01 (quy tắc phụ thuộc layer; package mới bắt buộc phải khai báo) |
| MT-01 | `edge/tests/contract/test_contract_files.py` | 13 | **PASS** | FR-COM-02/03/04 (ngữ pháp topic, QoS/retain, schema tồn tại và hợp lệ, không có schema mồ côi, tài liệu chứa mọi topic key, kênh an toàn được đánh dấu) |
| — | **Tổng** | **43** | **43 PASS / 0 FAIL** | |

### Kiểm tra môi trường

**Lệnh:** `python tools/check_env.py` → exit code 1

| Công cụ | Cần từ phase | Kết quả |
|---|---|---|
| python 3.11 | 0 | **OK** (3.11.9) |
| pytest | 0 | **OK** (9.1.1) |
| git | 0 | **OK** (2.55.0) |
| nvidia-smi | 1 (tùy chọn) | OK (610.78) |
| **mosquitto** | 1 | **MISSING** |
| **idf.py (ESP-IDF)** | 1 | **MISSING** |
| **gcc (MSYS2)** | 1 | **MISSING** |
| cmake | 1 (tùy chọn) | optional, chưa có |

→ Đủ điều kiện cho Phase 0. **Ba công cụ MISSING là blocker B4 của Phase 1.**

### Chưa chạy (NOT RUN) — và vì sao

| Nhóm test | Trạng thái | Lý do |
|---|---|---|
| FWT-* (unit test firmware trên host) | **NOT RUN** | Chưa có code firmware (Phase 0 chỉ có kiến trúc module); chưa có gcc |
| IT-* (integration) | **NOT RUN** | Chưa có `msfc.comm`/`msfc.sim` (Phase 1) |
| MT-02..05 (MQTT runtime) | **NOT RUN** | Chưa cài broker, chưa có MQTT client |
| HIL-*, ST-01..17, FT-01..12 | **NOT RUN** | **Chưa có phần cứng nào được lắp hay kiểm chứng** |
| VT-*, PT-*, LT-* | **NOT RUN** | Cần camera + băng tải + mô hình (Phase 1) |

### Giới hạn của Phase 0

1. **Không có kết quả nào trên phần cứng thật.** Toàn bộ kết quả trên là test phần mềm trên laptop.
2. Test contract kiểm tra **tính nhất quán của tài liệu và schema**, **không** kiểm chứng rằng firmware/Edge Server tuân thủ contract (việc đó ở Phase 1: MT-02..05).
3. Chưa có mô hình AI, chưa có dataset → mọi phát biểu về độ chính xác đều chưa tồn tại.
4. `test_layer_dependencies.py` hiện chỉ thấy package `core`; giá trị thật của nó thể hiện khi các package Phase 1 xuất hiện.
5. Chưa có commit git nào, nên chưa có mã commit để truy vết phiên bản; cần PO quyết định (Q-01).
6. Review nội bộ do **cùng một assistant** thực hiện (CEO + CTO passes), **không phải review độc lập của người thứ hai**.

---

## Phase 1 — Software-first (P1.1–P1.7), 2026-09-18

> **Toàn bộ mục này chạy trên dữ liệu tổng hợp/giả lập (`SyntheticFrameSource`, `InMemoryBus`, `SimCellController`), KHÔNG phải phần cứng thật.** Đây là bằng chứng cho **AC-SW-01..07** (cổng software trước khi mua hàng — [PHASE1_PLAN.md](docs/PHASE1_PLAN.md) mục 3), không phải cho **AC-P1-01..11** (cần phần cứng thật, vẫn NOT RUN — xem cuối mục này).

### Cập nhật 2026-09-18 (lượt 2) — P1.3 CNN/ONNX training scaffold

**Trình tự chạy test (theo yêu cầu PO):**

| # | Bước | Lệnh | Kết quả |
|---|---|---|---|
| 1 | Unit test liên quan | `cd edge && python -m pytest tests/unit/test_vision_training_smoke.py -v` | **12 passed in 24.77s** |
| 2 | AI smoke test (training) | (nằm trong bước 1: `test_train_smoke_test_runs_end_to_end_and_saves_a_checkpoint`, `test_train_smoke_test_is_reproducible_with_the_same_seed`) | **PASS** |
| 3 | ONNX inference smoke test | `cd edge && python -m pytest tests/unit/test_vision_onnx_inference_smoke.py -v` | **5 passed in 23.17s** |
| 4 | Integration pipeline (đã có, không sửa) | `cd edge && python -m pytest tests/integration/ -v` | không bị ảnh hưởng — nằm trong tổng số bước 5 |
| 5 | Toàn bộ pytest | `cd edge && python -m pytest` | **367 passed, 1 skipped in 31.49s** (tăng đúng 17 test mới so với 350+1 trước đó; **0 test cũ bị hỏng**) |

**Artifact:** `ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/checkpoint.pt` (32 025 byte) và `.../model.onnx` (30 417 byte) — SHA-256 trong `checksum.txt`, không commit git (đúng `ai/models/README.md`). **Dataset:** 3 phiên tổng hợp (`s01`,`s02`,`s03`) × 12 ảnh = 36 ảnh, `data_source: synthetic`, chia bằng `split_by_session()` (train=s01, val=s02, test=s03).

**Kết quả huấn luyện (test split, 12 ảnh, epoch tốt nhất theo F1 trên val):**

| accuracy | precision(DEFECT) | recall(DEFECT) | F1(DEFECT) | confusion |
|---|---|---|---|---|
| 0.5 | 0.0 | 0.0 | 0.0 | tp=0, fp=0, tn=6, fn=6 |

**Ghi nhận trung thực:** `TinyCapCNN` dự đoán **mọi ảnh là GOOD** sau 2 epoch trên 12 ảnh train — không phân biệt được GOOD/DEFECT trên dataset tổng hợp mặc định, cùng hiện tượng đã ghi ở R-28 cho `ClassicCvBaseline`. Đã xác nhận đây **không phải lỗi wiring**: `test_onnx_output_matches_pytorch_model_on_the_same_input` xác nhận ONNX Runtime khớp PyTorch (sai lệch <1e-4), và `test_onnx_engine_plugs_into_existing_postprocess_and_decision_engine` xác nhận `OnnxInferenceEngine` chạy đúng qua `postprocess()` và `DecisionEngine.decide()` **không sửa gì ở hai module đó**. Không tinh chỉnh ngưỡng hay train thêm để "qua" test, đúng chỉ thị PO. Chi tiết: [model_card.md](ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/model_card.md), quyết định D-035.

**P1.5 (firmware C thật):** xác nhận lại vẫn **BLOCKED** — chỉ kiểm tra tài liệu (`firmware/cell_controller/README.md`, `docs/HARDWARE_INTERFACE.md`), không cài ESP-IDF/gcc, không viết code C nào. `firmware/cell_controller/` vẫn chỉ có `README.md`.

### Môi trường

| Hạng mục | Giá trị |
|---|---|
| Dependency mới cài | `jsonschema` 4.26.0, `onnxruntime` 1.30.0 (+ `flatbuffers` 25.12.19, `protobuf` 7.36.1) |
| Dependency có sẵn | `numpy` 2.4.6, `opencv-python` 5.0.0.93, `paho-mqtt` 2.1.0, `torch` 2.13.0, `torchvision` 0.28.0 |
| GPU | `torch.cuda.is_available()` = **False** dù có RTX 3050 driver 610.78 — xem R-27 |
| Broker MQTT | Chưa cài Mosquitto (B4) |

### Kết quả chạy toàn bộ

**Lệnh:** `cd edge && python -m pytest` → **367 passed, 1 skipped**, exit code 0 (cập nhật 2026-09-18 lượt 2; trước đó 350 passed, 1 skipped).

| Gói | File test | Số case | Kết quả |
|---|---|---:|---|
| `msfc.domain` (P1.1) | `test_domain_enums_faults.py`, `test_domain_events.py`, `test_domain_inspection_commands.py`, `test_domain_state.py` | 80 | **PASS** |
| `msfc.contracts` (P1.7) | `test_contracts_registry.py`, `test_contracts_envelope.py`, `test_contracts_validation.py` | 45 | **PASS** |
| `msfc.comm` (P1.7) | `test_comm_topic_match.py`, `test_comm_bus.py`, `test_comm_dedupe.py`, `test_comm_backoff.py`, `test_comm_mqtt_bus.py` | 53 | **PASS** (MqttBus test bằng `FakeMqttClient`, không cần broker) |
| `msfc.vision` (P1.2+P1.3 cổ điển) | `test_vision_synthetic.py`, `test_vision_sources.py`, `test_vision_preprocess.py`, `test_vision_baseline_postprocess.py`, `test_vision_evaluation.py` | 65 | **PASS** (`ImageFolderFrameSource`/`VideoFileFrameSource` test bằng PNG/MP4 **thật**, tự ghi ra lúc test) |
| `msfc.vision` (P1.3 CNN/ONNX, mới) | `test_vision_training_smoke.py`, `test_vision_onnx_inference_smoke.py` | 17 | **PASS** (xem mục "Cập nhật 2026-09-18 (lượt 2)" ở trên) |
| `msfc.decision` (P1.4) | `test_decision_engine.py` | 20 | **PASS** |
| `msfc.sim` (P1.6) | `test_sim_cell_controller.py` | 38 | **PASS** (gồm cả đường đi qua `InMemoryBus` bằng envelope MQTT thật) |
| Pipeline MVP end-to-end | `tests/integration/test_full_pipeline_mvp.py` | 6 | **PASS** |
| Broker MQTT thật | `tests/integration/test_mqtt_bus_real_broker.py` | 1 | **SKIP** (đúng, Mosquitto chưa cài — B4) |

### Phát hiện quan trọng khi test (đã sửa hoặc ghi nhận)

| # | Phát hiện | Nơi | Xử lý |
|---|---|---|---|
| 1 | `format_topic`/`match_topic` ban đầu có tham số `name` cho placeholder tổng quát mà **không topic thật nào dùng tới** | `msfc.contracts.registry` | Bỏ tham số khỏi API (giảm code chết) |
| 2 | Thiết kế nháp của `SimCellController` định dùng `mono_ms` của gói tin MQTT **đến** làm giờ của chính nó — sai vì đó là đồng hồ của bên gửi | `msfc.sim.engine` | Sửa **trước khi viết test**: dùng một đồng hồ riêng (`self._now_mono_ms`), chỉ tiến qua `tick()`/tham số tường minh |
| 3 | 2 test tự viết sai giả định (đồng hồ lùi khi feed sự kiện không đúng thứ tự thời gian; quên gửi heartbeat mồi trước khi tick) | `test_sim_cell_controller.py` | Sửa lại test cho đúng trình tự thời gian thực; không phải lỗi của `sim` |
| 4 | `ClassicCvBaseline` (khoảng cách tới template trung bình) **gần như không phân biệt được GOOD/DEFECT** trên dữ liệu tổng hợp mặc định khi nối pipeline end-to-end (điểm GOOD ≈ 21,9 vs DEFECT ≈ 21,9–23,2) | Tích hợp pipeline MVP | **Giới hạn thật, không phải lỗi wiring** — ghi [RISK_REGISTER.md](docs/RISK_REGISTER.md) R-28; test wiring tách bạch bằng engine giả biết trước nhãn; test riêng vẫn chạy baseline thật để xác nhận đúng interface |
| 5 | `TinyCapCNN` (P1.3 CNN scaffold) **cũng dự đoán mọi ảnh là GOOD** sau 2 epoch trên dataset tổng hợp mặc định (accuracy=0.5, F1(DEFECT)=0.0) | `test_vision_training_smoke.py` | **Giới hạn thật (dataset tổng hợp quá nhỏ/khó + train cố tình ngắn), không phải lỗi wiring** — xác nhận bằng cross-check ONNX Runtime khớp PyTorch (<1e-4) và pipeline `postprocess→DecisionEngine` chạy đúng; ghi D-035, [model_card.md](ai/models/tiny_cap_cnn_smoke/v0.1-synthetic/model_card.md) |

### Chưa chạy (NOT RUN) và vì sao

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| AC-P1-01..11 (cần phần cứng thật) | **NOT RUN** | Hardware = NONE, chưa qua P1.9 (procurement) |
| MT-02..05 (MQTT trên broker thật) | **NOT RUN** (có test tự động, tự SKIP) | Chưa cài Mosquitto (B4) |
| P1.5 (firmware C, test host) | **DONE lượt 3** (131/131 PASS) | `gcc` thật ra đã có (D-036); xem mục "Cập nhật 2026-09-18 (lượt 3)" bên dưới |
| P1.5 (firmware C, build cho chip ESP32 qua `idf.py`) | **NOT RUN** | Vẫn thiếu ESP-IDF SDK (B4) |
| ST-*, FT-* (test an toàn/lỗi trên phần cứng) | **NOT RUN** | Cần phần cứng thật |
| Đánh giá độ chính xác AI trên dữ liệu thật | **NOT RUN** | Chưa có dataset thật (cần camera + sản phẩm mẫu); CNN/ONNX smoke test trên dữ liệu tổng hợp đã **DONE** (xem mục lượt 2 ở trên) |

### Giới hạn của vòng test này

1. Mọi kết quả PASS ở trên là **phần mềm chạy trên laptop với dữ liệu tổng hợp/giả lập** — không chứng minh gì về phần cứng thật hay độ chính xác AI thật.
2. Test wiring (routing GOOD/DEFECT, tracking, fault handling) dùng engine AI **giả định biết trước nhãn** để tách bạch khỏi vấn đề độ chính xác mô hình thật — đây là lựa chọn thiết kế test có chủ đích, không phải che giấu.
3. Review vẫn do một assistant thực hiện, không có người thứ hai độc lập.

### Cập nhật 2026-09-18 (lượt 3) — Close Phase 1 Software Gate: firmware `core_logic` host tests

**Môi trường (kiểm tra lại theo chỉ thị PO):**

| Công cụ | Trạng thái theo `check_env.py` | Trạng thái thật | Ghi chú |
|---|---|---|---|
| `idf.py` (ESP-IDF) | MISSING | **MISSING (xác nhận)** | Không có `IDF_PATH`, không có thư mục Espressif nào |
| `gcc` | MISSING | **thật ra ĐÃ CÓ** | MSYS2 UCRT64 `C:\msys64\ucrt64\bin\gcc.exe` 16.1.0, không nằm trong PATH mặc định (D-036) |
| `cmake`/`ninja`/`make` | — | không có trong MSYS2 UCRT64 | Không cần — build gọi `gcc` trực tiếp, không qua build system |
| `mosquitto` | MISSING | **MISSING (xác nhận)** | Không tìm thấy ở Program Files, PATH, hay MSYS2 |

**Lệnh:** `bash firmware/cell_controller/test_host/build_and_run.sh` (PATH được thêm `C:\msys64\ucrt64\bin` chỉ trong phạm vi script, không đổi PATH hệ thống)
**Kết quả quan sát được:** `TOTAL: 131 checks run, 0 failed` — build với `-std=c99 -Wall -Wextra -Werror`, **0 warning**.

| File | Số check | Kết quả |
|---|---:|---|
| `test_cell_sm.c` | 25 | **PASS** |
| `test_fault_manager.c` | 15 | **PASS** |
| `test_debounce.c` | 9 | **PASS** |
| `test_safety_supervisor.c` | 42 | **PASS** |
| `test_cmd_handler.c` | 15 | **PASS** |
| `test_watchdog.c` | 15 | **PASS** |
| `test_hal_boundary_integration.c` | 10 | **PASS** |
| **Tổng** | **131** | **131 PASS / 0 FAIL** |

**Không phải bằng chứng cho:** build/nạp firmware thật lên chip ESP32 (`idf.py build` vẫn NOT RUN — thiếu SDK); `product_tracker`/`heartbeat_monitor`/`timing_stats` (chưa viết, ngoài phạm vi ưu tiên PO lượt này). Xem D-037, TASKS.md mục "Chi tiết P1.5".

**Python (không đổi gì lượt này):** `cd edge && python -m pytest` → **367 passed, 1 skipped in 10.91s**, y hệt lượt trước — xác nhận không có gì bị hỏng.

### PO approval (2026-09-18) — Close P1 Software Scope

PO đã review kết quả trên và **approve đóng Phase 1 software scope**: SOFTWARE LOGIC + HOST VALIDATION = COMPLETE; ESP32 TARGET BUILD, REAL HARDWARE VALIDATION, REAL AI VALIDATION = PENDING (không phải thất bại — xem [PROJECT_STATUS.md](PROJECT_STATUS.md) mục 0 cho bảng 5 mức đầy đủ, và [PHASE1_COMPLETION_REPORT.md](PHASE1_COMPLETION_REPORT.md) cho báo cáo tổng kết). Không có test nào chạy lại trong lượt duyệt này — không có code nào bị sửa.

---

## Phase 2 — Software-only Safety & Interlock, 2026-09-18

> **SOFTWARE-ONLY.** Toàn bộ mục này chạy trên host qua `hal_host_mock`, không phần cứng. **SOFTWARE E-STOP SIMULATION != PHYSICAL E-STOP VALIDATION** — không có kết quả nào dưới đây được diễn giải là xác nhận an toàn vật lý.

### Kết quả chạy targeted (trong lúc implement)

| File test mới | Số check | Kết quả | Phạm vi |
|---|---:|---|---|
| `test_safety_interlock_core.c` | 34 | **PASS** | P2.1 (state view), P2.2 (software E-STOP), P2.7 (invalid/malformed command) |
| `test_safety_interlock_comm_loss.c` | 43 | **PASS** | P2.5 (comm loss: normal/timeout/disconnect/recovery), P2.6 (watchdog) |
| `test_safety_interlock_recovery.c` | 27 | **PASS** | P2.8 (deterministic recovery matrix theo từng loại lỗi; "no automatic recovery") |
| `test_safety_scenarios.c` | 27 | **PASS** | P2.9 — đúng 12 kịch bản PO liệt kê |

### Kết quả gate (sau khi implement xong)

**Lệnh:** `bash firmware/cell_controller/test_host/build_and_run.sh`
**Kết quả:** `TOTAL: 262 checks run, 0 failed` — 131 check P1 (không đổi) + 131 check Phase 2 mới, build `-std=c99 -Wall -Wextra -Werror`, **0 warning**.

**Lệnh:** `cd edge && python -m pytest` (regression toàn bộ, chạy đúng 1 lần tại gate theo yêu cầu PO)
**Kết quả:** `367 passed, 1 skipped in 12.80s` — **giống hệt trước Phase 2**, xác nhận không có regression (không file Python nào bị sửa).

### Thiết kế test quan trọng cần biết

1. **Không sửa file P1 nào để làm Phase 2** — `cell_sm.c`, `fault_manager.c`, `watchdog.c`, `cmd_handler.c`, `hal_interface.h`, `hal_host_mock.c` giữ nguyên 100%; toàn bộ Phase 2 nằm trong 2 file mới `safety_interlock.h/.c` + 4 file test mới.
2. **Phát hiện quan trọng khi viết test (đã sửa trước khi test, không phải debug sau):** thiết kế ban đầu định dùng `watchdog_check()` (P1) trực tiếp cho comm-loss — nhưng hàm này **chốt vĩnh viễn** sau lần timeout đầu (đúng cho watchdog reset-thiết-bị một lần, sai cho comm-loss cần tự phục hồi). Phát hiện ngay khi thiết kế kịch bản "communication recovery"/"repeated timeout" (P2.5/P2.6), sửa bằng cách tự viết một kiểm tra "còn tươi" cục bộ dùng lại dữ liệu của `watchdog_t` (không sửa `watchdog.c`) — xem D-039.
3. **`safety_interlock_confirm_recovery()` re-check toàn bộ điều kiện tại thời điểm gọi**, không chỉ tại thời điểm RESET — test `test_confirm_recovery_blocked_by_new_condition` xác nhận một lỗi mới xuất hiện giữa RESET và confirm sẽ chặn confirm (đúng P2.8 "avoid automatic recovery").
4. Test dùng harness tối thiểu tự viết (`test_util.h`, kế thừa từ P1, không sửa) — không phải Unity thật, cùng lý do đã ghi ở P1.5.

### Chưa chạy / ngoài phạm vi (NOT RUN)

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| ESP32 target build (`idf.py build`) cho `safety_interlock` | **NOT RUN** | Thiếu ESP-IDF SDK (không đổi từ P1.5) |
| PHYSICAL E-STOP VALIDATION | **NOT RUN** | Kênh E-stop vật lý (NC contact) chưa tồn tại, chưa mua |
| Interlock trên phần cứng thật (motor fault/sensor fault từ tín hiệu HAL thật) | **NOT RUN** | HARDWARE = NONE |
| Hợp nhất `interlock_reject_t` vào MQTT contract (`cmd_ack.v1`) | **NOT RUN — có chủ đích** | Ngoài phạm vi "software-only safety/interlock" lượt này (D-040, Q-16) |

---

## Phase 3 — Software-only OCR / Expiry / Label Verification, 2026-09-18

> **SOFTWARE-ONLY.** Toàn bộ ảnh là tổng hợp (render bằng `cv2.putText`, 0đ), không camera thật, không dịch vụ OCR thật (`MockOcrEngine`/`FixtureOcrEngine`). **Không claim độ chính xác OCR trên ảnh/sản phẩm thật** (rule 14, PO chỉ thị).

### Kết quả chạy targeted (trong lúc implement)

| File test mới | Số case | Kết quả | Phạm vi |
|---|---:|---|---|
| `test_ocr_models.py` | 8 | **PASS** | P3.1 (domain model) |
| `test_ocr_engine.py` | 6 | **PASS** | P3.2 (Mock OCR, Fixture OCR) |
| `test_ocr_preprocess.py` | 17 | **PASS** | P3.3 (grayscale/resize/contrast/denoise/threshold/crop/deskew) |
| `test_ocr_text.py` | 17 | **PASS** | P3.4 (normalize) + P3.5 (date extraction, cả 5 định dạng) |
| `test_ocr_validate.py` | 17 | **PASS** | P3.6 (date validation) + P3.7 (label/product validation) |
| `test_ocr_classify.py` | 11 | **PASS** | P3.8 (classification) + P3.9 (InspectionResult wrapping) |
| `test_ocr_pipeline.py` | 7 | **PASS** | P3.9 (flow) + P3.12 (error handling) |
| `test_ocr_fixtures.py` | 15 | **PASS** | P3.10/P3.11 (12 kịch bản + simulation, tham số hóa) |
| `tests/integration/test_ocr_decision_integration.py` | 5 | **PASS** | P3.9 (tích hợp `DecisionEngine` thật, không sửa) |

### Kết quả gate (sau khi implement xong)

**Lệnh:** `cd edge && python -m pytest`
**Kết quả:** `470 passed, 1 skipped in 14.92s` — tăng đúng 103 từ 367+1 trước đó, **0 test cũ hỏng**.

`test_layer_dependencies.py` (2 test, Phase 0, không sửa) tiếp tục PASS — xác nhận `msfc.ocr` tự động đúng luật layer đã khai báo sẵn từ Phase 0 (`"ocr": {"core", "domain"}`).

### 12 kịch bản fixture (P3.10/P3.11) — kết quả từng cái

| # | Kịch bản | Verdict mong đợi | Kết quả |
|---|---|---|---|
| 1 | valid_expiry_date | GOOD | PASS |
| 2 | expired_product | DEFECT | PASS |
| 3 | impossible_date | DEFECT | PASS |
| 4 | missing_expiry | DEFECT | PASS |
| 5 | wrong_product_identifier | DEFECT | PASS |
| 6 | valid_product_and_expiry | GOOD | PASS |
| 7 | low_ocr_confidence | UNCERTAIN | PASS |
| 8 | ambiguous_ocr | UNCERTAIN | PASS |
| 9 | multiple_date_formats | GOOD | PASS |
| 10 | ocr_noise | GOOD | PASS |
| 11 | empty_ocr_result | UNCERTAIN | PASS |
| 12 | malformed_ocr_result | DEFECT | PASS |

### Lỗi tự phát hiện và sửa qua test (đã sửa trước khi viết test chính thức, không phải debug sau)

| # | Phát hiện | Nơi | Xử lý |
|---|---|---|---|
| 1 | `FixtureOcrEngine` tra ground-truth theo `id(image)` — vỡ vì `preprocess()` luôn trả mảng numpy MỚI, khiến ảnh đăng ký không bao giờ khớp lại | `msfc.ocr.engine` | Phát hiện bằng script smoke-check thủ công chạy cả 12 fixture trước khi viết test (11/12 sai kết quả). Sửa bằng `set_next_output()` tường minh, đúng pattern `_OracleVisionEngine` đã có sẵn ở P1 — D-044 |
| 2 | Fixture `malformed_ocr_result` đặt confidence=0.5 (dưới ngưỡng 0.6), khiến kết quả rơi vào UNCERTAIN thay vì DEFECT như dự định — lỗi ở dữ liệu fixture, không phải logic | `msfc.ocr.synthetic` | Tăng confidence lên 0.70 để cô lập đúng điều đang muốn test ("văn bản vô nghĩa" tách khỏi "confidence thấp", đã có fixture riêng) |

### Chưa chạy / ngoài phạm vi (NOT RUN)

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| REAL OCR VALIDATION (ảnh camera/sản phẩm thật) | **NOT RUN** | HARDWARE = NONE, chưa có ảnh thật, không cài dịch vụ OCR thật (rule 4) |
| ESP32 target build | **NOT RUN** | Không đổi từ Phase 1/2 — thiếu ESP-IDF SDK |
| Publish `ocr.event.label_result` qua MQTT thật (`label_result.v1` vẫn là draft) | **NOT RUN — có chủ đích** | Ngoài phạm vi lượt này; `msfc.services` (nơi sẽ gọi MQTT) chưa xây — D-040/Q-17 |
| LABEL_MISALIGNED trong 12 kịch bản fixture | **Không nằm trong danh sách 12 kịch bản PO liệt kê** | Test riêng bằng unit test tường minh (`test_ocr_validate.py`), không phải fixture ảnh |

---

## Phase 4 — Software-only OEE / Machine Monitoring, 2026-09-18

> **SOFTWARE-ONLY.** Toàn bộ sự kiện là mô phỏng/tổng hợp (`msfc.analytics.simulate`), không cảm biến/ESP32/PLC/camera/MQTT broker thật. **Không claim OEE thật của một dây chuyền vật lý.**

### Kết quả chạy targeted (trong lúc implement)

| File test mới | Số case | Kết quả | Phạm vi |
|---|---:|---|---|
| `test_analytics_models.py` | 10 | **PASS** | P4.1 (domain model), P4.4 (downtime), P4.10 (cycle stats) |
| `test_analytics_events.py` | 14 | **PASS** | P4.3 (machine event) + factory từ đúng domain event P1 |
| `test_analytics_calculations.py` | 25 | **PASS** | P4.5–P4.8 (Availability/Performance/Quality/OEE) + edge case toán học |
| `test_analytics_session.py` | 22 | **PASS** | P4.9 (production session) + P4.15 (thứ tự sự kiện, trùng lặp, downtime chồng lấn, reset) |
| `test_analytics_monitor.py` | 5 | **PASS** | P4.11 (machine monitoring layer) |
| `test_analytics_repository.py` | 5 | **PASS** | P4.17 (storage abstraction, in-memory) |
| `test_analytics_fixtures.py` | 17 | **PASS** | P4.13 (10 kịch bản) + P4.14 (15 fixture, tham số hóa nơi có thể) |
| `tests/integration/test_analytics_domain_integration.py` | 1 | **PASS** | P4.16 — chạy qua đúng `StateChangedEvent`/`ProductDetectedEvent`/`ProductSortedEvent`/`FaultReport` thật của P1, không phải test double tự chế |

### Kết quả gate (sau khi implement xong)

**Lệnh:** `cd edge && python -m pytest`
**Kết quả:** `569 passed, 1 skipped in 11.15s` — tăng đúng 99 từ 470+1 trước đó, **0 test cũ hỏng**.

`test_layer_dependencies.py` (2 test, P0, không sửa) tiếp tục PASS — xác nhận `msfc.analytics` tự động đúng luật layer đã khai báo sẵn từ Phase 0 (`"analytics": {"core", "domain"}`), và **không thể** import `msfc.sim`/`msfc.decision`/firmware — bảo đảm kiến trúc cho P4.12 (OEE không ghi đè an toàn).

**Firmware:** không sửa file C nào lượt này — `bash firmware/cell_controller/test_host/build_and_run.sh` vẫn **262/262 PASS** (không chạy lại, không có gì thay đổi để kiểm).

### 10 kịch bản simulation (P4.13) — kết quả hand-checked

| # | Kịch bản | Availability | Performance | Quality | OEE |
|---|---|---:|---:|---:|---:|
| 1 | normal_production | 1.000 | 1.000 | 1.000 | 1.000 |
| 2 | normal_cycles | 1.000 | 1.000 | 1.000 | 1.000 |
| 3 | planned_downtime | 1.000 | 1.000 | 1.000 | 1.000 |
| 4 | unplanned_downtime | 0.286 | 1.000 | 1.000 | 0.286 |
| 5 | machine_fault | 0.333 | 0.000 | 0.000 | 0.000 |
| 6 | emergency_stop | 0.000 | 0.000 | 0.000 | 0.000 |
| 7 | defect_production | 1.000 | 1.000 | 0.000 | 0.000 |
| 8 | mixed_good_defect_production | 1.000 | 1.000 | 0.625 | 0.625 |
| 9 | slow_cycles | 1.000 | 0.500 | 1.000 | 0.500 |
| 10 | multiple_production_sessions | (2 phiên độc lập — session 1 OEE=1.0, session 2 OEE=0.0) | | | |

Kịch bản 3 vs 4 (cùng hình dạng — 2 chu kỳ, khoảng nghỉ 10s, 2 chu kỳ — chỉ khác category downtime) minh chứng trực tiếp quyết định D-049: PLANNED không phạt Availability, UNPLANNED thì có.

### Lỗi tự phát hiện và sửa qua test (đã sửa trước khi viết test chính thức)

| # | Phát hiện | Nơi | Xử lý |
|---|---|---|---|
| 1 | Trạng thái khởi tạo mặc định BOOT mở một khoảng downtime không bao giờ đóng (kịch bản không phát sự kiện chuyển trạng thái) → `run_time_ms must be > 0` cho mọi kịch bản có chu kỳ | `msfc.analytics.simulate` | Phát hiện bằng script chạy thử cả 10 kịch bản trước khi viết test chính thức. Sửa: khởi tạo session ở RUNNING cho kịch bản tập trung sản xuất (boot sequence đã kiểm ở P1/P2, không cần lặp lại) |
| 2 | Chuyển trạng thái giữa hai non-production states KHÁC NHAU (vd ESTOP→IDLE khi phục hồi) không đóng/mở lại khoảng downtime — khiến cả khoảng downtime bị gán category của trạng thái ĐẦU TIÊN dù đã đổi sang trạng thái khác | `msfc.analytics.events.from_state_changed` | Phát hiện qua cùng script chạy thử. Sửa: khi from/to đều non-production nhưng khác nhau, phát cả `DOWNTIME_END` lẫn `DOWNTIME_START` (đóng interval cũ, mở interval mới đúng category) |
| 3 | Ban đầu định tính PLANNED downtime giống các loại downtime khác (trừ vào Run Time) — không khớp định nghĩa OEE kinh điển (Nakajima), khiến ca có nghỉ đúng lịch vẫn bị "phạt" Availability | `msfc.analytics.calculations`/`session` | Phát hiện khi thiết kế kịch bản `planned_downtime`/`unplanned_downtime` để so sánh trực tiếp. Sửa: tách downtime thành "loại khỏi mẫu số" (PLANNED/MAINTENANCE) vs "trừ vào tử số" (còn lại) — D-049, ghi quyết định thay vì tự chọn ngầm (đúng chỉ thị P4.4) |

### Chưa chạy / ngoài phạm vi (NOT RUN)

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| REAL OEE VALIDATION (dây chuyền/sản xuất thật) | **NOT RUN** | HARDWARE = NONE, không có sự kiện máy thật |
| ESP32 target build | **NOT RUN** | Không đổi từ Phase 1/2/3 — thiếu ESP-IDF SDK |
| Publish `oee.state.metrics` qua MQTT thật (`oee_metrics.v1` vẫn là draft) | **NOT RUN — có chủ đích** | `msfc.services` chưa xây — D-040/D-048/Q-17/Q-18 |
| Dashboard tiêu thụ `MachineStatus`/`OeeResult` | **NOT RUN — có chủ đích** | P4.19: không xây dashboard lượt này |
| `msfc.storage` (SQLite/khác) thay cho `InMemoryOeeSnapshotRepository` | **NOT RUN — có chủ đích** | Ngoài phạm vi P4.17; cần `msfc.services` nối `analytics`+`storage` — D-050 |

---

## Phase 5 — Software-only Machine Health / Anomaly Detection / Predictive Maintenance, 2026-09-18

> **SOFTWARE-ONLY. KHÔNG claim độ chính xác predictive maintenance thật.** Toàn bộ cảm biến là mô phỏng/mock (`msfc.analytics.health_simulate`, `FixedSequenceSensorSource`), không cảm biến/máy/MQTT broker thật. `RuleBasedReferenceModel` KHÔNG phải mô hình đã huấn luyện.

### Kết quả chạy targeted (trong lúc implement)

| File test mới | Số case | Kết quả | Phạm vi |
|---|---:|---|---|
| `test_analytics_health_models.py` | 10 | **PASS** | P5.1 (domain model, 5-state HealthState) |
| `test_analytics_sensors.py` | 4 | **PASS** | P5.2 (sensor abstraction, Mock/FixedSequence) |
| `test_analytics_quality.py` | 16 | **PASS** | P5.3 (data quality: NaN/Inf/stale/future/duplicate/unit) |
| `test_analytics_features.py` | 10 | **PASS** | P5.4 (feature extraction, RMS, moving average) |
| `test_analytics_baseline.py` | 10 | **PASS** | P5.5 (baseline, deviation, z-score) |
| `test_analytics_anomaly.py` | 16 | **PASS** | P5.6/P5.8 (threshold/trend/quality detection, severity combination) |
| `test_analytics_health_score.py` | 6 | **PASS** | P5.7 (health score) |
| `test_analytics_health_events.py` | 9 | **PASS** | P5.9 (health event factories) |
| `test_analytics_health_monitor.py` | 10 | **PASS** | P5.10 (monitor orchestration, out-of-order rejection, event drain) |
| `test_analytics_predictive.py` | 9 | **PASS** | P5.11/P5.12 (predictive abstraction — never marked validated) |
| `test_analytics_health_repository.py` | 5 | **PASS** | P5.19 (storage abstraction, in-memory) |
| `test_analytics_evaluation.py` | 12 | **PASS** | P5.21 (evaluation framework, hand-computed metrics only) |
| `test_analytics_health_p4_bridge.py` | 5 | **PASS** | P5.16/P5.17 (opt-in bridge, WARNING/ANOMALY never bridge) |
| `test_analytics_health_fixtures.py` | 19 | **PASS** | P5.13/P5.14 (15 scenarios + remaining named fixtures) |
| `tests/integration/test_analytics_health_p4_integration.py` | 2 | **PASS** | P5.16 — bridge tested against the REAL, unmodified `ProductionSession` (P4) |

### Kết quả gate (sau khi implement xong)

**Lệnh:** `cd edge && python -m pytest`
**Kết quả:** `712 passed, 1 skipped in 13.11s` — tăng đúng 143 từ 569+1 trước đó, **0 test cũ hỏng**.

`test_layer_dependencies.py` (2 test, P0, không sửa) tiếp tục PASS. **Firmware:** không sửa file C nào lượt này — vẫn 262/262 (không chạy lại, không có gì thay đổi để kiểm).

### 15 kịch bản simulation (P5.13/P5.14) — kết quả hand-checked

| # | Kịch bản | Health state | Ghi chú |
|---|---|---|---|
| 1 | normal_temperature | HEALTHY | |
| 2 | rising_temperature | ANOMALY | trend(WARNING) + deviation(ANOMALY) đồng thời |
| 3 | temperature_spike | CRITICAL | dùng giá trị cực trị, không phải mean (D-055) |
| 4 | normal_motor_current | HEALTHY | |
| 5 | increasing_motor_current | ANOMALY | |
| 6 | current_spike | CRITICAL | |
| 7 | normal_vibration | HEALTHY | |
| 8 | increasing_vibration | ANOMALY | |
| 9 | vibration_spike | CRITICAL | |
| 10 | sensor_failure | WARNING | sensor_quality anomaly |
| 11 | missing_sensor_data | WARNING | |
| 12 | stale_sensor_data | WARNING | |
| 13 | multiple_simultaneous_anomalies | CRITICAL | 6 anomaly trên 3 cảm biến |
| 14 | recovery_after_anomaly | HEALTHY | dùng window_ms nhỏ (2.5s) để spike thoát khỏi cửa sổ — window-size ảnh hưởng tốc độ "phục hồi", đã ghi tài liệu trong `health_monitor.py` |
| 15 | critical_machine_condition | CRITICAL | 6 anomaly, cả 3 cảm biến đồng thời vượt ngưỡng critical |

### Lỗi tự phát hiện và sửa qua test (đã sửa trước khi viết test chính thức)

| # | Phát hiện | Nơi | Xử lý |
|---|---|---|---|
| 1 | `detect_baseline_anomaly()` dùng **trung bình (mean)** của cửa sổ — một đỉnh nhọn (spike) giữa 6 giá trị bình thường bị pha loãng dưới mọi ngưỡng hợp lý, khiến cả 3 kịch bản "spike" (temperature/current/vibration) báo sai HEALTHY | `msfc.analytics.anomaly` | Phát hiện bằng script chạy thử cả 15 kịch bản trước khi viết test chính thức (cùng kỷ luật D-039/D-044/D-049). Sửa: dùng giá trị **cực trị** (max/min) của cửa sổ — D-055 |
| 2 | `AnomalyThresholds` ban đầu dùng chung một bộ ngưỡng cho mọi cảm biến — không hợp lý vì thang đo khác nhau hoàn toàn (°C vs mm/s vs A) | `msfc.analytics.anomaly`/`health_monitor`/`predictive` | Phát hiện cùng lúc với lỗi #1. Sửa: `dict[str, AnomalyThresholds]` theo từng `sensor_id`, giống `baselines` đã có — D-056 |

### Chưa chạy / ngoài phạm vi (NOT RUN)

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| REAL MACHINE-HEALTH VALIDATION (máy/cảm biến thật) | **NOT RUN** | HARDWARE = NONE, không có cảm biến thật |
| REAL PREDICTIVE-MAINTENANCE VALIDATION | **NOT RUN** | Không có dữ liệu suy giảm máy thật để huấn luyện/hiệu chỉnh bất kỳ mô hình nào |
| ESP32 target build | **NOT RUN** | Không đổi từ Phase 1-4 — thiếu ESP-IDF SDK |
| Publish `health.state`/`health.telemetry.features` qua MQTT thật (draft) | **NOT RUN — có chủ đích** | `msfc.services` chưa xây; xung đột 5-state/8-sensor-type với draft schema đã ghi (D-051/Q-19) |
| ROC-AUC/PR-AUC trong `evaluation.py` | **NOT RUN — có chủ đích** | Cần một classifier có điểm số thật để đánh giá; chưa tồn tại — D-053 |
| `msfc.storage` (SQLite/khác) thay cho `InMemorySensorHistoryRepository` | **NOT RUN — có chủ đích** | Ngoài phạm vi P5.19; cần `msfc.services` nối `analytics`+`storage`, cùng lý do D-050 |

## Phase 6 — Edge AI Platform / Final Software Integration, 2026-09-19

> **SOFTWARE-ONLY, FINAL SOFTWARE PHASE.** `msfc.services.CellRuntime` chạy đối chọi với `msfc.sim.SimCellController` (mô phỏng, không sửa) qua `InMemoryBus` (mô phỏng, không sửa) — chưa có ESP32/camera/cảm biến/broker MQTT thật nào tham gia.

### Kết quả chạy targeted (trong lúc implement)

| File test mới | Số case | Kết quả | Phạm vi |
|---|---:|---|---|
| `test_services_platform_model.py` | 11 | **PASS** | P6.1 (domain model, RuntimeState/PipelineOutcome/ProductCycleTrace) |
| `test_services_codec.py` | 11 | **PASS** | P6.6 (decode round-trip vs `msfc.sim.codec`'s encoders; encode verdict/control/heartbeat vs schema) |
| `test_services_timing.py` | 5 | **PASS** | P6.12 (StageTimer/TimingStats, host-only) |
| `test_services_vision_pipeline.py` | 5 | **PASS** | P6.2 (vision composition: GOOD/DEFECT/UNCERTAIN, ROI failure, engine crash) |
| `test_services_safety_gate.py` | 7 | **PASS** | P6.4 (courtesy gate: unknown/latched/allowed states) |
| `test_services_health_pipeline.py` | 5 | **PASS** | P6.2/P6.11 (sensor→monitor composition, failing sensor not faked, critical bridge) |
| `test_services_pipeline.py` | 11 | **PASS** | P6.5 (precedence: safety gate → vision/OCR fail-closed → DecisionEngine) |
| `test_services_runtime.py` | 8 | **PASS** | P6.3 (lifecycle vs REAL `SimCellController`: INIT/READY/RUNNING/SAFE_STOP/DEGRADED/FAULT/SHUTDOWN) |
| `test_services_fixtures.py` | 11 | **PASS** | P6.15 (26 reusable deterministic fixtures) |
| `tests/integration/test_services_scenarios.py` | 20 | **PASS** | P6.14 — all 20 PO-listed scenarios, against REAL `SimCellController` |
| `tests/integration/test_services_full_stack_integration.py` | 2 | **PASS** | P6.16 — one full-stack success path, one full-stack failure path |

### Kết quả gate (sau khi implement xong)

**Lệnh:** `cd edge && python -m pytest`
**Kết quả:** `808 passed, 1 skipped in 10.37s` — tăng đúng 96 từ 712+1 trước đó, **0 test cũ hỏng**.

`test_layer_dependencies.py` (2 test, P0, không sửa) tiếp tục PASS **không cần thêm dòng nào** — `services` đã được khai báo sẵn từ Phase 0. **Firmware:** không sửa file C nào lượt này — chạy lại để xác nhận: `262 checks run, 0 failed`.

### 20 kịch bản end-to-end (P6.14) — kết quả

| # | Kịch bản | Kết quả then chốt |
|---|---|---|
| 1 | GOOD product | PASSED |
| 2 | DEFECT product | REJECTED, VERDICT_DEFECT |
| 3 | UNCERTAIN vision | REJECTED (fail-closed default policy) |
| 4 | OCR valid | PASSED |
| 5 | OCR invalid (expired) | REJECTED |
| 6 | OCR unavailable (misconfigured) | REJECTED, NO_DECISION |
| 7 | Vision unavailable (engine crash) | REJECTED, NO_DECISION; runtime DEGRADED |
| 8 | Safety denial | outcome=SAFETY_DENIED, không publish verdict |
| 9 | Communication loss | cell → FAULT (F010); runtime → SAFE_STOP |
| 10 | Machine-health WARNING | health_state=WARNING |
| 11 | Machine-health ANOMALY | health_state=ANOMALY |
| 12 | Machine-health CRITICAL, bridge bật | PASSED sản phẩm; OEE current_fault=F070 (không chặn sản xuất, D-054) |
| 13 | Nhiều lỗi đồng thời (vision + sensor) | subsystems.degraded = {vision, health} |
| 14 | Recovery (ESTOP→reset→RUNNING) | SAFE_STOP → READY → RUNNING |
| 15 | Degraded mode: OEE không cấu hình | RUNNING (không tự động DEGRADED chỉ vì thiếu cấu hình) |
| 16 | Sản xuất bình thường (4 sản phẩm GOOD) | good_count=4, defect_count=0 |
| 17 | Lô trộn GOOD/DEFECT | good_count=2, defect_count=3 |
| 18 | Sự kiện dị dạng | bị drop, không crash, không phát verdict |
| 19 | Subsystem timeout (mô hình bằng exception) | REJECTED, NO_DECISION |
| 20 | Full clean shutdown | SHUTDOWN, frame_source đóng, idempotent, không phát verdict sau đó |

### Lỗi tự phát hiện và sửa qua test (đã sửa trước khi chốt)

| # | Phát hiện | Nơi | Xử lý |
|---|---|---|---|
| 1 | `CellIdentity` ban đầu chỉ có MỘT `device_id` dùng chung cho cả topic `conveyor/*` (Cell Controller) và `system/*` (Edge Server) — hai thiết bị khác nhau theo MQTT_CONTRACT.md | `msfc.services.platform_model`/`runtime` | Phát hiện khi viết `send_heartbeat()`. Sửa: tách `cell_device_id`/`edge_device_id` — D-058 |
| 2 | Test kịch bản 12/13 ban đầu gọi thẳng `MachineHealthMonitor.ingest()` rồi mong `CellRuntime.process_sensors()` "thấy" — sai giả định, vì `process_sensors()` chỉ đọc qua `SensorSource` đã cấu hình | Thiết kế test (`test_services_scenarios.py`) | Sửa THIẾT KẾ TEST dùng `FixedSequenceSensorSource`/sensor giả lỗi qua đúng cổng vào công khai — không sửa code sản phẩm — D-061 |

### Chưa chạy / ngoài phạm vi (NOT RUN)

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| REAL HARDWARE VALIDATION (mọi loại) | **NOT RUN** | HARDWARE = NONE |
| REAL EDGE DEPLOYMENT | **NOT RUN** | Chưa deploy lên thiết bị Edge thật nào |
| ESP32 target build | **NOT RUN** | Không đổi từ Phase 1-5 — thiếu ESP-IDF SDK |
| Chạy `CellRuntime` qua `MqttBus` với broker Mosquitto thật | **NOT RUN — có chủ đích** | Không cài Mosquitto (đúng chỉ thị PO); `MqttBus` (P1, không sửa) đã là implementation thật của cùng `MessageBus` interface |
| Publish `oee.state.metrics`/`health.state`/`health.telemetry.features` qua MQTT thật | **NOT RUN — có chủ đích** | D-060: schema vẫn draft/xung đột chưa PO quyết định (Q-17/Q-18/Q-19) |
| Timing model so với phần cứng thật | **NOT RUN — có chủ đích** | `StageTimer`/`TimingStats` chỉ đo host/simulation, ghi rõ trong docstring |

## Official Web Dashboard, 2026-09-19

> **SOFTWARE SIMULATION.** `msfc.dashboard.session.DemoSession` sở hữu một `SimCellController`+`CellRuntime`+`InMemoryBus` thật (không mock ở tầng nghiệp vụ) — chỉ chưa có phần cứng/broker/camera thật.

### Kết quả chạy targeted (trong lúc implement)

| File test mới | Số case | Kết quả | Phạm vi |
|---|---:|---|---|
| `test_services_runtime_observability.py` | 7 | **PASS** | Mở rộng bồi thêm `product_history()`/`event_log()` (D-066) |
| `test_dashboard_dtos.py` | 11 | **PASS** | DTO builders thuần — không tính lại verdict/OEE/health |
| `test_dashboard_session.py` | 11 | **PASS** | `DemoSession`: start/stop/reset, 7 simulate control, full demo |
| `tests/integration/test_dashboard_api.py` | 22 | **PASS** | 20 mục yêu cầu (mục 13 chỉ thị) + WebSocket + OpenAPI, qua `TestClient` thật |

### Kết quả gate (sau khi implement xong)

**Lệnh:** `cd edge && python -m pytest`
**Kết quả:** `859 passed, 1 skipped` — tăng đúng 51 từ 808+1 trước đó, **0 test cũ hỏng**.

`test_layer_dependencies.py` (2 test) tiếp tục PASS sau khi mở rộng `ALLOWED["dashboard"]` (D-065). **Firmware:** không sửa file C nào — chạy lại xác nhận `262 checks run, 0 failed`.

### 20 mục test bắt buộc (mục 13 chỉ thị) — kết quả

| # | Mục | Test | Kết quả |
|---|---|---|---|
| 1-2 | Dashboard/backend adapter khởi động | `test_01`, `test_02` | PASS |
| 3-10 | Overview/Production/Vision/OCR/Safety/Health/OEE/Event log load | `test_03`–`test_10` | PASS |
| 11-13 | Controller state, E-STOP, UNKNOWN hiển thị đúng | `test_11`–`test_13` | PASS |
| 14 | Backend unavailable → SYSTEM OFFLINE | `test_14` | PASS |
| 15 | Invalid control command bị từ chối (4xx) | `test_15` | PASS |
| 16 | Simulation mode tường minh | `test_16` | PASS |
| 17 | Full demo end-to-end | `test_17` | PASS |
| 18 | Không bypass P2 | `test_18` | PASS |
| 19 | Không tự tính OEE | `test_19` | PASS |
| 20 | Không tự quyết định sản phẩm | `test_20` | PASS |

### Xác minh trực quan qua trình duyệt thật (Claude Browser tool)

Server chạy thật (`python edge/run_dashboard.py`, `preview_start`), thao tác trực tiếp: START → SIMULATE GOOD → SIMULATE DEFECT → xem đủ 8 tab (Overview/Production/Vision&OCR/Safety/Machine Health/OEE/Event Log/Diagnostics) → E-STOP → xác nhận SAFETY_DENIED cho sản phẩm tiếp theo → RESET → START (phục hồi) → RUN FULL DEMO (modal tổng kết đúng 14 bước). Không có lỗi console JS nào (`read_console_messages` rỗng). Ảnh chụp màn hình lưu trong phiên làm việc.

### Lỗi tự phát hiện và sửa qua test (đã sửa trước khi chốt)

| # | Phát hiện | Nơi | Xử lý |
|---|---|---|---|
| 1 | `DemoSession._advance()` nhảy một bước thời gian mô phỏng lớn (vd. >1000ms để phục hồi sức khỏe máy) — gây lỗi COMM_LOSS (F010) giả vì đồng hồ nhảy nhanh hơn `heartbeat_timeout_ms` | `msfc.dashboard.session` | Chia nhỏ bước nhảy (`_SAFE_ADVANCE_STEP_MS=200`), làm tươi heartbeat sau mỗi bước con — D-067 |
| 2 | Test ban đầu mong nút "RECOVERY" đưa sức khỏe máy về HEALTHY ngay lập tức | `test_dashboard_session.py` (thiết kế test) | Sai giả định — hành vi P5 cửa sổ trung bình (D-055) vẫn đúng; sửa `simulate_health_recovery()` chủ động nhảy đồng hồ qua khỏi cửa sổ trước khi đẩy giá trị khỏe mạnh — D-067 |

### Chưa chạy / ngoài phạm vi (NOT RUN)

| Nhóm | Trạng thái | Lý do |
|---|---|---|
| Test frontend JS tự động (Selenium/Playwright) | **NOT RUN — có chủ đích** | Tránh hạ tầng không cần thiết cho dự án sinh viên; xác minh trực quan thủ công qua Claude Browser tool đã thay thế |
| Nhiều người dùng / xác thực đồng thời | **NOT RUN** | Ngoài phạm vi — một phiên demo cục bộ |
| Deploy thật (không phải `127.0.0.1`) | **NOT RUN** | Ngoài phạm vi Official Dashboard lượt này |

## Phase 1 — Hardware-in-the-loop (P1.9 trở đi) — chưa bắt đầu

Sẽ ghi kết quả theo bảng acceptance [AC-P1-01..11](docs/PHASE1_PLAN.md#5-acceptance-criteria-của-phase-1), kèm:
- Dữ liệu đo thời gian (p50/p95/max, `margin_ms`) xuất từ `telemetry/timing` và `product_sorted` **trên phần cứng thật**.
- Ma trận nhầm lẫn của mô hình vision trên tập test chia theo phiên chụp, dữ liệu **thật**.
- Bằng chứng test an toàn: video/ảnh + log `fault`.
