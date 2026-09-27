# Phase 1 Plan — Conveyor + Basic Vision Control

**Phiên bản:** 2.0 (cập nhật 2026-09-18 sau khi PO xác nhận **hardware = NONE**) · **Trạng thái:** chờ PO duyệt
**Nguyên tắc mới:** **không block project vì chưa có phần cứng.** Phase 1 chia thành 12 phần; **P1.1 → P1.8 làm hoàn toàn trên laptop với 0đ phần cứng**, chỉ sau đó mới mua theo wave.

---

## 1. MVP của Phase 1

> Một sản phẩm chạy trên băng tải, camera chụp khi cảm biến S1 kích, Edge AI phân loại GOOD/DEFECT, ESP32 gạt đúng sản phẩm lỗi tại S2, dữ liệu đi qua MQTT, và **mất kết nối thì băng tải dừng an toàn**.

Phạm vi giữ nguyên như v1.0: 1 loại sản phẩm, 3 loại lỗi tự tạo (xem [DATASET_SPEC.md](DATASET_SPEC.md)), tốc độ đai thấp, an toàn cơ bản (E-stop, boot an toàn, mất heartbeat, chốt lỗi, reset có kiểm soát, watchdog).

**Ngoài phạm vi:** vùng nguy hiểm (P2) · OCR (P3) · OEE (P4) · sức khỏe động cơ (P5) · quản lý mô hình/dashboard tổng hợp (P6) · encoder (tùy chọn) · AI chạy trên ESP32 (**không** làm ở Phase 1 theo quyết định D-021).

## 2. Mười hai phần của Phase 1

| # | Phần | Cần phần cứng? | Cần cài phần mềm (miễn phí)? | Ước tính |
|---|---|:-:|---|---|
| **P1.1** | Software Architecture: `msfc.domain`, khung package theo layer, hoàn thiện quy tắc phụ thuộc | ❌ | – | 3–5 ngày |
| **P1.2** | Camera Simulation / Test Input: `FrameSource` (ảnh tổng hợp, thư mục ảnh, video, camera USB), ring buffer có timestamp | ❌ | numpy, opencv-python | 4–6 ngày |
| **P1.3** | AI Baseline: baseline xử lý ảnh cổ điển + khung đánh giá offline (accuracy/precision/recall/FP/FN/ma trận nhầm lẫn) + pipeline huấn luyện CNN (chạy khi có dataset thật) | ❌ (dùng ảnh tổng hợp + ảnh điện thoại) | onnxruntime, (torch cho train) | 1–2 tuần |
| **P1.4** | Decision Engine: luật, mã lý do, chính sách `UNCERTAIN`/`NO_DECISION`, nhật ký quyết định | ❌ | – | 3–4 ngày |
| **P1.5** | ESP32 Firmware Architecture: module `core_logic` (C99), header HAL theo [HARDWARE_INTERFACE](HARDWARE_INTERFACE.md), danh sách test FWT, bảng chuyển trạng thái | ❌ | ESP-IDF 5.x + MSYS2 gcc (để biên dịch/test host) | 1–2 tuần |
| **P1.6** | Firmware Simulator / Mock: `msfc.sim` — mô phỏng **đầy đủ hành vi** cell (product_id, FIFO, verdict, fail-safe khi mất heartbeat, chốt lỗi, reset) + đồng hồ ảo | ❌ | – | 1 tuần |
| **P1.7** | Communication Contract (runtime): registry loader, envelope codec, kiểm tra schema, `MessageBus` + `InMemoryBus` + `MqttBus`, chống trùng, backoff | ❌ | Mosquitto, paho-mqtt, jsonschema | 1 tuần |
| **P1.8** | Hardware Interface Definition: ✅ **đã xong** ([HARDWARE_INTERFACE.md](HARDWARE_INTERFACE.md)) + gán chân theo board thật (chốt khi biết board) | ❌ | – | ✅ |
| **P1.9** | Hardware Procurement: wave W1 → W2 → W3, kiểm tra hàng về | 🛒 mua | – | phụ thuộc giao hàng |
| **P1.10** | Real Hardware Integration: nạp firmware, đấu dây theo WIRING_GUIDE, test HAL từng tín hiệu, thay `hal_host_mock` → `hal_esp32`, lắp băng tải | ✅ | – | 2–3 tuần |
| **P1.11** | Timing Calibration: đo tốc độ đai, khoảng cách, trễ gạt, phân bố độ trễ MQTT, chốt `heartbeat_timeout_ms`; thu dataset thật + huấn luyện mô hình v1 | ✅ | – | 1–2 tuần |
| **P1.12** | Full System Test: AC-P1-01..11, ST-01..06/13..17, FT-01..05/07/09..12, PT-01/02/04, LT-01, báo cáo | ✅ | – | 1–2 tuần |

