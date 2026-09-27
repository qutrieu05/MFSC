# Phase 1 Completion Report — MSFC

**Ngày:** 2026-09-18 · **Trạng thái:** **SOFTWARE-FIRST COMPLETE** (PO approved) · **Hardware:** NONE · **Procurement:** NOT APPROVED

Đây là báo cáo tổng kết Phase 1 software-only scope, viết theo yêu cầu PO ("PO APPROVAL — CLOSE P1 SOFTWARE SCOPE"). Đây là bản **tổng hợp/tham chiếu**, không lặp lại chi tiết implementation — chi tiết đầy đủ nằm ở [PROJECT_STATUS.md](PROJECT_STATUS.md), [TASKS.md](TASKS.md), [TEST_REPORT.md](TEST_REPORT.md), [DECISIONS.md](DECISIONS.md), [CHANGELOG.md](CHANGELOG.md).

---

## 1. Phase Gate Status (5 mức)

| Mức | Trạng thái | Ghi chú |
|---|---|---|
| **SOFTWARE LOGIC** | ✅ **COMPLETE** | Toàn bộ P1.1–P1.4, P1.6–P1.8 xong; P1.5 `core_logic` C99 viết xong |
| **HOST VALIDATION** | ✅ **COMPLETE** | 367 Python test passed / 1 skipped; 131/131 firmware check passed |
| **ESP32 TARGET BUILD** | ⏳ **PENDING** | Thiếu ESP-IDF SDK (không phải lỗi code) — mục 5 |
| **REAL HARDWARE VALIDATION** | ⏳ **PENDING** | HARDWARE = NONE, chưa qua P1.9 procurement — mục 6 |
| **REAL AI VALIDATION** | ⏳ **PENDING** | Chỉ mới chạy trên dataset tổng hợp — mục 7 |

**Các mục PENDING là do phụ thuộc bên ngoài phạm vi software** (SDK chưa cài, hardware chưa mua, dataset thật chưa thu thập được) — **không phải thất bại kỹ thuật hay code không chạy được**. Mọi phần software đã viết đều có test chứng minh chạy đúng.

## 2. Completed Components (P1.1–P1.8)

| # | Thành phần | Package/Thư mục | Test |
|---|---|---|---:|
| P1.1 | Domain model (state machine enum, fault catalog, events, commands) | `edge/src/msfc/domain/` | 80 |
| P1.2 | Camera simulation (4 `FrameSource`: synthetic/folder/video/USB) | `edge/src/msfc/vision/` (frame, sources) | (trong 65) |
| P1.3 | AI: baseline cổ điển + CNN/ONNX training scaffold | `edge/src/msfc/vision/` (baseline, training, onnx_backend) | 65 + 17 |
| P1.4 | Decision Engine (luật fail-closed, chính sách UNCERTAIN) | `edge/src/msfc/decision/` | 20 |
| P1.5 | Firmware `core_logic` C99 (host-testable) | `firmware/cell_controller/components/` | 131 (C, riêng) |
| P1.6 | Cell Controller simulator ("ESP32 mock") | `edge/src/msfc/sim/` | 38 |
| P1.7 | MQTT contract runtime (registry, envelope, comm bus) | `edge/src/msfc/contracts/`, `edge/src/msfc/comm/` | 98 (45+53) |
| P1.8 | Hardware Interface Definition (HAL contract) | `docs/HARDWARE_INTERFACE.md` | — (tài liệu) |
| — | Pipeline MVP end-to-end (P1.2+P1.4+P1.6+P1.7) | `edge/tests/integration/test_full_pipeline_mvp.py` | 6 |

Vòng khép kín đã chứng minh chạy được (dữ liệu tổng hợp): `Camera/Test Input → Vision/AI → Decision Engine → Command → ESP32 Mock → Motor/Servo Mock → GOOD/DEFECT result`.

## 3. Test Evidence

| Bộ test | Kết quả | Lệnh |
|---|---|---|
| Python (toàn repo) | **367 passed, 1 skipped**, 10.91s | `cd edge && python -m pytest` |
| Firmware `core_logic` (host, C99) | **131 checks, 0 failed**, `-Wall -Wextra -Werror` sạch | `bash firmware/cell_controller/test_host/build_and_run.sh` |
| Broker MQTT thật | 1 **SKIP** (trung thực, Mosquitto chưa cài) | `edge/tests/integration/test_mqtt_bus_real_broker.py` |

Không có regression qua 3 lượt phát triển liên tiếp (350→367 Python test, luôn 0 fail). Chi tiết đầy đủ từng module: [TEST_REPORT.md](TEST_REPORT.md).

## 4. Known Limitations

