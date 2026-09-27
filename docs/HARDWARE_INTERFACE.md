# Hardware Interface Definition (P1.8)

**Phiên bản:** 1.0 · **Ngày:** 2026-09-18 · **Trạng thái:** đề xuất, chờ PO duyệt cùng wave mua W1

**Mục đích:** định nghĩa **hợp đồng giữa software và phần cứng** để:
1. Software (P1.1–P1.7) viết và test được **trước khi mua** bất cứ thứ gì.
2. Có thể **đổi linh kiện** (đổi cảm biến, đổi driver, đổi board) mà **không sửa logic lõi**.
3. Biết chính xác phải mua linh kiện có thông số gì (đầu vào cho [HARDWARE_MASTER_BOM.md](../HARDWARE_MASTER_BOM.md)).

> Tài liệu này mô tả **tín hiệu logic**, không phải chân GPIO cụ thể. Việc gán tín hiệu → chân là một **binding** riêng trong [hardware/PIN_MAPPING_DRAFT.md](../hardware/PIN_MAPPING_DRAFT.md); đổi board chỉ đổi binding.

---

## 1. Danh sách tín hiệu logic (Cell Controller N1)

| ID | Tín hiệu | Hướng | Loại | Mức tích cực | Yêu cầu thời gian | Hành vi khi lỗi/mất tín hiệu | Mô phỏng ở P1.6 |
|---|---|---|---|---|---|---|---|
| **IF-HW-01** | `ESTOP_SENSE` | In | Số, cách ly bằng tiếp điểm NC | **HIGH = dừng** (hở mạch hoặc đứt dây = HIGH) | Đọc mỗi chu kỳ ≤ 10 ms | Đứt dây → coi như nhấn (SAF-11) | Cờ boolean trong simulator, có kịch bản đứt dây |
| **IF-HW-02** | `RESET_BTN` | In | Số, nút thường (NO) | LOW khi nhấn | Chống dội 20–50 ms | Kẹt LOW → bỏ qua (không auto-reset liên tục) | Lệnh giả trong CLI |
| **IF-HW-03** | `START_BTN` | In | Số, nút thường (NO) | LOW khi nhấn | Chống dội 20–50 ms | Kẹt LOW → chỉ nhận cạnh, không nhận mức | Lệnh giả trong CLI |
| **IF-HW-04** | `SENSOR_S1` | In | Số từ cảm biến quang | Cấu hình được (active LOW/HIGH) | **Chụp timestamp trong ISR, chống dội 3–10 ms; đáp ứng cảm biến ≤ 5 ms** | Kẹt mức → phát hiện qua lệch theo dõi F030 | Sinh sự kiện theo mô hình sản phẩm đi trên đai |
| **IF-HW-05** | `SENSOR_S2` | In | Số từ cảm biến quang | Cấu hình được | Như S1 | Như S1 | Như S1, trễ đúng `t_travel` |
| **IF-HW-06** | `MOTOR_PWM` | Out | PWM | — | Tần số 15–25 kHz, độ phân giải ≥ 8 bit, cập nhật mỗi 10 ms | Về 0 khi không ở RUNNING | Giá trị số trong simulator |
| **IF-HW-07** | `MOTOR_DIR` (IN1/IN2) | Out | Số ×2 | — | Không đảo chiều khi PWM > 0 | Cả hai LOW = coast | Trạng thái trong simulator |
| **IF-HW-08** | `MOTOR_EN` | Out | Số | **HIGH = cho phép** | Tắt trong ≤ 1 chu kỳ khi có yêu cầu an toàn | **Có điện trở kéo xuống**: thả nổi = tắt (SAF-10) | Trạng thái |
| **IF-HW-09** | `SAFETY_RELAY` | Out | Số → relay tiếp điểm **NO** | **HIGH = đóng (cấp nguồn động cơ)** | Ngắt trong ≤ 1 chu kỳ; relay đáp ứng ≤ 20 ms | Thả nổi hoặc mất nguồn = **hở** = động cơ mất nguồn | Trạng thái + độ trễ relay mô phỏng |
| **IF-HW-10** | `SERVO_PWM` | Out | PWM servo | — | 50 Hz, xung 500–2500 µs; hành trình đẩy–thu **≤ 300 ms** | Về vị trí thu khi không ở RUNNING (SF-07) | Trạng thái pusher + thời gian hành trình |
| **IF-HW-11** | `LED_GREEN/YELLOW/RED` | Out | Số ×3 | HIGH = sáng | Cập nhật ≤ 100 ms | Không ảnh hưởng an toàn | In ra console trong simulator |
| **IF-HW-12** | `BUZZER` (tùy chọn) | Out | Số | HIGH = kêu | — | Không ảnh hưởng an toàn | Bỏ qua |
| **IF-HW-13** | `LCD_I2C` (tùy chọn) | Bi | I²C 100 kHz | — | Cập nhật ≤ 500 ms, **không chặn control task** | Lỗi I²C → ghi WARNING, hệ thống vẫn chạy | Bỏ qua |
| **IF-HW-14** | `ENCODER_A` (tùy chọn) | In | Số, xung | — | Đếm bằng PCNT, ≥ 200 xung/s | Không có xung khi PWM > 0 → nghi kẹt (Phase 5) | Sinh xung theo tốc độ mô phỏng |
| **IF-HW-15** | `HEALTH_I2C` (Phase 5) | Bi | I²C | — | Đọc ≤ 100 Hz | Lỗi đọc → F070 WARNING | Sinh tín hiệu tổng hợp |

