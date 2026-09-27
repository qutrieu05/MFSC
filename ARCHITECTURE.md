# Architecture — Mini Smart Factory Cell (MSFC)

**Phiên bản:** 0.1 (DRAFT — chờ PO duyệt) · **Ngày:** 2026-09-17
**Tài liệu liên quan:** [REQUIREMENTS](docs/REQUIREMENTS.md) · [SAFETY_CONCEPT](docs/SAFETY_CONCEPT.md) · [MQTT_CONTRACT](docs/MQTT_CONTRACT.md) · [DECISIONS](DECISIONS.md)

> Mọi ADR trong tài liệu đang ở trạng thái **PROPOSED** cho tới khi PO duyệt Phase 0.

---

## 1. Nguyên tắc kiến trúc

| # | Nguyên tắc | Hệ quả |
|---|---|---|
| P1 | **An toàn nằm ở tầng embedded và fail-safe theo "vắng mặt"** | Mất heartbeat hoặc tín hiệu an toàn → dừng. Không có tín hiệu nào từ laptop có quyền "giữ cho máy chạy" |
| P2 | **ESP32 sở hữu danh tính sản phẩm và thời gian thực** | Laptop chỉ gửi *khuyến nghị* (verdict) cho một `product_id`; ESP32 tự quyết định thời điểm gạt |
| P3 | **Không có verdict = loại bỏ** | Lỗi AI/mạng làm giảm năng suất chứ không để lọt sản phẩm lỗi |
| P4 | **Contract-first** | Topic, payload, QoS, retain định nghĩa trong `contracts/` trước khi code |
| P5 | **Simulation-first** | Mỗi layer test được trên laptop bằng simulator/mock trước khi nối phần cứng |
| P6 | **Cấu hình thay vì hard-code** | Ngưỡng, thời gian, đường dẫn, topic đều từ config/registry |
| P7 | **Layer phụ thuộc một chiều** | Có test tự động kiểm tra import (mục 7.2) |
| P8 | **Module nhỏ, một trách nhiệm** | Không có file "god object"; hướng dẫn ≤ ~400 dòng/file |

---

## 2. Bối cảnh hệ thống và các node triển khai

```
                 ┌───────────────────────── LAPTOP (Windows 11, RTX 3050) — Edge Server ─────────────────────────┐
                 │  L3 Vision/OCR/SafetyVision   L4 Decision   L5 MQTT broker + adapter   L6 Services            │
                 │  L7 Storage/Analytics (JSONL → SQLite)      L8 Dashboard                                        │
                 └──────────────▲─────────────────────────────────────────▲──────────────────────────────────────┘
          USB camera(s) ────────┘                                         │ Wi-Fi LAN (MQTT, không Internet)
                                                                          │
   ┌──────────────────────────────────────────────────────────────────────┴───────────────────────────────┐
   │ N1: ESP32 Cell Controller — L0 Safety supervisor · L2 Firmware · điều khiển L1                          │
   └───────┬───────────────┬───────────────┬──────────────┬───────────────┬──────────────┬─────────────────┘
      E-stop (NC)      IR S1 / S2     Motor driver     Servo pusher   LED + LCD     RESET/START
      (ngắt cứng nguồn   (sản phẩm)   + safety relay
       động cơ)
   N3 (Phase 5): ESP32 Health Node — rung / nhiệt / dòng  ──MQTT──►  Edge Server
   N4 (FUTURE):  Camera node (Jetson Nano / ESP32-S3)     ──MQTT──►  Edge Server
```

| Node | Phần cứng | Vai trò | Phase |
|---|---|---|---|
| **N1** Cell Controller | ESP32 (model chờ xác nhận) | An toàn tầng embedded, băng tải, cảm biến sản phẩm, actuator, HMI tại chỗ | 1 |
| **N2** Edge Server | Laptop Windows 11 + RTX 3050 | Vision, OCR, safety vision, decision, broker, service, lưu trữ, dashboard | 1 |
| **N3** Health Node | ESP32 thứ hai (nếu có) hoặc chung N1 | Cảm biến sức khỏe động cơ | 5 |
| **N4** Camera Node | Jetson Nano / ESP32-S3 camera | Suy luận tại camera (tùy chọn) | 6 / FUTURE |
| Raspberry Pi | Có sẵn | **Không dùng trong S1** (dự phòng: broker/dashboard tách khỏi laptop) | FUTURE |