1. **`ClassicCvBaseline` và `TinyCapCNN` đều không phân biệt tốt GOOD/DEFECT trên dataset tổng hợp mặc định** (R-28, D-032, D-035) — nguyên nhân: nhiễu nền + lệch vị trí ngẫu nhiên trong bộ sinh ảnh tổng hợp lớn hơn tín hiệu lỗi thật. Đã báo cáo trung thực, không tinh chỉnh để "qua" test. Cần dataset thật (P1.11) để đánh giá lại.
2. **`torch.cuda.is_available()` = False** dù có RTX 3050 (R-27) — huấn luyện hiện tại chỉ chạy CPU; cần cài lại `torch` bản CUDA trước khi huấn luyện thật.
3. **`comm_link.h` (P1.5) chỉ là interface**, chưa nối esp-mqtt thật — cần ESP-IDF + hardware để hiện thực (P1.10).
4. **`product_tracker`, `heartbeat_monitor`, `timing_stats` (firmware) chưa viết** — nằm ngoài phạm vi ưu tiên PO cho các lượt này, để BACKLOG cho vòng làm P1.5 tiếp theo.
5. **Review chỉ do một assistant thực hiện**, không có người thứ hai độc lập kiểm tra.

## 5. P1.5 Target-Build Prerequisite

**Đã có (host validation):** `core_logic` C99 (state machine, fault manager, safety supervisor, command parser, watchdog, logger, HAL boundary) build + test bằng `gcc` tìm thấy sẵn trên máy (MSYS2 UCRT64, không nằm trong PATH mặc định — D-036). 131/131 test PASS.

**Còn thiếu (ESP32 target build):** `idf.py build` — cần cài **ESP-IDF 5.x SDK** (chưa cài, không tìm thấy `IDF_PATH` hay thư mục Espressif nào trên máy). Đây là điều kiện duy nhất còn thiếu để build thật cho chip; không phải vấn đề về code hay thiết kế.

**Command cài đặt (PO tự thực hiện — Claude Inc không tự cài phần mềm mới theo đúng chỉ thị PO):**
- ESP-IDF 5.x (Windows): tải "ESP-IDF Tools Installer" tại `dl.espressif.com/dl/esp-idf` (bản offline, có sẵn toolchain xtensa).
- Sau khi cài: mở "ESP-IDF 5.x CMD" từ Start Menu để có `idf.py` sẵn trong PATH của phiên đó, rồi chạy `idf.py build` trong `firmware/cell_controller/`.

## 6. Hardware Dependencies

**HARDWARE AVAILABLE = NONE.** Chưa mua bất kỳ linh kiện nào. Toàn bộ Phase 1 software hoàn thành với **0đ phần cứng**, đúng chỉ thị PO.

Phụ thuộc phần cứng cho các bước tiếp theo (chưa được duyệt, chỉ liệt kê để rõ ràng):
- **P1.9 (procurement):** cần PO chọn phương án trong [HARDWARE_MASTER_BOM.md](HARDWARE_MASTER_BOM.md) + duyệt ngân sách wave W1 (0,65–1,35 triệu VNĐ) — **NOT APPROVED**.
- **P1.10 (hardware integration):** cần ESP32 + cảm biến + động cơ + servo + E-stop đã mua và lắp ráp, cộng ESP-IDF đã cài (mục 5).
- **P1.11 (dataset thật):** cần camera thật (hoặc điện thoại làm webcam, 0đ) + 50–100 nắp chai làm sản phẩm mẫu.

## 7. AI Validation Limitation

Mọi kết quả AI hiện tại (baseline cổ điển + CNN/ONNX) chạy **hoàn toàn trên dữ liệu tổng hợp** (`data_source: synthetic`, D-026) — **không phải bằng chứng về độ chính xác trên sản phẩm thật**. Pipeline kỹ thuật (dataset → training → checkpoint → ONNX → inference → postprocess → DecisionEngine) đã chứng minh chạy đúng end-to-end; con số accuracy/F1 cụ thể **không được dùng làm acceptance criteria** (D-026, D-035). Đánh giá AI thật cần dataset ảnh chụp từ camera thật, thu thập ở P1.11.

## 8. Remaining Validation Work

| Việc | Giai đoạn | Điều kiện mở khóa |
|---|---|---|
| Build thật cho chip ESP32 (`idf.py build`) | P1.5 (tiếp) | Cài ESP-IDF (mục 5) |
| Test MQTT trên broker thật (MT-02..05) | P1.7 (tiếp) | Cài Mosquitto |
| Hardware procurement (wave W1→W3) | P1.9 | PO duyệt BOM + ngân sách |
| Nạp firmware thật, đổi `hal_host_mock` → `hal_esp32`, lắp băng tải | P1.10 | P1.9 xong |
| Hiệu chuẩn timing + thu dataset thật + huấn luyện lại | P1.11 | P1.10 xong |
| Full System Test (AC-P1-01..11, ST/FT/PT/LT) | P1.12 | P1.11 xong |

## 9. Explicit Non-Goals lượt này (theo đúng chỉ thị PO)

Không cài ESP-IDF · không cài Mosquitto · không mua hardware · không bắt đầu Phase 2 implementation · không sửa code P1 đang chạy đúng.

## 10. Sign-off

- **PO approval:** "PO APPROVAL — CLOSE P1 SOFTWARE SCOPE" (2026-09-18) — xem nguyên văn trong lịch sử trao đổi.
- **Phase gate:** Phase 1 = **SOFTWARE-FIRST COMPLETE**, các mục PENDING không tính là thất bại.
- **Bước tiếp theo:** STOP. Chờ PO duyệt Phase 2 hoặc quyết định mở khóa P1.9/P1.5b/Mosquitto theo lịch trình riêng.