## 2. Yêu cầu điện

| Hạng mục | Yêu cầu | Lý do |
|---|---|---|
| Mức logic | 3,3 V (ESP32). Mọi tín hiệu vào phải trong 0–3,3 V | Chân ESP32 **không** chịu 5 V |
| Ngõ vào từ cảm biến 5 V | Dùng cảm biến có ngõ ra 3,3 V tương thích, hoặc chia áp/level shifter | Tránh phá chân GPIO |
| Ngõ vào chỉ đọc (34–39) | **Cần điện trở kéo lên ngoài 10 kΩ** | Nhóm chân này không có pull-up nội |
| Ngõ ra an toàn (`MOTOR_EN`, `SAFETY_RELAY`) | **Điện trở kéo xuống 10 kΩ** tại chân; relay dùng tiếp điểm NO | Boot/treo/mất nguồn = động cơ tắt |
| Nguồn động cơ | 12 V DC riêng, qua **cầu chì 2 A → E-stop NC → relay NO → driver** | Kênh an toàn phần cứng (SF-01) |
| Nguồn servo | 5 V ≥ 2 A **riêng** (buck từ 12 V), tụ 470–1000 µF gần servo | Servo kéo dòng xung, gây reset ESP32 nếu dùng chung |
| Nguồn ESP32 | USB 5 V từ laptop (hoặc adapter 5 V riêng) | Tách khỏi nhiễu động cơ |
| Đất (GND) | Tất cả nối về **một điểm chung** (star ground) | Tránh vòng đất, số đo sai |
| Dòng tối đa qua breadboard | **Không cho dòng động cơ/servo đi qua breadboard** | Tiếp xúc breadboard không chịu dòng |

## 3. Thông số phần cứng tối thiểu suy ra từ yêu cầu

| Yêu cầu hệ thống | Suy ra thông số phần cứng | Item trong Master BOM |
|---|---|---|
| Sản phẩm đi từ S1 tới S2 ≥ 2,5 s (ngân sách thời gian) | Tốc độ đai 60–100 mm/s **và** khoảng S1→S2 ≥ 250 mm → động cơ **có hộp số**, 30–120 rpm | M1 |
| Gạt xong trong ≤ 300 ms | Servo ≥ 1,8 kg·cm, thời gian 60° ≤ 0,12 s | M3 |
| `product_id` có timestamp chính xác | Cảm biến đáp ứng ≤ 5 ms, ngõ ra số (không dùng cảm biến analog chậm) | S1, S2 |
| Ảnh không nhòe ở tốc độ đai | Thời gian phơi sáng ≤ 10 ms → cần **đèn đủ sáng** + khóa exposure | L1, C3 |
| Phân biệt được lỗi bằng thị giác | Camera ≥ 720p, lấy nét ở 15–25 cm, ROI sản phẩm ≥ 200×200 px | C3 |
| E-stop ngắt được nguồn động cơ | Tiếp điểm NC chịu ≥ 3 A DC ở 12 V | F1 |
| Relay cắt nguồn động cơ | Tiếp điểm ≥ 5 A, ngõ vào kích được từ 3,3 V | F2 |
| Bảo vệ ngắn mạch | Cầu chì 2 A (≈ 2× dòng làm việc dự kiến của động cơ) | F3 |
| Nguồn không sụt khi khởi động | Adapter 12 V ≥ 2 A + tụ 470–1000 µF | P1, P3 |

## 4. HAL API (hợp đồng giữa `core_logic` và `hal`)

`core_logic` **chỉ** gọi các hàm dưới đây; nó không biết gì về ESP-IDF, GPIO hay module cụ thể. Nhờ vậy `core_logic` test được trên laptop và đổi phần cứng không ảnh hưởng logic.