---

## 3. Chín layer và trách nhiệm

| Layer | Tên | Chạy ở | Trách nhiệm chính | Interface ra ngoài | Phase |
|---|---|---|---|---|---|
| **L0** | Safety / Embedded Control | N1 | E-stop (cứng), giám sát heartbeat, chốt lỗi, safe state, watchdog, ưu tiên an toàn | Trạng thái an toàn → L2; lệnh "cho phép động cơ" → L1 | 1 |
| **L1** | Sensors / Actuators | N1, N3 | Động cơ + driver + safety relay, servo, IR S1/S2, nút bấm, LED, LCD, cảm biến sức khỏe | HAL C API (IF-01) | 1, 5 |
| **L2** | ESP32 Firmware | N1, N3 | Máy trạng thái cell, theo dõi sản phẩm, điều khiển động cơ/actuator, xử lý lệnh, telemetry | MQTT contract (IF-02) | 1 |
| **L3** | Camera / CV / Edge AI | N2 | Thu ảnh, tiền xử lý, suy luận, hậu xử lý (vision, OCR, safety vision) | `FrameSource`, `InferenceEngine`, `InspectionResult` (IF-03..05) | 1, 2, 3 |
| **L4** | Decision Engine | N2 | Kết hợp kết quả L3 → verdict + mã lý do; nhật ký quyết định | `DecisionEngine.decide()` (IF-06) | 1 |
| **L5** | MQTT Communication | N2 (+ client trên N1/N3) | Broker, registry topic, envelope, kiểm tra payload, kết nối lại | `MessageBus` (IF-07) | 1 |
| **L6** | Edge Server | N2 | Điều phối service, self-check, heartbeat, chẩn đoán, CLI | Service lifecycle API | 1 |
| **L7** | Database / Data Processing | N2 | Event log (JSONL, P1) → SQLite (P4); OEE, phân tích sức khỏe | `Repository` (IF-08) | 1, 4, 5 |
| **L8** | Dashboard / Monitoring | N2 | Hiển thị trạng thái, số liệu, sự kiện; P1 dùng CLI monitor | Data API (IF-09) | 4, 6 |

---

## 4. Máy trạng thái Cell Controller (N1)

```
             ┌──────┐   auto   ┌───────────┐  pass   ┌──────┐ start (guards OK)  ┌──────────┐ ramp done ┌─────────┐
  power on ─►│ BOOT │────────►│ SELF_TEST │───────►│ IDLE │───────────────────►│ STARTING │──────────►│ RUNNING │
             └──────┘          └─────┬─────┘        └──▲───┘                    └──────────┘           └────┬────┘
                                     │ fail            │ ramp-down done                     stop cmd       │
                                     ▼                 │               ┌──────────┐◄──────────────────────┘
                                 ┌───────┐             └───────────────│ STOPPING │
                                 │ FAULT │                             └──────────┘
                                 └───────┘
  Từ MỌI trạng thái (trừ BOOT):
    E-stop active                                   → ESTOP      (chốt; reset CHỈ bằng nút RESET tại chỗ)
    zone_clear=false / safety vision stale*         → SAFE_STOP  (chốt; reset khi vùng trống ≥ clear_hold_ms)
    mất heartbeat Edge Server / lỗi nghiêm trọng**   → FAULT      (chốt; reset khi nguyên nhân đã hết)
  * chỉ khi safety.vision_required=true (Phase 2+). Ở IDLE: chỉ chặn START, không chốt.
  ** chỉ khi đang STARTING/RUNNING/STOPPING. Ở IDLE: chặn START.
  ESTOP / SAFE_STOP / FAULT --reset hợp lệ--> IDLE   (KHÔNG tự chạy lại; cần START mới)
```

**Thứ tự ưu tiên đánh giá mỗi chu kỳ điều khiển (10 ms):** `ESTOP > SAFE_STOP > FAULT > STOPPING > STARTING/RUNNING`

