# Firmware — Cell Controller (N1)

**Trạng thái:** 📋 **Chỉ có kiến trúc module. Chưa có code** (theo yêu cầu Phase 0: không viết implementation trước khi kiến trúc được duyệt).
**Framework đề xuất:** ESP-IDF 5.x — [ADR-0006](../../docs/adr/0006-firmware-framework.md) (cần PO xác nhận)

## 1. Trách nhiệm

Layer 0–2 trong [ARCHITECTURE.md](../../ARCHITECTURE.md): an toàn, điều khiển băng tải, cảm biến sản phẩm, cơ cấu gạt, HMI tại chỗ, giao tiếp MQTT.

**Nguyên tắc bất biến:** firmware **tự đưa hệ thống về trạng thái an toàn** khi mất laptop/MQTT/AI. Không tín hiệu nào từ bên ngoài có quyền "giữ cho máy chạy".

## 2. Cấu trúc dự kiến

```
firmware/cell_controller/
├── CMakeLists.txt
├── sdkconfig.defaults          # watchdog, brownout, log level, Wi-Fi
├── main/
│   └── app_main.c              # chỉ init + tạo task, không chứa logic
└── components/
    ├── core_logic/             # C99 thuần, KHÔNG include ESP-IDF → test trên host
    │   ├── cell_sm.c/.h            # máy trạng thái (bảng chuyển trạng thái)
    │   ├── safety_supervisor.c/.h  # E-stop + heartbeat + zone → yêu cầu an toàn
    │   ├── product_tracker.c/.h    # FIFO S1→S2, gắn verdict, phát hiện lệch
    │   ├── heartbeat_monitor.c/.h  # timeout + kiểm tra seq tăng dần
    │   ├── fault_manager.c/.h      # mã lỗi, chốt, bộ đệm vòng
    │   ├── debounce.c/.h
    │   └── timing_stats.c/.h       # p50/p95/max trên thiết bị
    ├── hal/                    # GPIO, LEDC (PWM motor/servo), I2C LCD, relay, time
    ├── comm/                   # wifi_manager, mqtt_link (esp-mqtt), msg_codec (cJSON), topics_gen.h
    ├── app/                    # control_task (10 ms), comm_task, ui_task, cmd_handler, config_store (NVS)
    └── test_host/              # runner Unity cho core_logic (chạy bằng gcc trên laptop)
```

## 3. Quy tắc thiết kế (CODING_STANDARDS mục 3)

| # | Quy tắc |
|---|---|
| 1 | `core_logic` không phụ thuộc ESP-IDF → unit test trên host (FWT-*) |
| 2 | `control_task` chu kỳ 10 ms, ưu tiên cao nhất, **không bao giờ chờ mạng** |
| 3 | ISR chỉ chụp timestamp + đẩy queue (S1/S2) |
| 4 | Ngõ ra an toàn (`MOTOR_EN`, `SAFETY_RELAY`) chỉ được ghi ở **một chỗ duy nhất** sau khi `safety_supervisor` cho phép |
| 5 | Không cấp phát động sau init; queue/buffer kích thước cố định |
| 6 | Mọi topic lấy từ `topics_gen.h` (sinh từ `contracts/mqtt/topics.toml`) |
| 7 | Thứ tự ưu tiên mỗi chu kỳ: `ESTOP > SAFE_STOP > FAULT > STOPPING > STARTING/RUNNING` |

## 4. Máy trạng thái

Xem [ARCHITECTURE.md](../../ARCHITECTURE.md) mục 4 (trạng thái, chuyển trạng thái, hành vi ngõ ra) và [SAFETY_CONCEPT.md](../../docs/SAFETY_CONCEPT.md) (chức năng an toàn SF-01..08, bảng mã lỗi, ma trận reset).

## 5. Việc sẽ làm ở Phase 1 (chờ PO duyệt)

| Task | Nội dung |
|---|---|
| P1-01 | Cài ESP-IDF + gcc host, build ví dụ, ghi phiên bản |
| P1-02 | Chốt pin map theo board thật + phát hành `hardware/WIRING_GUIDE.md` |
| P1-05 | `core_logic`: cell_sm, fault_manager, debounce + unit test host |
| P1-06 | `product_tracker` + unit test host (gồm case lệch theo dõi) |
| P1-07 | `heartbeat_monitor` + unit test host (timeout, seq không tăng) |
| P1-08 | HAL: motor, servo, GPIO, LCD, relay |
| P1-09 | `comm`: Wi-Fi + MQTT + codec + `topics_gen.h` |
| P1-10 | Tích hợp firmware + đo thời gian trên thiết bị |
