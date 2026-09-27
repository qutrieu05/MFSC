# Safety Concept — MSFC

**Phiên bản:** 0.1 (DRAFT — chờ PO duyệt) · **Ngày:** 2026-09-17

> ⚠️ **GIỚI HẠN BẮT BUỘC PHẢI ĐỌC**
> MSFC là **prototype học tập dùng điện áp thấp**. Các chức năng an toàn dưới đây được thiết kế theo nguyên tắc fail-safe nhưng **KHÔNG** được đánh giá hay chứng nhận theo ISO 13849, IEC 62061 hoặc bất kỳ tiêu chuẩn an toàn nào.
> - Giám sát vùng nguy hiểm bằng camera/AI là **lớp bổ sung**, không thay thế che chắn cơ khí hay nút dừng khẩn.
> - **Không** dùng thiết kế này cho máy móc thật có người vận hành.
> - Thao tác phần cứng phải do PO thực hiện khi **đã ngắt nguồn**, theo hướng dẫn an toàn của phòng lab.

---

## 1. Phân tích mối nguy (sơ bộ)

| ID | Mối nguy | Tình huống | Biện pháp chính (theo thứ tự ưu tiên) |
|---|---|---|---|
| H1 | Kẹp tay/cuốn vào con lăn băng tải | Tay chạm con lăn khi băng tải chạy | Che chắn cơ khí con lăn → tốc độ thấp → E-stop → giám sát vùng (P2) |
| H2 | Va đập từ cơ cấu gạt | Tay trong vùng gạt khi servo đẩy | Servo lực nhỏ, hành trình ngắn → không gạt ngoài `RUNNING` → pusher thu về khi an toàn |
| H3 | Chập điện, quá nhiệt dây dẫn | Đấu sai, ngắn mạch, dây nhỏ | Chỉ DC ≤ 12 V; cầu chì trên nguồn động cơ; dây đúng tiết diện; không dùng pin lithium trong S1 |
| H4 | Máy tự khởi động bất ngờ | Sau khi có điện lại, sau reset | Boot ở trạng thái an toàn; không tự chạy lại; START phải tường minh |
| H5 | Mất kiểm soát khi mất kết nối | Laptop treo, Wi-Fi mất, broker dừng | Heartbeat timeout → dừng + chốt lỗi |
| H6 | AI không phát hiện người | Che khuất, ánh sáng, mô hình kém | E-stop cứng là biện pháp chính; ghi rõ giới hạn; đo FN |
| H7 | Động cơ kẹt gây nóng | Kẹt băng tải, quá tải | Cầu chì; giám sát dòng/nhiệt (P5); dừng khi kẹt (FUTURE nếu cảm biến cho phép) |
| H8 | Xâm phạm quyền riêng tư | Camera quay người | Không lưu video thô mặc định; làm mờ mặt; giới hạn lưu giữ |

---

## 2. Chức năng an toàn (Safety Functions)

| ID | Kích hoạt | Phản ứng | Thời gian phản ứng (mục tiêu ban đầu) | **Không phụ thuộc vào** | Reset | Test |
|---|---|---|---|---|---|---|
| **SF-01** E-stop | Nhấn nút E-stop (NC) hoặc đứt dây | **Mạch cứng ngắt nguồn động cơ**; ESP32 → `ESTOP`, pusher thu, chốt | Tức thời (phần cứng) | Firmware, laptop, MQTT, AI | Nhả nút + **RESET tại chỗ** | ST-01..03 |
| **SF-02** Mất liên lạc | Không nhận heartbeat Edge Server trong `heartbeat_timeout_ms` (1000) | `FAULT(COMM_LOSS)`: tắt động cơ, ngắt relay, pusher thu, chốt | ≤ timeout + 50 ms tới lệnh dừng | Laptop, MQTT, AI (**chính là thứ được giám sát**) | Kết nối đã phục hồi + RESET (tại chỗ/từ xa) | ST-04..06 |
| **SF-03** Xâm nhập vùng (P2) | `zone_clear=false` | `SAFE_STOP(ZONE_INTRUSION)` | Phát hiện → lệnh dừng p95 ≤ 500 ms | Dashboard | Vùng trống liên tục ≥ `clear_hold_ms` + RESET | ST-07..09 |
| **SF-04** Giám sát safety vision (P2) | Heartbeat an toàn vắng > 600 ms, `frame_seq` không tăng, hoặc `detector_ok=false` | `SAFE_STOP(SAFETY_VISION_LOST)` | ≤ stale timeout + 50 ms | Chính kênh camera/AI | Kênh phục hồi + RESET | ST-10..12 |
| **SF-05** Boot an toàn / không tự chạy lại | Có điện, reset, sau khi reset lỗi | Động cơ tắt, pusher thu, tới `IDLE` chỉ sau self-test; cần START | – | Laptop | – | ST-13..14 |
| **SF-06** Watchdog / brownout | Task treo, sụt áp | Chip reset → SF-05; ghi lý do reset | Theo cấu hình watchdog | Laptop | Tự động về `IDLE` (không chạy) | ST-15 |
| **SF-07** Vị trí an toàn của actuator | Mọi trạng thái khác `RUNNING` | Pusher về vị trí thu; không nhận lệnh gạt | ≤ 1 chu kỳ điều khiển tới lệnh | Laptop | – | ST-16 |
| **SF-08** Chốt lỗi và reset có kiểm soát | Mọi lỗi mức SAFETY/FAULT | Giữ safe state tới khi reset hợp lệ | – | Dashboard | Theo ma trận mục 4 | ST-17 |

**Tín hiệu cho phép động cơ theo nguyên tắc fail-safe (SAF-10):**
- `MOTOR_EN` và `SAFETY_RELAY` hoạt động mức cao, có điện trở kéo xuống.
- Relay dùng tiếp điểm **thường hở (NO)** để cấp nguồn động cơ.
- **Mất điều khiển → không có nguồn cho động cơ.**