| Trạng thái | Động cơ | Safety relay | Pusher | Nhận verdict | LED |
|---|---|---|---|---|---|
| BOOT, SELF_TEST | Tắt | Ngắt | Thu | Không | Vàng nhấp nháy |
| IDLE | Tắt | Ngắt | Thu | Không | Vàng |
| STARTING / RUNNING | Theo ramp / setpoint | Đóng | Theo verdict | Có | Xanh |
| STOPPING | Ramp xuống | Đóng | Xử lý sản phẩm còn lại (theo cấu hình) | Có | Xanh nhấp nháy |
| SAFE_STOP | **Tắt ngay** | **Ngắt** | Thu | Không | Đỏ nhấp nháy |
| FAULT | **Tắt ngay** | **Ngắt** | Thu | Không | Đỏ |
| ESTOP | **Tắt (phần cứng)** | **Ngắt** | Thu | Không | Đỏ + còi |

---

## 5. Luồng chính

### 5.1 Luồng kiểm tra sản phẩm (Phase 1)

```
ESP32 (N1)                          MQTT broker                    Edge Server (N2)
────────────────────────────────────────────────────────────────────────────────────────────────
IR S1 cạnh lên (ISR, t1 mono)
 ├─ product_id = <boot_id>-<n>; FIFO.push({id, t1, verdict: NONE})
 └─ publish event/product_detected ─────────────────────────────►  InspectionService nhận (t_rx)
                                                                    ├─ FrameSource: chọn khung hình
                                                                    ├─ Preprocess → Inference → Postprocess
                                                                    ├─ DecisionEngine.decide() → verdict + reason
                                                                    └─ publish cmd/verdict {product_id, …}
verdict tới (t2 mono) ◄──────────────────────────────────────────
 └─ gắn verdict vào FIFO theo product_id (quá hạn → ghi LATE)
IR S2 cạnh lên (t3 mono)
 ├─ head = FIFO.pop()   (FIFO rỗng → lỗi TRACKING_MISMATCH, xử lý theo cấu hình)
 ├─ verdict DEFECT hoặc NONE → hẹn giờ gạt sau push_delay_ms (t4)
 └─ publish event/product_sorted {id, action, reason, t1..t4}
```

**Điểm đo thời gian** (NFR-PERF-01):
- `t2 − t1`: đo trên **cùng đồng hồ ESP32**, không cần đồng bộ giờ.
- Vision báo cáo thời gian từng bước trên đồng hồ laptop.
- Biên an toàn thời gian: `t3 − t2 > 0` cho mọi sản phẩm.

**Ngân sách thời gian ban đầu (p95, chờ đo):**

| Bước | Ngân sách |
|---|---|
| Publish S1 | 20 ms |
| Mạng → laptop | 50 ms |
| Chọn khung hình | 50 ms |
| Tiền xử lý | 10 ms |
| Suy luận | 50 ms |
| Quyết định | 5 ms |
| Mạng → ESP32 | 50 ms |
| **Tổng** | **≈ 235 ms** (mục tiêu ≤ 300 ms) |

Thời gian sản phẩm đi từ S1 tới S2 = `d_S1S2 / v_belt` phải lớn hơn p99 độ trễ tối thiểu **1 s** (cấu hình hình học trong `config`).

### 5.2 Luồng an toàn

| Nguồn | Tần suất | Timeout tại ESP32 | Phản ứng |
|---|---|---|---|
| E-stop phần cứng | Liên tục (mạch cứng) | – | Nguồn động cơ bị ngắt vật lý + `ESTOP` |
| `system/edge01/heartbeat` | 5 Hz | `comm.heartbeat_timeout_ms` = 1000 | `FAULT(COMM_LOSS)` |
| `safety/safecam01/heartbeat` (P2) | ≥ 5 Hz | `safety.vision_stale_ms` = 600 | `SAFE_STOP(SAFETY_VISION_LOST)` |
| `zone_clear=false` (P2) | – | – | `SAFE_STOP(ZONE_INTRUSION)` |
| Watchdog task | – | cấu hình IDF | Reset → BOOT (safe) + ghi lý do |