```c
/* Đọc đầu vào (được gọi 1 lần mỗi chu kỳ điều khiển) */
typedef struct {
    bool     estop_active;     /* IF-HW-01, đã xử lý fail-safe */
    bool     reset_pressed;    /* IF-HW-02, đã chống dội, theo cạnh */
    bool     start_pressed;    /* IF-HW-03 */
    bool     s1_edge;          /* IF-HW-04, có cạnh mới kể từ lần đọc trước */
    uint32_t s1_edge_mono_ms;  /* timestamp cạnh S1 (chụp trong ISR) */
    bool     s2_edge;          /* IF-HW-05 */
    uint32_t s2_edge_mono_ms;
    uint32_t now_mono_ms;      /* đồng hồ đơn điệu của thiết bị */
} hal_inputs_t;

esp_err_t hal_inputs_read(hal_inputs_t *out);

/* Ghi đầu ra (chỉ được gọi từ một chỗ duy nhất, sau khi safety cho phép) */
typedef struct {
    bool    motor_enable;      /* IF-HW-08 */
    bool    safety_relay_closed; /* IF-HW-09 */
    uint8_t motor_pwm_pct;     /* IF-HW-06, 0..100 */
    bool    motor_forward;     /* IF-HW-07 */
    bool    pusher_extend;     /* IF-HW-10 */
    bool    led_green, led_yellow, led_red, buzzer; /* IF-HW-11, 12 */
} hal_outputs_t;

esp_err_t hal_outputs_write(const hal_outputs_t *in);

/* Tùy chọn */
esp_err_t hal_lcd_show(const char *line1, const char *line2);   /* IF-HW-13 */
esp_err_t hal_encoder_read(uint32_t *pulses, uint32_t *mono_ms); /* IF-HW-14 */
esp_err_t hal_selftest(uint32_t *fault_mask);                    /* SELF_TEST */
```

**Quy tắc:**
- `hal_*` **không chứa logic quyết định**; chỉ đọc/ghi phần cứng.
- Mọi hàm trả mã lỗi; lỗi khởi tạo → `SELF_TEST_FAILED` (F050).
- `hal_outputs_write` phải **đảm bảo thứ tự an toàn**: khi tắt thì ngắt `motor_enable` và `safety_relay` trước, khi bật thì bật relay trước rồi mới tăng PWM.

## 5. Ba lớp hiện thực cùng interface

| Lớp hiện thực | Dùng ở đâu | Mục đích |
|---|---|---|
| `hal_esp32` | Phần cứng thật (P1.10+) | ESP-IDF: GPIO, LEDC, I²C, PCNT |
| `hal_host_mock` | Unit test `core_logic` trên laptop (P1.5) | Bơm đầu vào theo kịch bản, kiểm tra đầu ra; **đồng hồ ảo** để test timeout không cần chờ thật |
| `sim_cell` (Python, `msfc.sim`) | Simulator toàn cell nói MQTT (P1.6) | Cho Edge Server chạy end-to-end khi chưa có ESP32: sinh `product_detected`, nhận verdict, phát `product_sorted`, mô phỏng đủ hành vi fail-safe (mất heartbeat → SAFE_STOP) |

Nhờ ba lớp này, **P1.1–P1.8 hoàn thành được với 0đ phần cứng**, và khi hàng về chỉ cần thay `hal_host_mock` bằng `hal_esp32`.

## 6. Tham số hiệu chuẩn (đo sau khi có phần cứng, P1.11)

| Tham số config | Ý nghĩa | Cách đo |
|---|---|---|
| `conveyor.belt_speed_mm_s` | Tốc độ đai thực tế theo %PWM | Đánh dấu đai, đo thời gian đi 200 mm |
| `conveyor.distance_s1_s2_mm` | Khoảng cách hai cảm biến | Đo bằng thước |
| `conveyor.distance_s2_pusher_mm` | Khoảng cách S2 → tâm cần gạt | Đo bằng thước |
| `pusher.delay_ms` | Trễ từ S2 đến lúc đẩy | = distance/speed, hiệu chỉnh bằng thử 20 sản phẩm |
| `pusher.extend_ms` / `retract_ms` | Thời gian hành trình servo | Quan sát video/đo bằng log |
| `sensor.debounce_ms` | Chống dội cảm biến | Thử với 20 sản phẩm, xem có đếm đôi |
| `comm.heartbeat_timeout_ms` | Ngưỡng mất liên lạc | Đo phân bố khoảng heartbeat thật trong 30 phút |
| `vision.exposure_us`, `vision.roi` | Thông số camera | Chụp thử, chọn giá trị không nhòe |

## 7. Test nghiệm thu từng interface (khi hàng về)

| Interface | Test | Kết quả mong đợi |
|---|---|---|
| IF-HW-01 | Nhấn/nhả E-stop, rút dây | HIGH khi nhấn **và** khi rút dây |
| IF-HW-04/05 | Cho 20 sản phẩm đi qua | Đếm đúng 20, không đếm đôi |
| IF-HW-06/07/08 | Quét PWM 0→100% | Tốc độ tăng đều, đảo chiều đúng, `MOTOR_EN` LOW thì dừng |
| IF-HW-09 | Cắt `SAFETY_RELAY` khi đang chạy | Động cơ mất nguồn (đo bằng đồng hồ) |
| IF-HW-10 | Gạt 50 lần | Hành trình ≤ 300 ms, không kẹt, về vị trí thu đúng |
| Boot behavior | Cấp nguồn khi chưa nạp firmware / trong lúc boot | Động cơ **không** quay, relay **hở** |

Kết quả ghi vào [TEST_REPORT.md](../TEST_REPORT.md) mục Phase 1.
