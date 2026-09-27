# Pin Mapping — DRAFT v0.1 (ESP32 đời đầu, DevKit 30/36 chân)

> ⚠️ **DRAFT.** Chỉ chốt sau khi PO xác nhận **đúng model ESP32** ([HARDWARE_INVENTORY](../docs/HARDWARE_INVENTORY.md) mục 2.1). Nếu board là **ESP32-S3/C3**, bảng này phải làm lại.
> Đây **chưa** phải hướng dẫn đấu dây thi công. Hướng dẫn đấu dây từng bước + quy trình test sẽ được phát hành ở Phase 1 (task P1-02) **trước khi PO đấu dây**.

## 1. Nguyên tắc chọn chân

| Nguyên tắc | Lý do |
|---|---|
| Tránh GPIO **0, 2, 5, 12, 15** | Chân strapping (ảnh hưởng boot); có chân xuất tín hiệu lúc boot |
| Tránh GPIO **6–11** | Nối với flash nội |
| Tránh GPIO **1, 3** | UART0 (console/nạp code) |
| GPIO **34–39** là **input-only, không có pull-up nội** | Dùng cho nút/cảm biến **có điện trở kéo lên ngoài 10 kΩ** |
| Ngõ ra an toàn phải có **điện trở kéo xuống 10 kΩ** | Lúc boot chân ở trạng thái thả nổi → phải đảm bảo động cơ **tắt** (SAF-10) |

## 2. Bảng chân (đề xuất)

| Tín hiệu | GPIO | Hướng | Mức tích cực | Ghi chú |
|---|---|---|---|---|
| `ESTOP_SENSE` | 34 | In | **HIGH = dừng** | Tiếp điểm **NC** nối GPIO↔GND, pull-up ngoài 10 kΩ. Nhả nút = LOW; nhấn **hoặc đứt dây** = HIGH (SAF-11) |
| `RESET_BTN` | 35 | In | LOW khi nhấn | Nút thường (NO) + pull-up ngoài 10 kΩ; chống dội trong firmware |
| `START_BTN` | 39 | In | LOW khi nhấn | Như trên |
| `IR_S1` (cảm biến kiểm tra) | 32 | In | tùy module | Có pull-up nội; chụp timestamp trong ISR |
| `IR_S2` (trước cơ cấu gạt) | 33 | In | tùy module | Như trên |
| `MOTOR_PWM` | 25 | Out (LEDC) | – | Tần số PWM ~20 kHz (ngoài dải nghe) |
| `MOTOR_IN1` | 26 | Out | – | Chiều quay |
| `MOTOR_IN2` | 27 | Out | – | Chiều quay |
| `MOTOR_EN` (STBY driver) | 13 | Out | HIGH = cho phép | **Pull-down 10 kΩ** |
| `SAFETY_RELAY` | 23 | Out | HIGH = đóng (cấp nguồn động cơ) | **Pull-down 10 kΩ**; relay dùng tiếp điểm **NO** |
| `SERVO_PWM` | 18 | Out (LEDC) | – | 50 Hz; nguồn servo **riêng 5 V**, chung GND |
| `LED_GREEN` | 16 | Out | HIGH | + điện trở 330 Ω |
| `LED_YELLOW` | 17 | Out | HIGH | + điện trở 330 Ω |
| `LED_RED` | 19 | Out | HIGH | + điện trở 330 Ω |
| `BUZZER` | 14 | Out | HIGH | OPTIONAL. Lưu ý GPIO14 có thể xuất xung ngắn lúc boot → có thể kêu nhẹ |
| `LCD_SDA` | 21 | I²C | – | LCD1602 I²C (địa chỉ 0x27/0x3F) |
| `LCD_SCL` | 22 | I²C | – | |
| `ENCODER_A` | 36 | In | – | OPTIONAL (PCNT), pull-up ngoài nếu module không có |

**Chân còn trống để mở rộng:** 4 (cẩn thận: một số tài liệu xếp vào strapping), 15 (strapping), 2 (LED onboard). Cảm biến sức khỏe Phase 5 dự kiến dùng **ESP32 thứ hai** hoặc I²C dùng chung `21/22` (MPU6050 0x68).

## 3. Miền nguồn (rất quan trọng — rủi ro R-04)

```
Adapter 12 V ─[Cầu chì 2A]─[E-stop NC]─[Relay NO]──► Driver động cơ ──► Động cơ DC
                    │                       ▲
                    │                       └── điều khiển bởi SAFETY_RELAY (GPIO23)
                    └─► Buck 12V→5V ──► Servo (nguồn riêng, dòng ≥ 2 A)
USB 5 V từ laptop ──► ESP32 (chỉ cấp cho MCU và cảm biến logic)
TẤT CẢ GND nối chung tại một điểm (star ground)
```

**Không** cấp nguồn servo hoặc động cơ từ chân 5V/3V3 của ESP32.

## 4. Chuỗi an toàn (kênh cứng + kênh firmware)

| Lớp | Thành phần | Tác dụng khi lỗi |
|---|---|---|
| Cứng | Cầu chì | Ngắt khi quá dòng/ngắn mạch |
| Cứng | E-stop NC | Ngắt nguồn động cơ ngay, không qua firmware (SF-01) |
| Firmware | `SAFETY_RELAY` = LOW | Mất nguồn động cơ khi có yêu cầu an toàn hoặc khi ESP32 reset/mất điều khiển |
| Firmware | `MOTOR_EN` = LOW + PWM = 0 | Dừng điều khiển driver |
| Cơ khí | Che chắn con lăn | Ngăn kẹp tay (H1) — **bắt buộc trước khi chạy** |

## 5. Việc PO phải làm bằng tay (sẽ có checklist chi tiết ở Phase 1)

1. Xác nhận model board, in lại bảng chân nếu khác.
2. Lắp cơ khí băng tải + che chắn con lăn.
3. Đấu nguồn: cầu chì → E-stop → relay → driver (khi **đã ngắt điện**).
4. Đấu tín hiệu theo bảng mục 2, thêm điện trở pull-up/pull-down.
5. Đo trước khi cấp nguồn cho ESP32: kiểm tra không ngắn mạch, kiểm tra 5 V/12 V đúng cực.
6. Test từng phần theo quy trình Phase 1 (P1-02): nút E-stop → relay → động cơ không tải → servo → cảm biến.

## 6. Cảnh báo an toàn

- Luôn **ngắt nguồn** trước khi đấu/sửa dây.
- Không để tay gần cơ cấu gạt và con lăn khi có điện.
- Test E-stop **trước** khi chạy băng tải lần đầu; chạy ở tốc độ thấp nhất.
- Không nối bất kỳ thiết bị điện lưới 220 V nào vào hệ thống này (SAF-12).