Heartbeat an toàn phải có `frame_seq` tăng dần và `frame_age_ms`. ESP32 coi **seq không tăng** là tín hiệu cũ (chống lỗi "kẹt ở zone_clear=true").

### 5.3 Luồng lỗi và phục hồi

Lỗi → ESP32 chốt mã lỗi + safe state → hiển thị LED/LCD → lưu bộ đệm vòng → publish `fault` (khi có mạng) → Edge Server ghi log + dashboard → người vận hành xử lý nguyên nhân → RESET (tại chỗ, hoặc từ xa nếu được phép) → IDLE → START. Bảng mã lỗi: [SAFETY_CONCEPT.md](docs/SAFETY_CONCEPT.md) mục 5.

---

## 6. Cấu trúc firmware (N1), đề xuất theo ESP-IDF 5.x (ADR-0006)

```
firmware/cell_controller/
├── main/app_main.c            # chỉ khởi tạo và tạo task
└── components/
    ├── core_logic/            # C thuần, KHÔNG include ESP-IDF → unit test trên host
    │   ├── cell_sm.*          # máy trạng thái cell (bảng chuyển trạng thái)
    │   ├── safety_supervisor.*# tổng hợp E-stop, heartbeat, zone → yêu cầu an toàn
    │   ├── product_tracker.*  # FIFO S1→S2, gắn verdict, phát hiện lệch
    │   ├── heartbeat_monitor.*# timeout + kiểm tra seq tăng
    │   ├── fault_manager.*    # mã lỗi, chốt, bộ đệm vòng
    │   └── debounce.*, timing_stats.*
    ├── hal/                   # phụ thuộc ESP-IDF: GPIO, LEDC (PWM), I2C LCD, relay, thời gian
    ├── comm/                  # Wi-Fi, esp-mqtt, codec JSON (cJSON), topics_gen.h (sinh từ registry)
    └── app/                   # control_task (10 ms), comm_task, ui_task, cmd_handler, config_store (NVS)
```

**Quy tắc:**
- `core_logic` không phụ thuộc gì.
- `hal` và `comm` chỉ được gọi từ `app`.
- `control_task` có ưu tiên cao nhất trong các task ứng dụng và **không bao giờ chờ mạng** (chỉ trao đổi qua queue không chặn).
- Timestamp cạnh S1/S2 được chụp trong ISR.

---

## 7. Cấu trúc Edge Server (N2)

### 7.1 Package Python `msfc` (`edge/src/msfc/`)

| Package | Layer | Nội dung | Phase |
|---|---|---|---|
| `core` | chung | cấu hình, logging, lỗi, tiện ích thời gian | **0 (đã tạo)** |
| `domain` | chung | dataclass thuần: `ProductEvent`, `InspectionResult`, `Verdict`, `ReasonCode`, `Fault` | 1 |
| `contracts` | L5 | nạp registry topic, tạo/đọc envelope, kiểm tra payload | 1 |
| `comm` | L5 | `MessageBus` interface; `MqttBus` (paho-mqtt); `InMemoryBus` cho test | 1 |
| `vision` | L3 | `FrameSource` (USB, video, ảnh), preprocess, `InferenceEngine` (baseline, ONNX), postprocess, metrics | 1 |
| `safety_vision` | L3 | vùng đa giác, phát hiện người, quyết định chiếm vùng, heartbeat payload | 2 |
| `ocr` | L3 | định vị nhãn, OCR, trích xuất và kiểm tra hạn dùng | 3 |
| `decision` | L4 | luật, `DecisionEngine`, nhật ký quyết định | 1 |
| `storage` | L7 | JSONL event log (P1), repository SQLite (P4) | 1, 4 |
| `analytics` | L7 | tính OEE, phân tích sức khỏe | 4, 5 |
| `services` | L6 | vòng đời service, orchestrator, inspection/safety/oee/health service, chẩn đoán | 1 (kế hoạch) → **6 (đã xây dựng)** |
| `dashboard` | L8 | công nghệ chờ quyết định ở Phase 4 (ADR-0012) | 4 |
| `sim` | test | simulator ESP32 cell, camera giả | 1 |
| `cli` | L6 | `msfc run`, `msfc doctor`, `msfc monitor`, `msfc eval` | 1 |