---

## 3. Kiến trúc kênh an toàn

```
                           ┌─────────────── Mạch cứng (không qua firmware) ───────────────┐
Nguồn DC động cơ ─[Cầu chì]─[E-stop NC]─[Relay NO do ESP32 điều khiển]─► Driver động cơ ─► Động cơ
                                  │ (tiếp điểm thứ 2 hoặc mạch đo sau nút)
                                  ▼
ESP32: ESTOP_SENSE ──► safety_supervisor ◄── heartbeat_monitor(edge01) ◄── MQTT
                             ▲              ◄── heartbeat_monitor(safecam01) ◄── MQTT (P2)
                             │
                        cell_sm (ưu tiên: ESTOP > SAFE_STOP > FAULT > sản xuất)
```

- **Kênh 1 (phần cứng):** E-stop ngắt trực tiếp nguồn động cơ. Kể cả khi firmware lỗi, động cơ vẫn mất nguồn.
- **Kênh 2 (firmware):** ESP32 cắt `MOTOR_EN` và relay khi có yêu cầu an toàn.
- **MQTT không phải kênh an toàn.** Thiết kế chỉ đảm bảo *mất* MQTT dẫn tới dừng; MQTT không bao giờ là điều kiện để máy tiếp tục chạy an toàn.

---

## 4. Ma trận reset

| Trạng thái chốt | Điều kiện để reset | Reset tại chỗ (nút RESET) | Reset từ xa (lệnh `reset`) |
|---|---|---|---|
| `ESTOP` | Nút E-stop đã nhả | ✅ | ❌ **Không cho phép** |
| `SAFE_STOP` | Vùng trống ≥ `clear_hold_ms` **và** kênh safety vision OK | ✅ | ✅ (khi đủ điều kiện) |
| `FAULT` | Nguyên nhân đã hết (ví dụ heartbeat phục hồi ≥ `recover_hold_ms`) | ✅ | ✅ (khi đủ điều kiện) |
| WARNING | – | Tự xóa khi hết nguyên nhân | – |

**Sau mọi reset:** trạng thái là `IDLE`, phải có lệnh START mới. Nút STOP trên dashboard **không phải** chức năng an toàn.

---

## 5. Bảng mã lỗi (v0.1)

| Mã | Tên | Mức | Trạng thái gây ra | Phase |
|---|---|---|---|---|
| F001 | `ESTOP_ACTIVE` | SAFETY | ESTOP | 1 |
| F010 | `COMM_LOSS_EDGE` | FAULT | FAULT | 1 |
| F011 | `MQTT_DISCONNECTED` | WARNING (IDLE) / FAULT (khi chạy, qua F010) | – | 1 |
| F020 | `ZONE_INTRUSION` | SAFETY | SAFE_STOP | 2 |
| F021 | `SAFETY_VISION_LOST` | SAFETY | SAFE_STOP | 2 |
| F030 | `TRACKING_MISMATCH` | FAULT (mặc định) / WARNING (cấu hình) | FAULT | 1 |
| F031 | `TRACKING_QUEUE_OVERFLOW` | FAULT | FAULT | 1 |
| F032 | `DECISION_LATE` | WARNING | – | 1 |
| F033 | `NO_DECISION_REJECT` | WARNING (đếm) | – | 1 |
| F040 | `ACTUATOR_FAULT` | FAULT | FAULT | FUTURE (cần phản hồi vị trí) |
| F041 | `MOTOR_STALL` | FAULT | FAULT | 5 (nếu có cảm biến dòng/encoder) |
| F050 | `SELF_TEST_FAILED` | FAULT | FAULT | 1 |
| F051 | `WATCHDOG_RESET` | WARNING (sau boot) | – | 1 |
| F052 | `BROWNOUT_RESET` | WARNING (sau boot) | – | 1 |
| F060 | `CONFIG_INVALID` | FAULT | FAULT | 1 |
| F070 | `HEALTH_SENSOR_INVALID` | WARNING | – | 5 |
| E1xx | Lỗi phía Edge Server (camera, mô hình, OCR, broker) | theo service | ảnh hưởng gián tiếp qua F010/F033 | 1+ |

Troubleshooting cho từng mã sẽ được viết dần trong `docs/TROUBLESHOOTING.md` (Phase 1 trở đi).

---

## 6. Nguyên tắc đấu dây an toàn (chi tiết ở Phase 1)

1. **Luôn ngắt nguồn** trước khi đấu/sửa dây. Kiểm tra lại bằng đồng hồ đo.
2. **Tách nguồn:** ESP32 (USB 5 V), servo (5 V riêng, dòng ≥ 2 A), động cơ (6–12 V riêng) — **nối chung GND**.
3. **Không cấp nguồn servo/động cơ từ chân 3V3/5V của ESP32.**
4. Có cầu chì trên đường nguồn động cơ; E-stop nối tiếp **trước** relay và driver.
5. Relay/driver enable mặc định **tắt**, có điện trở kéo xuống.
6. Diode dập cho cuộn relay (nếu module chưa có); tụ lọc gần driver động cơ.
7. **Che chắn con lăn** trước khi chạy băng tải lần đầu; chạy thử ở tốc độ thấp nhất.
8. Không để tay trong vùng gạt khi test pusher.

## 7. Kiểm chứng

Các test ST-01..ST-17 được định nghĩa trong [QA_PLAN.md](QA_PLAN.md) và kết quả ghi vào [TEST_REPORT.md](../TEST_REPORT.md). **Chức năng an toàn chưa có kết quả test trên phần cứng thật thì chưa được coi là hoạt động.**
