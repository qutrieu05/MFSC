# ADR-0006: Framework firmware ESP32 và cách test firmware

- **Trạng thái:** PROPOSED — **cần PO xác nhận** trước Phase 1 · **Ngày:** 2026-09-17

## Bối cảnh

PO muốn đào sâu Embedded Firmware. Firmware cần: FreeRTOS nhiều task, PWM (LEDC), ngắt GPIO có timestamp, watchdog, NVS, MQTT client, và **logic lõi test được không cần phần cứng**.

Audit ngày 2026-09-17: máy **chưa có** ESP-IDF, PlatformIO, gcc hay cmake.

## Các phương án

| Phương án | Chi phí | Độ phức tạp / học | Độ tin cậy / chiều sâu | Test trên host |
|---|---|---|---|---|
| **A. ESP-IDF 5.x chính thức** (VS Code extension hoặc `idf.py`) | Miễn phí | Cao | Cao; đầy đủ esp-mqtt, LEDC, watchdog, NVS; đúng hướng Embedded | Logic lõi C thuần + Unity, biên dịch bằng gcc trên host |
| B. Arduino-ESP32 (Arduino IDE) | Miễn phí | Thấp | Trung bình; che giấu nhiều chi tiết RTOS; test kém | Khó |
| C. PlatformIO (Arduino hoặc ESP-IDF framework) | Miễn phí | Trung bình | Cao; có môi trường `native` để test | Dễ; nhưng phiên bản ESP-IDF qua PlatformIO có thể trễ so với bản chính thức |
| D. MicroPython | Miễn phí | Thấp | Thấp cho thời gian thực | – |

## Quyết định đề xuất

**Chọn A.**
- `components/core_logic` viết **C99 thuần, không include ESP-IDF**, unit test trên laptop bằng **Unity** (ThrowTheSwitch).
- Trình biên dịch host: **MinGW-w64 gcc qua MSYS2** (miễn phí).
- Nếu PO muốn học nhanh hơn, **C** là phương án thay thế chấp nhận được. Cấu trúc module giữ nguyên, chỉ đổi build system.

## Hệ quả

- Việc cần làm ở đầu Phase 1: PO cài ESP-IDF 5.x và MSYS2 gcc (vài GB, miễn phí). Claude Inc cung cấp hướng dẫn và kiểm tra bằng lệnh `idf.py --version`, `gcc --version`.
- Đường cong học tập cao hơn Arduino, đổi lại đúng mục tiêu đào sâu Embedded.
- CI trên máy PO: `pytest` (edge) + `ctest`/script Unity (core_logic firmware).