### 7.2 Quy tắc phụ thuộc giữa package (kiểm tra bằng test tự động)

| Package | Được import |
|---|---|
| `core` | (không có) |
| `domain` | `core` |
| `contracts` | `core` |
| `comm` | `core`, `contracts` |
| `vision`, `safety_vision`, `ocr` | `core`, `domain` |
| `decision` | `core`, `domain` |
| `storage`, `analytics` | `core`, `domain` |
| `services` | mọi package trừ `dashboard`, `sim`, `cli` |
| `dashboard` | `core`, `domain`, `contracts`, `comm`, `storage` |
| `sim` | `core`, `domain`, `contracts`, `comm` |
| `cli` | mọi package |

**Hệ quả:** L3 và L4 **không biết MQTT tồn tại**; chỉ `services` nối chúng với `comm`. Nhờ đó có thể test vision/decision thuần bằng dữ liệu.

---

## 8. Danh sách interface

| ID | Interface | Giữa | Định nghĩa tại | Phase |
|---|---|---|---|---|
| IF-01 | HAL C API | L1 ↔ L2 | `firmware/.../hal/*.h` | 1 |
| IF-02 | MQTT contract | N1/N3 ↔ N2 | [MQTT_CONTRACT.md](docs/MQTT_CONTRACT.md), `contracts/` | 0 (v0.1), 1 |
| IF-03 | `FrameSource` | camera ↔ L3 | `msfc.vision` | 1 |
| IF-04 | `InferenceEngine` | L3 nội bộ | `msfc.vision` | 1 |
| IF-05 | `InspectionResult` | L3 → L4 | `msfc.domain` | 1 |
| IF-06 | `DecisionEngine.decide()` | L4 → L6 | `msfc.decision` | 1 |
| IF-07 | `MessageBus` | L5 ↔ L6/sim | `msfc.comm` | 1 |
| IF-08 | `Repository` | L6 ↔ L7 | `msfc.storage` | 4 |
| IF-09 | Dashboard data API | L7 → L8 | `msfc.dashboard` | 4 |
| IF-10 | Model registry | L3 ↔ AI pipeline | `ai/models/`, `msfc.vision` | 6 |
| IF-11 | Config và logging | mọi package | `msfc.core` | **0 (đã tạo)** |

---

## 8a. Phase 6 — `msfc.services` đã triển khai (Edge AI Cell Platform)

`services` (L6) — dự kiến từ Phase 0, hoãn tới lượt này — đã được xây dựng đúng vị trí và đúng
quy tắc phụ thuộc ở mục 7.2 (không sửa bảng đó): `msfc.services.runtime.CellRuntime` là
orchestrator duy nhất, nối `vision`/`ocr`/`decision`/`analytics` với Cell Controller (thật hoặc
`msfc.sim`) **chỉ qua** `msfc.comm.MessageBus` + `msfc.contracts` — không bao giờ import
`msfc.sim` trực tiếp (test tự động `test_layer_dependencies.py` đã chặn điều này). Nhờ vậy việc
thay `SimCellController` bằng firmware thật (khi có phần cứng) không cần sửa `msfc.services`.

Không có "SafetyState" mới nào được tạo — an toàn vẫn là `MachineState`/`LATCHED_STATES` sẵn có
(mục 4). `msfc.services` chỉ thêm một khái niệm mới thật sự: `RuntimeState` (vòng đời của chính
tiến trình orchestrator — INIT/READY/RUNNING/DEGRADED/FAULT/SAFE_STOP/SHUTDOWN), tách bạch khỏi
`MachineState` của Cell Controller. Chi tiết đầy đủ: PHASE6_COMPLETION_REPORT.md, DECISIONS.md
(D-057 trở đi).