**Tổng:** software-first (P1.1–P1.8) ≈ **5–7 tuần**; phần phần cứng (P1.9–P1.12) ≈ **4–7 tuần** sau khi hàng về.

## 3. Cổng nghiệm thu phần software (trước khi mua) — AC-SW

**Đây là điều kiện để chuyển sang P1.9 (mua hàng).** Tất cả chạy trên laptop, 0đ phần cứng.

| ID | Tiêu chí | Cách kiểm chứng |
|---|---|---|
| AC-SW-01 | Contract runtime hoạt động: nạp registry, tạo/đọc envelope, **payload sai bị loại** với mã `E101` | Unit test + integration test với broker local |
| AC-SW-02 | Vòng lặp end-to-end chạy trên laptop: simulator cell → vision (ảnh tổng hợp) → decision → verdict → simulator gạt → event log | `msfc run --sim` + `msfc monitor` in ra timeline; integration test tự động |
| AC-SW-03 | Logic an toàn đạt **toàn bộ** test fail-safe bằng **đồng hồ ảo**: mất heartbeat → SAFE, chốt lỗi, không tự chạy lại, pusher về vị trí an toàn, lệch theo dõi bị phát hiện, reset từ xa bị từ chối khi ESTOP | Test suite `test_safety_logic.py` (và FWT tương ứng khi có gcc) |
| AC-SW-04 | Vision pipeline + khung đánh giá cho ra ma trận nhầm lẫn trên dữ liệu **tổng hợp/điện thoại**, có đo FPS và độ trễ từng bước | `msfc eval` sinh báo cáo; ghi rõ là dữ liệu synthetic |
| AC-SW-05 | Decision engine: mọi mã lý do có test, gồm `NO_DECISION`, `UNCERTAIN`, verdict muộn | Unit test |
| AC-SW-06 | Firmware architecture: module `core_logic` + header HAL biên dịch được, có danh sách test FWT khớp ST-*; nếu đã cài gcc thì test host pass | `cmake`/script build + báo cáo |
| AC-SW-07 | [HARDWARE_MASTER_BOM](../HARDWARE_MASTER_BOM.md) + [HARDWARE_INTERFACE](HARDWARE_INTERFACE.md) được PO duyệt; wave W1 được chốt | PO approve |

## 4. Acceptance criteria của Phase 1 (giữ nguyên, cần phần cứng thật)

| ID | Tiêu chí | Ngưỡng (mục tiêu ban đầu) |
|---|---|---|
| AC-P1-01 | Phát hiện sản phẩm | ≥ 99% trên 100 sản phẩm |
| AC-P1-02 | Phân loại | recall(DEFECT) ≥ 95%, loại oan ≤ 5%, **có recall theo từng loại lỗi** |
| AC-P1-03 | Verdict tới kịp | 100% sản phẩm có verdict trước khi tới S2; mất verdict < 0,5% |
| AC-P1-04 | Actuator | gạt đúng ≥ 98% trên 100 sản phẩm |
| AC-P1-05 | Thời gian | p95 `detect→verdict` ≤ 300 ms; `margin_ms > 0` với 100% sản phẩm; vision p95 ≤ 50 ms |
| AC-P1-06 | Không phụ thuộc cloud | chạy bình thường khi ngắt Internet |
| AC-P1-07 | Phục hồi | ST-04/05/06 × 10 lần: động cơ tắt ≤ timeout + 50 ms, không tự chạy lại, reset có kiểm soát |
| AC-P1-08 | Test | unit + host + integration pass; FT-01..05, 07, 09..12 có kết quả quan sát được |
| AC-P1-09 | An toàn | ST-01, 02, 03, 13, 14, 15, 16, 17 pass kèm bằng chứng |
| AC-P1-10 | Ổn định | LT-01 chạy 2 giờ không crash |
| AC-P1-11 | Tài liệu | WIRING_GUIDE, TEST_REPORT, CHANGELOG, TROUBLESHOOTING |

**Kết quả trên simulator không dùng để tuyên bố Phase 1 đạt.** Simulator chỉ dùng cho cổng AC-SW.

## 5. Điều kiện tiên quyết còn lại

| ID | Điều kiện | Ai | Trạng thái |
|---|---|---|---|
| B1 | Duyệt Phase 0 + Phase 1 plan v2.0 | PO | ⏳ |
| B2 | ~~Xác nhận model phần cứng~~ → **đã rõ: chưa có gì**; thay bằng: PO chọn phương án trong Master BOM (động cơ, cảm biến, servo, camera) | PO | ⏳ |
| B3 | Duyệt wave W1 (0,65–1,35 triệu) | PO | ⏳ (chỉ cần khi tới P1.9) |
| B4 | Cài phần mềm miễn phí: Mosquitto (cho P1.7), ESP-IDF + gcc (cho P1.5/P1.6) | PO | ⏳ |
| B5 | Chọn sản phẩm mẫu (đề xuất: nắp chai) + gom 50–100 cái | PO | ⏳ (0đ) |

**Việc bắt đầu được ngay sau B1** (không cần B2/B3, chỉ cần một phần B4): P1.1, P1.2, P1.3 (baseline), P1.4, P1.6, P1.7.

## 6. Thứ tự thực hiện đề xuất

```
B1 duyệt
 ├─► P1.1 domain + khung package            (không cần cài gì)
 ├─► P1.7 contract runtime + MessageBus      (cần Mosquitto cho integration test)
 ├─► P1.2 FrameSource + ảnh tổng hợp
 ├─► P1.4 decision engine
 ├─► P1.6 simulator cell (dùng P1.1, P1.7)
 ├─► P1.3 vision baseline + eval harness
 │      └─► AC-SW-02: vòng lặp end-to-end trên laptop  ◄── mốc demo đầu tiên, 0đ
 ├─► P1.5 firmware architecture + core_logic + HAL header  (cần ESP-IDF + gcc)
 │      └─► AC-SW-03/06
 └─► P1.8 ✅ + duyệt BOM → P1.9 mua W1 → P1.10 → P1.11 → P1.12
```

## 7. Điểm dừng để PO làm bằng tay

| Khi nào | Claude Inc cung cấp | PO làm |
|---|---|---|
| Trước P1.7 | Hướng dẫn cài Mosquitto + tạo user/password + mở firewall LAN | Cài + báo kết quả `mosquitto -h` |
| Trước P1.5 | Hướng dẫn cài ESP-IDF 5.x + MSYS2 gcc + cách kiểm tra | Cài + báo `idf.py --version`, `gcc --version` |
| P1.9 | Danh sách mua wave W1/W2/W3 (đã có trong Master BOM) + checklist kiểm tra hàng về | Mua, kiểm tra hàng, báo kết quả |
| P1.10 | `hardware/WIRING_GUIDE.md` (pin map đã chốt, sơ đồ, cảnh báo an toàn, quy trình test từng bước) | Lắp cơ khí, đấu dây, đo nguồn, test E-stop |
| P1.11 | Hướng dẫn thu dataset (theo DATASET_SPEC) + script thu ảnh | Chụp 600–1.000 ảnh theo 3 phiên |
| P1.12 | Checklist test an toàn/lỗi/hiệu năng | Chạy test, quay video, ghi kết quả |

## 8. Rủi ro đặc thù của tình huống "chưa có phần cứng"

| ID | Rủi ro | Biện pháp |
|---|---|---|
| R-21 | Software viết theo giả định sai về phần cứng → phải sửa nhiều khi hàng về | Interface cố định trước (P1.8); simulator mô phỏng cả trường hợp xấu (cảm biến rung, trễ, mất gói) |
| R-22 | Thời gian giao hàng làm trễ Phase 1 | Mua theo wave, wave W1 nhỏ và đặt sớm ngay khi AC-SW-07 đạt; trong lúc chờ vẫn làm được P1.3/P1.5 |
| R-23 | Mua sai linh kiện (ví dụ E-stop loại NO, relay kích mức thấp) | Checklist kiểm tra hàng về (Master BOM mục 18); ghi rõ min spec |
| R-24 | Mô hình AI huấn luyện trên ảnh tổng hợp không dùng được với ảnh thật | Không dùng số liệu synthetic cho acceptance; huấn luyện lại ở P1.11 với dataset thật |
| R-25 | Chi phí vượt dự kiến khi mua lẻ nhiều lần | Gom theo wave, so giá 2–3 shop, ưu tiên phương án giá thấp trong Master BOM |