OEE (`oee.state.metrics`) và health (`health.state`/`health.telemetry.features`) **vẫn chưa
publish qua MQTT thật** ở lượt này — 2 schema đó vẫn là draft với xung đột/câu hỏi chưa PO xác
nhận (D-048/Q-18, D-051/Q-19); `msfc.services` quan sát OEE/health bằng gọi hàm Python trực
tiếp (`MachineMonitor`/`MachineHealthMonitor`), không qua bus, cho tới khi PO quyết định.

## 9. Khả năng mở rộng

| Muốn thêm | Cách làm theo kiến trúc |
|---|---|
| Camera | `device_id` mới trong config + `FrameSource` instance mới; topic đã có `{device_id}` |
| Máy / cell | `line_id`/`device_id` mới; ESP32 mới dùng chung firmware với cấu hình NVS khác |
| Mô hình AI | Backend `InferenceEngine` mới + model card + mục registry; chọn qua config |
| Cảm biến | Kênh telemetry mới trong registry + schema; bộ phân tích trong `analytics` |
| Node suy luận tại camera (N4) | Publish cùng `inspection_result` schema, **Decision Engine không cần sửa** |

---

## 10. Triển khai và mạng

- ESP32 và laptop cùng Wi-Fi 2,4 GHz trong LAN (router riêng hoặc Windows Mobile Hotspot); **không cần Internet**.
- Mosquitto 2.x trên laptop: listener 1883 trong LAN, **bắt buộc username/password**, không cho anonymous; mở Windows Firewall cho mạng Private.
- Edge Server: Python 3.11 (đã có trên máy) + môi trường ảo; dependency khai báo trong `edge/pyproject.toml`, thêm dần theo phase.

## 11. Công nghệ và ADR (đều PROPOSED)

| ADR | Quyết định đề xuất |
|---|---|
| [0001](docs/adr/0001-repository-and-monorepo-layout.md) | Monorepo riêng `mini-smart-factory-cell/` |
| [0002](docs/adr/0002-compute-placement.md) | Laptop là edge compute chính; ESP32 điều khiển; Pi/Jetson để FUTURE |
| [0003](docs/adr/0003-safety-architecture.md) | E-stop cứng + fail-safe theo heartbeat + chốt lỗi + reset có kiểm soát |
| [0004](docs/adr/0004-mqtt-contract-and-broker.md) | MQTT 3.1.1 + Mosquitto local + registry topic + envelope JSON |
| [0005](docs/adr/0005-product-identity-and-timing.md) | ESP32 sở hữu `product_id` và thời điểm gạt; không có verdict = loại |
| [0006](docs/adr/0006-firmware-framework.md) | ESP-IDF 5.x; logic lõi C thuần test trên host |
| [0007](docs/adr/0007-edge-server-python-layering.md) | Python 3.11, package theo layer, dependency tối thiểu |
| [0008](docs/adr/0008-configuration-system.md) | TOML phân lớp (`tomllib`) + kiểm tra hợp lệ nghiêm ngặt |
| [0009](docs/adr/0009-logging-system.md) | Logging chuẩn thư viện: console + JSON lines xoay vòng |
| [0010](docs/adr/0010-vision-baseline-phase1.md) | Camera USB + OpenCV; baseline cổ điển → bộ phân loại ONNX |
| [0011](docs/adr/0011-storage-strategy.md) | JSONL (P1) → SQLite (P4) |
| [0012](docs/adr/0012-dashboard-technology-deferred.md) | Công nghệ dashboard: hoãn quyết định tới Phase 4 |
| [0013](docs/adr/0013-git-strategy.md) | Trunk-based, nhánh ngắn, Conventional Commits, tag theo phase |

## 12. Câu hỏi mở (ảnh hưởng kiến trúc)

1. Model ESP32 chính xác (ESP32 đời đầu / S3 / C3)? → ảnh hưởng pin map, tài nguyên.
2. Camera USB có sẵn không (audit không thấy camera nào đang kết nối)?
3. Có bao nhiêu ESP32? (N3 riêng hay chung N1)
4. Loại động cơ/driver có sẵn? (điện áp, dòng, có hộp số không)
5. Hành động khi sức khỏe động cơ `CRITICAL`: chỉ cảnh báo hay dừng có kiểm soát? (PO quyết định ở Phase 5)
