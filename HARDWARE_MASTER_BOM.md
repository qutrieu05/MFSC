# HARDWARE MASTER BOM — MSFC (S1)

**Phiên bản:** 1.0 · **Ngày:** 2026-09-18 · **Trạng thái:** ⏳ **CHƯA MUA GÌ — chờ PO approve**
**Baseline phần cứng:** **NONE** (PO xác nhận 2026-09-18 chưa có bất kỳ linh kiện nào)

> **Nguyên tắc BOM này tuân theo (theo chỉ thị của PO):**
> 1. Không giả định PO có sẵn bất cứ thứ gì.
> 2. Mỗi item nêu rõ **chức năng cần thiết** trước, rồi mới tới linh kiện.
> 3. Luôn có **phương án giá thấp**; khi có nhiều lựa chọn thì so sánh cost / performance / difficulty / reliability / expandability.
> 4. Nhãn **REQUIRED / OPTIONAL / FUTURE**.
> 5. **Chỉ mua khi interface đã được định nghĩa** — xem [docs/HARDWARE_INTERFACE.md](docs/HARDWARE_INTERFACE.md).
> 6. Ưu tiên: giá thấp · dễ mua ở VN · dễ sửa · dễ lập trình · có tài liệu · mở rộng được.
> 7. **Không** mua PLC công nghiệp, camera công nghiệp, Jetson mới hay hardware AI đắt tiền cho S1.

**Giá là ước tính tham khảo tại VN (09/2026), ±30%, chưa kiểm tra từng shop.** Nơi mua phổ thông: Hshop, Nshop, Thegioiic, IC Đây Rồi, Điện Tử Nhật Tảo, Shopee/Lazada (linh kiện cơ khí), cửa hàng ốc vít/mica địa phương.

**Ký hiệu cột:**
- **Mô phỏng?** = ✅ có thể thay bằng software mock/simulator trong Phase 1.1–1.8 · ⚠️ mô phỏng được một phần · ❌ bắt buộc hardware thật.
- **Thay thế?** = có thể dùng thứ khác/tận dụng nếu không mua.

---

## 1. Compute và điều khiển

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| C1 | **ESP32 DevKit** (Cell Controller) | 1 | Chạy firmware L0–L2: an toàn, máy trạng thái, PWM động cơ, servo, đọc cảm biến, MQTT | ESP32-WROOM-32, 30/38 chân, USB-UART (CP2102 hoặc CH340), 4 MB flash | ESP32-WROOM-32 DevKit V1 38 chân (nhiều chân hơn, dễ cắm breadboard) | ESP32 DevKit hàng phổ thông ~110–140k | **120–160k** | **REQUIRED** | 1 | ✅ (P1.6 mock) | Không nên thay bằng STM32/Arduino: mất Wi-Fi + hệ sinh thái tài liệu | Rủi ro: mua đúng biến thể (tránh ESP32-S2/C3 vì pin map và tài liệu khác) |
| C2 | ESP32 DevKit thứ hai (Health Node N3) | 1 | Tách cảm biến sức khỏe khỏi bộ điều khiển an toàn | Như C1 | Như C1 | Dùng chung C1 nếu chưa mua | 120–160k | **OPTIONAL** | 5 | ✅ | Có: chạy chung trên C1 với chu kỳ đọc chậm | Rủi ro: gộp vào C1 làm tăng tải cho control task (chấp nhận được ở tần số thấp) |
| C3 | **Camera USB (vision kiểm tra)** | 1 | Chụp sản phẩm khi S1 kích; phục vụ AI phân loại | 720p, 30 fps, UVC (Windows tự nhận), lấy nét tay hoặc cố định nét gần | 1080p, ống kính lấy nét tay, khung hình ổn định | Webcam 720p phổ thông ~180–250k | **250–400k** | **REQUIRED** | 1 | ⚠️ (ảnh/video có sẵn thay được ở P1.2–P1.3) | Có: điện thoại Android làm webcam qua USB (DroidCam) = 0đ nhưng độ trễ khó kiểm soát | Rủi ro: webcam rẻ tự auto-exposure gây thay đổi độ sáng → khóa exposure trong code; nhòe khi băng tải nhanh → giữ tốc độ thấp |
| C4 | Camera USB thứ hai (safety zone) | 1 | Giám sát vùng nguy hiểm song song với camera kiểm tra | 720p, góc rộng | 1080p góc rộng | Webcam 720p ~180–250k | 250–400k | **REQUIRED @P2** | 2 | ⚠️ (video ghi sẵn) | Có: webcam laptop nếu đặt được laptop đúng góc = 0đ | Rủi ro: hai camera USB cùng lúc có thể vượt băng thông một hub → cắm 2 cổng USB khác nhau |
| C5 | Cáp USB nối dài 3 m (có repeater) | 1–2 | Đặt camera trên băng tải cách laptop | USB 2.0, có IC repeater | 3 m active | Cáp 1,5 m thường ~25k | 60–110k | OPTIONAL | 1 | ✅ | Có: đặt laptop gần băng tải | Rủi ro: cáp dài không repeater gây mất kết nối camera (FT-01) |
| C6 | Router/AP Wi-Fi 2,4 GHz riêng | 1 | Mạng LAN riêng cho MQTT, tránh Wi-Fi trường quá tải (rủi ro R-01) | 2,4 GHz, 1 LAN | Router cũ bất kỳ | **Windows Mobile Hotspot = 0đ** | 0–250k | OPTIONAL | 1 | ✅ | Có: Mobile Hotspot của laptop | Rủi ro: hotspot Windows đôi khi tự tắt → nếu mất heartbeat nhiều thì cân nhắc router |
| C7 | Laptop + RTX 3050 | 1 | Edge Server: vision, OCR, decision, MQTT broker, dashboard | — | — | **Đã có** | 0 | — | 1 | — | — | Không phải khoản mua |

## 2. Truyền động (motion)

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| M1 | **Động cơ DC có hộp số** (kéo băng tải) | 1 | Kéo đai ở tốc độ thấp, momen đủ, đảo chiều được | 6–12 V, có hộp số, 30–120 rpm tại trục ra, momen ≥ 1,5 kg·cm | **JGA25-370 12 V 30–60 rpm** (momen tốt, trục 4 mm, dễ gắn pulley) | **TT motor (hộp số nhựa vàng) 3–6 V ~25–35k** (đủ cho băng tải nhẹ < 200 g) | 30–200k | **REQUIRED** | 1 | ✅ (P1.6) | Có: động cơ máy in/đồ chơi cũ tháo ra = 0đ | Rủi ro: động cơ **không hộp số** quay quá nhanh, không kéo nổi đai → **bắt buộc có hộp số**; TT motor nhựa dễ trượt bánh răng nếu tải nặng |
| M2 | **Driver động cơ** | 1 | PWM tốc độ + đảo chiều + cách ly công suất khỏi ESP32 | Điều khiển 1 kênh DC ≥ 1 A, có chân enable | **TB6612FNG** (hiệu suất cao, sụt áp thấp, 1,2 A/kênh) | **L298N module ~30–40k** (rẻ, phổ biến, nhưng sụt ~2 V và nóng) | 35–60k | **REQUIRED** | 1 | ✅ | Có: module MOSFET 1 chiều (mất khả năng đảo chiều) | Rủi ro: L298N sụt áp làm động cơ 6 V yếu → nếu dùng L298N thì cấp 9–12 V |
| M3 | **Servo (cơ cấu gạt)** | 1 | Gạt sản phẩm lỗi ra khỏi băng tải trong < 300 ms | Servo 180°, momen ≥ 1,8 kg·cm, 4,8–6 V | **MG90S (bánh răng kim loại) ~50–60k** — bền hơn khi gạt liên tục | **SG90 ~25–30k** (bánh răng nhựa, đủ cho sản phẩm ≤ 50 g) | 25–120k | **REQUIRED** | 1 | ✅ | Có: solenoid đẩy hoặc cơ cấu cần gạt bằng động cơ DC nhỏ | Rủi ro: SG90 chết bánh răng sau vài nghìn lần gạt → dự phòng 1 cái; servo phải có **nguồn riêng** (xem P3) |
| M4 | Encoder đo tốc độ băng tải | 1 | Bù thời gian gạt khi tốc độ thay đổi; tính Performance cho OEE | Cảm biến quang khe (photo-interrupter) + đĩa khe, hoặc động cơ có encoder | Photo-interrupter + đĩa 20 khe in 3D/mica | Module encoder quang ~25–35k | 25–60k | **OPTIONAL** | 1 (nâng cấp) / 4 | ✅ | Có: tính thời gian theo tốc độ cố định (đủ cho MVP) | Rủi ro: thiếu encoder thì tốc độ đai thay đổi (trượt, tải) sẽ làm gạt lệch → giữ tốc độ thấp và cố định |
| M5 | Pulley/khớp nối trục động cơ ↔ con lăn | 1–2 | Truyền chuyển động từ động cơ sang con lăn | Khớp nối mềm 4–6 mm hoặc pulley + dây curoa nhỏ | Khớp nối nhôm 5×8 mm | Ống silicon + kẹp + keo ~10–20k | 20–60k | **REQUIRED** | 1 | ✅ | Có: nối trực tiếp bằng ống silicon | Rủi ro: lệch trục gây rung và trượt đai |

## 3. Cảm biến

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| S1 | **Cảm biến phát hiện sản phẩm (vị trí S1 – trạm kiểm tra)** | 1 | Kích chụp ảnh + cấp `product_id`; timestamp chính xác | Ngõ ra số, thời gian đáp ứng < 5 ms, phát hiện vật ≥ 20 mm | **Cặp thu-phát hồng ngoại cắt tia (break-beam)** — ít bị ảnh hưởng màu sản phẩm | **FC-51 IR obstacle ~12–18k** (rẻ nhất, nhưng nhạy với ánh sáng môi trường và màu vật) | 15–90k | **REQUIRED** | 1 | ✅ (P1.6 mock) | Có: công tắc lá (microswitch) ~10k, hoặc phát hiện bằng vision (mất độ chính xác thời gian) | Rủi ro: FC-51 báo sai với vật tối màu/ánh sáng mạnh → nếu tỷ lệ bỏ sót cao thì nâng cấp E18-D80NK (~70–90k) |
| S2 | **Cảm biến trước cơ cấu gạt (vị trí S2)** | 1 | Xác nhận sản phẩm tới điểm gạt, chốt thứ tự FIFO | Như S1 | Như S1 | Như S1 | 15–90k | **REQUIRED** | 1 | ✅ | Như S1 | Rủi ro: nếu S2 hỏng thì phát hiện qua lệch theo dõi (F030) |
| S3 | Gia tốc kế (rung động động cơ) | 1 | Đo rung để phân loại NORMAL/WARNING/CRITICAL | I2C/SPI, ≥ 2 g, ODR ≥ 400 Hz | **ADXL345** (ODR tới 3200 Hz, phù hợp phân tích rung) | **MPU6050 ~40–50k** (ODR thấp hơn nhưng đủ cho rung tần số thấp) | 40–90k | **REQUIRED @P5** | 5 | ✅ | Có: bắt đầu bằng nhiệt độ + dòng, thêm rung sau | Rủi ro: gắn không cứng → số đo vô nghĩa; MPU6050 không đủ băng thông cho lỗi ổ bi (ghi rõ giới hạn) |
| S4 | Cảm biến nhiệt độ vỏ động cơ | 1 | Phát hiện quá nhiệt (H7) | Đo tiếp xúc 0–100 °C, sai số ≤ 2 °C | **DS18B20 dạng đầu dò kim loại** (dễ kẹp vào vỏ động cơ) | NTC 10k + điện trở ~5–10k | 10–35k | **REQUIRED @P5** | 5 | ✅ | Có: NTC rẻ hơn nhưng phải hiệu chuẩn | Rủi ro: đo sai vị trí (không tiếp xúc vỏ) → số vô dụng |
| S5 | Cảm biến dòng động cơ | 1 | Phát hiện kẹt/quá tải, tính năng lượng | Đo DC 0–3 A | **INA219 (I2C, đo cả V và I, độ phân giải tốt)** | ACS712-5A ~30–40k (analog, nhiễu hơn) | 30–60k | **OPTIONAL @P5** | 5 | ✅ | Có: suy ra tải qua PWM + tốc độ (kém chính xác) | Rủi ro: ACS712 nhiễu ở dòng nhỏ (< 300 mA) → chọn INA219 nếu động cơ nhỏ |

## 4. An toàn (safety-critical — thiết kế hardware-first)

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| F1 | **Nút E-stop NC (mushroom, latching)** | 1 | SF-01: ngắt trực tiếp nguồn động cơ bằng phần cứng; ESP32 đọc trạng thái | Loại nhấn giữ (latching), **≥ 1 tiếp điểm NC**, dòng ≥ 3 A DC | **Loại 22 mm có 2 tiếp điểm NC** (1 cho nguồn, 1 cho ESP32 đọc) ~60–90k | Loại 1 NC ~35–50k + đọc điện áp sau nút qua cầu phân áp | **40–90k** | **REQUIRED** (đã APPROVED về thiết kế, mua sau khi chốt BOM) | 1 | ❌ **Không mô phỏng được cho test an toàn thật (ST-01..03)** | Không: nút thường (không latching) **không đạt** yêu cầu E-stop | Rủi ro: mua loại chỉ có NO → **sai hoàn toàn nguyên tắc fail-safe**; phải kiểm tra bằng đồng hồ trước khi lắp |
| F2 | **Relay module 1 kênh 5 V** (cắt nguồn động cơ theo firmware) | 1 | SAF-10: mất điều khiển = động cơ mất nguồn | Tiếp điểm NO ≥ 5 A, có opto cách ly, ngõ vào 3,3 V tương thích | Module relay 1ch 5 V có opto + transistor, **chọn loại kích mức CAO** | Module relay 1ch ~15–20k (thường kích mức THẤP → cần đảo logic + điện trở kéo) | 15–30k | **REQUIRED** | 1 | ✅ (mock trạng thái) | Có: MOSFET IRF520 module ~15k (cắt phía âm, không cách ly) | Rủi ro: module kích mức thấp sẽ **đóng relay khi ESP32 đang boot** → phải chọn kích mức cao hoặc thêm mạch đảo + pull-down (kiểm tra bằng test ST-13) |
| F3 | **Cầu chì + đế** (2 A, 5×20 mm) | 5 | Bảo vệ ngắn mạch/quá dòng đường nguồn động cơ (H3) | Đế cầu chì gắn dây + cầu chì 2 A | Đế có nắp + 5 cầu chì dự phòng | Đế đơn + 2 cầu chì ~12–18k | 15–30k | **REQUIRED** | 1 | ❌ | Không: bỏ cầu chì là vi phạm nguyên tắc an toàn | Rủi ro: chọn cầu chì quá lớn (10 A) làm mất tác dụng bảo vệ |
| F4 | **Che chắn cơ khí con lăn/vùng gạt** (mica/nhựa + trụ) | 1 bộ | Biện pháp an toàn **chính** cho H1/H2 (che vùng kẹp tay) | Mica 2–3 mm, kích thước che hết con lăn và vùng gạt | Mica 3 mm cắt theo kích thước + trụ đồng | Bìa formex/nhựa cứng tái sử dụng ~20–40k | 40–90k | **REQUIRED** | 1 (trước khi chạy) | ❌ | Có: tấm nhựa/gỗ tự cắt | Rủi ro: chạy băng tải khi chưa che chắn → nguy cơ kẹp tay thật |
| F5 | Nút RESET + nút START (momentary) | 2 | Reset lỗi tại chỗ (SAF-05), khởi động có chủ ý (SAF-06) | Nút nhấn nhả 12 mm | Nút có đế + màu khác nhau (xanh START, vàng RESET) | Nút nhấn 6×6 mm ~2–3k/cái | 10–30k | **REQUIRED** | 1 | ✅ | Có: dùng nút trên breadboard | Rủi ro: nhầm nút → dán nhãn rõ |
| F6 | LED trạng thái (đỏ/vàng/xanh 5 mm) + điện trở 330 Ω | 3+3 | Hiển thị trạng thái tại chỗ khi không có laptop (FR-CNV-07) | LED 5 mm + điện trở | Module LED 3 màu hoặc tháp đèn mini | LED rời ~500đ/cái | 10–20k | **REQUIRED** | 1 | ✅ | Có: LED onboard của ESP32 (thông tin rất hạn chế) | Rủi ro thấp |
| F7 | Buzzer 5 V (active) | 1 | Cảnh báo âm khi vào trạng thái an toàn/lỗi | Buzzer active 5 V | Buzzer active có driver transistor | Buzzer thụ động ~5k | 7–15k | OPTIONAL | 1 | ✅ | Có: chỉ dùng LED | Rủi ro thấp |
| F8 | LCD 1602 + I2C backpack | 1 | Xem trạng thái/mã lỗi/IP tại chỗ không cần laptop | LCD1602 + PCF8574 | LCD2004 (4 dòng) hoặc OLED 0.96 inch | OLED SSD1306 0.96 inch ~35–45k | 40–70k | OPTIONAL | 1 | ✅ | Có: chỉ dùng LED + serial | Rủi ro thấp; giúp debug tại hiện trường rất nhiều |

## 5. Nguồn điện

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| P1 | **Adapter 12 V DC** | 1 | Cấp nguồn động cơ (tách khỏi USB của ESP32) | 12 V, ≥ 2 A, có bảo vệ ngắn mạch | 12 V 3 A (dư công suất, ít sụt áp) | Adapter 12 V 2 A ~55–75k; tái dùng adapter router/TV box cũ = 0đ | 0–110k | **REQUIRED** | 1 | ✅ | Có: adapter cũ ≥ 12 V 2 A | Rủi ro: adapter yếu gây sụt áp khi động cơ khởi động (R-04) |
| P2 | **Buck converter 12 V → 5 V** | 1 | Cấp nguồn servo riêng (servo kéo dòng xung lớn) | 5 V, ≥ 2 A liên tục | **Module buck 5 V 3 A (MP1584/XL4015)** có tụ lọc | LM2596 module ~20–28k | 20–45k | **REQUIRED** | 1 | ✅ | Có: adapter 5 V 2 A riêng ~50k | Rủi ro: cấp servo từ chân 5 V của ESP32 → **reset ESP32** (lỗi kinh điển) |
| P3 | Tụ lọc 470–1000 µF 25 V + 100 nF | 2+4 | Chống sụt áp và nhiễu khi động cơ/servo hoạt động (R-04) | Tụ hóa 470 µF 25 V | 1000 µF 25 V low-ESR | Tụ rời ~2–5k/cái | 10–20k | **REQUIRED** | 1 | ❌ | Không | Rủi ro: thiếu tụ → ESP32 reset ngẫu nhiên, rất khó debug |
| P4 | Jack DC + đầu nối vít (screw terminal) | 2 | Nối adapter vào mạch an toàn, tháo được | Jack 5,5×2,1 mm | Jack có domino | ~5–10k/cái | 10–25k | **REQUIRED** | 1 | ✅ | Có: cắt dây adapter (không khuyến khích) | Rủi ro: đấu ngược cực → thêm diode bảo vệ |
| P5 | Ổ cắm có công tắc | 1 | Ngắt toàn bộ nguồn nhanh khi thử nghiệm | Ổ cắm có công tắc | Ổ cắm có công tắc từng cổng | Ổ cắm thường + rút phích | 0–60k | OPTIONAL | 1 | ✅ | Có: rút phích | Rủi ro thấp; tiện khi test an toàn |

## 6. Cơ khí băng tải

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| K1 | **Khung băng tải** | 1 | Giữ con lăn song song, đủ cứng để không rung | Dài 500–700 mm, rộng 120–150 mm | Nhôm định hình 2020 (2 thanh 600 mm) + ke góc | **Gỗ thông/MDF 12 mm cắt sẵn ~50–90k** (cửa hàng gỗ cắt theo kích thước) | 50–220k | **REQUIRED** | 1 | ✅ (P1.6) | Có: tận dụng thùng gỗ/ván cũ = 0đ | Rủi ro: khung mềm → đai lệch, rung, vision nhòe (R-02) |
| K2 | **Con lăn** | 2 | Dẫn đai, một con lăn chủ động | Ø 30–40 mm, dài bằng bề rộng đai, tròn đều | Ống nhôm Ø 32 mm + bạc trục | **Ống nhựa PVC Ø 32 mm ~10–20k** (2 đoạn 150 mm) | 15–60k | **REQUIRED** | 1 | ✅ | Có: lõi giấy cuộn băng keo + trục (tạm) | Rủi ro: con lăn không tròn/không cân → đai trượt lệch liên tục |
| K3 | **Vòng bi 608ZZ** | 4 | Giảm ma sát trục con lăn | 608ZZ (8×22×7 mm) | 608ZZ có nắp | ~5–8k/cái | 20–35k | **REQUIRED** | 1 | ✅ | Có: bạc nhựa/ống đồng (ma sát cao hơn) | Rủi ro thấp |
| K4 | **Trục** | 2 | Trục quay cho con lăn | Thanh thép Ø 8 mm dài 200 mm hoặc ty ren M8 | Trục thép trắng Ø 8 mm | Ty ren M8 ~10–15k | 15–40k | **REQUIRED** | 1 | ✅ | Có: đinh dài/ống thép tận dụng | Rủi ro: ty ren làm con lăn rung nhẹ |
| K5 | **Dây đai băng tải** | 1 | Mặt chở sản phẩm, ma sát đủ để không trượt | Rộng 100–150 mm, dài ~1300–1600 mm (vòng kín), mặt nhẵn màu tối (tương phản với sản phẩm) | Đai PVC 2 mm liền mạch cắt theo yêu cầu | **Vải bạt/simili + may hoặc dán mí ~50–100k**; hoặc băng tải mini có sẵn | 60–250k | **REQUIRED** | 1 | ✅ | Có: giấy dán liền, dây cao su rộng | Rủi ro: mối dán bung khi chạy dài (R-02) → may + dán, kiểm tra sau 30 phút chạy |
| K6 | Cơ cấu căng đai | 1 | Điều chỉnh độ căng, chống trượt | Rãnh trượt + bu lông cho một con lăn | Ke trượt + ốc điều chỉnh | Khoan rãnh dài trên khung + bu lông M6 ~10–20k | 10–40k | **REQUIRED** | 1 | ✅ | Có: chèn nêm gỗ (tạm, dễ tuột) | Rủi ro: không có cơ cấu căng → đai trượt, không kéo được |
| K7 | Cần gạt + giá đỡ servo | 1 | Gạt sản phẩm; giữ servo chắc | Mica/nhựa 2–3 mm, cần dài 60–100 mm | Cần gạt mica + giá servo in 3D | Mica vụn/nhựa tấm + keo nến ~15–30k | 20–50k | **REQUIRED** | 1 | ✅ | Có: cắt từ vỏ nhựa cũ | Rủi ro: cần gạt mềm → gạt không dứt khoát |
| K8 | Máng hứng sản phẩm lỗi | 1 | Chứa sản phẩm bị gạt ra | Hộp/khay nghiêng | Máng mica nghiêng | Hộp giấy ~0–10k | 0–30k | OPTIONAL | 1 | ✅ | Có: hộp giấy | Rủi ro thấp |
| K9 | Ốc vít, ke góc, trụ đồng, dây rút | 1 bộ | Lắp ghép toàn bộ | Bộ ốc M3/M4 + ke L + dây rút | Bộ ốc hỗn hợp có hộp chia | Mua lẻ theo nhu cầu ~40–80k | 50–120k | **REQUIRED** | 1 | ✅ | Có: mua lẻ đúng số lượng | Rủi ro: thiếu ốc đúng cỡ làm chậm cả buổi lắp |

## 7. Chiếu sáng và quang học (vision)

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| L1 | **Đèn LED chiếu sáng** | 1 | Ánh sáng **ổn định, không nhấp nháy** cho camera (rủi ro R-06) | LED trắng 12 V DC (không dùng đèn AC nhấp nháy), ≥ 300 lm | LED dây 12 V 5 m loại 2835 + nguồn riêng, hoặc đèn LED bàn DC | **LED dây 12 V 1 m ~25–45k** | 25–90k | **REQUIRED** | 1 | ⚠️ (dataset cũ dùng được nhưng ảnh thật cần đèn) | Có: đèn bàn LED sẵn trong nhà = 0đ (phải là loại không nháy) | Rủi ro: đèn AC/huỳnh quang nhấp nháy theo 50 Hz → ảnh sọc, vision sai |
| L2 | Tấm tán sáng (diffuser) | 1 | Giảm bóng gắt và phản chiếu trên sản phẩm | Giấy can/giấy nến hoặc mica trắng sữa | Mica trắng sữa 2 mm | Giấy nến nhà bếp ~5–15k | 5–40k | **REQUIRED** | 1 | ⚠️ | Có: giấy A4 trắng | Rủi ro thấp |
| L3 | Hộp/khung che sáng | 1 | Giữ điều kiện sáng cố định, chặn sáng môi trường | Bìa carton/foam đủ che vùng chụp | Foam board 5 mm sơn đen trong | **Thùng carton cũ = 0đ** | 0–50k | **REQUIRED** | 1 | ⚠️ | Có: chụp vào ban đêm, tắt đèn phòng (kém ổn định) | Rủi ro: không che sáng → mô hình học theo ánh sáng thay vì theo lỗi (R-05) |
| L4 | Giá đỡ camera | 1 | Giữ camera cố định đúng khoảng cách/góc, **không xê dịch giữa các phiên chụp** | Kẹp/chân đế giữ chắc, điều chỉnh cao độ | Kẹp gooseneck hoặc tripod mini + kẹp | Thanh gỗ + ke + dây rút ~10–20k | 10–90k | **REQUIRED** | 1 | ⚠️ | Có: tự chế từ gỗ/ke | Rủi ro: camera xê dịch → dataset không nhất quán, ROI lệch (ảnh hưởng trực tiếp độ chính xác) |

## 8. Dây, đầu nối, lắp mạch

| ID | Linh kiện | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| W1 | Dây cắm Dupont (M-M, M-F, F-F) | 3 bộ | Nối thử nghiệm nhanh | 20 cm, 40 sợi/bộ | Bộ 3 loại 20 cm + 30 cm | ~12–18k/bộ | 35–60k | **REQUIRED** | 1 | ✅ | Có: cắt dây tự bấm | Rủi ro: dây Dupont lỏng gây lỗi chập chờn → sau khi chạy ổn thì hàn lại |
| W2 | Breadboard 830 lỗ | 1 | Lắp thử mạch điều khiển | 830 lỗ | 830 lỗ + nguồn phụ | ~25–35k | 25–45k | **REQUIRED** | 1 | ✅ | Có: hàn trực tiếp lên perfboard | Rủi ro: breadboard tiếp xúc kém với dòng động cơ → **tuyệt đối không cho dòng động cơ đi qua breadboard** |
| W3 | Perfboard (mạch lỗ) 7×9 cm | 2 | Hàn mạch ổn định cho bản chạy dài (thay breadboard) | Perfboard 2 mặt | Perfboard có đường mạch sẵn | ~8–12k/cái | 15–30k | OPTIONAL | 1 (sau khi mạch ổn) | ✅ | Có: giữ breadboard (kém tin cậy) | Rủi ro: breadboard là nguyên nhân hàng đầu của lỗi "chạy lúc được lúc không" |
| W4 | Dây điện đơn 22 AWG nhiều màu | 1 bộ | Đi dây tín hiệu gọn, bền | 22 AWG, 5 màu | Dây lõi cứng + lõi mềm | ~25–40k | 25–50k | **REQUIRED** | 1 | ✅ | Có: tận dụng dây mạng cũ | Rủi ro thấp |
| W5 | Dây nguồn 18 AWG (đỏ/đen) | 2 m | Dẫn dòng động cơ | 18 AWG, ≥ 3 A | 16–18 AWG silicon | ~10–20k | 10–25k | **REQUIRED** | 1 | ✅ | Có: dây loa | Rủi ro: dây quá nhỏ gây nóng và sụt áp |
| W6 | Domino (terminal block) 2–3 chân | 5 | Nối tháo được các mối nguồn/an toàn | Domino 2 chân 5,08 mm | Domino có vít chắc | ~2–4k/cái | 10–25k | **REQUIRED** | 1 | ✅ | Có: nối xoắn + băng keo (không khuyến khích) | Rủi ro: mối nối xấu ở đường an toàn = nguy hiểm |
| W7 | Gen co nhiệt + băng keo điện | 1 bộ | Cách điện mối hàn | Gen co 2–6 mm | Bộ gen co nhiều cỡ | ~15–25k | 15–35k | **REQUIRED** | 1 | ✅ | Có: băng keo điện | Rủi ro thấp |
| W8 | Cáp micro-USB / USB-C cho ESP32 | 1 | Nạp code + nguồn cho ESP32 | Cáp data (không phải cáp chỉ sạc) | Cáp data ngắn 50 cm | ~15–25k (thường kèm board) | 0–25k | **REQUIRED** | 1 | ✅ | Có: cáp điện thoại cũ (phải là cáp data) | Rủi ro: cáp chỉ sạc → không nạp được code, mất thời gian debug oan |

## 9. Sản phẩm mẫu và vật tư dataset

| ID | Hạng mục | SL | Chức năng cần thiết | Min spec | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Phase | Mô phỏng? | Thay thế? | Lý do & rủi ro |
|---|---|:-:|---|---|---|---|---|---|:-:|:-:|---|---|
| D1 | **Sản phẩm mẫu đồng nhất** | 50–100 | Vật thể để phân loại GOOD/DEFECT; phải giống nhau để lỗi là biến duy nhất | 50+ cái giống nhau, kích thước 25–60 mm, đứng vững trên đai | **Nắp chai nhựa cùng loại** (dễ gom, phẳng, dễ tạo lỗi) hoặc hộp giấy nhỏ cùng cỡ | **Gom nắp chai miễn phí = 0đ**; hoặc mua 100 nắp chai/hộp giấy ~20–40k | 0–40k | **REQUIRED** | 1 | ⚠️ (ảnh tổng hợp dùng được ở P1.3 nhưng không thay được dataset thật) | Có: khối gỗ/nhựa tự cắt cùng kích thước | Rủi ro: sản phẩm không đồng nhất → mô hình học sai đặc trưng (R-05) |
| D2 | Vật tư tạo lỗi (bút lông, nhãn dán, giấy nhám) | 1 bộ | Tạo 2–3 loại lỗi **lặp lại được** (vết bẩn, thiếu nhãn, móp/xước) | Bút lông dầu + nhãn tròn + giấy nhám mịn | Thêm bút xóa để tạo lỗi sáng trên nền tối | ~15–35k | 15–40k | **REQUIRED** | 1 | ⚠️ | Có: dùng giấy dán tự cắt | Rủi ro: lỗi tạo tay không nhất quán → ghi quy trình tạo lỗi trong dataset spec |
| D3 | Nhãn in hạn sử dụng (giấy decal A4) | 1 tệp | Dataset OCR (Phase 3) | Giấy decal A4 in laser/phun | Decal A4 + in ở quán | In quán ~5–15k/tờ | 15–50k | **REQUIRED @P3** | 3 | ⚠️ | Có: viết tay (khó cho OCR, nhưng là case UNREADABLE hợp lệ) | Rủi ro: chữ quá nhỏ so với camera → định cỡ theo khoảng cách camera trước khi in |

## 10. Dụng cụ (không phải linh kiện nhưng bắt buộc để lắp)

| ID | Dụng cụ | Chức năng | Recommended | Phương án giá thấp | Giá ước tính | Nhãn | Ghi chú |
|---|---|---|---|---|---|---|---|
| T1 | **Đồng hồ vạn năng (multimeter)** | Kiểm tra điện áp, thông mạch, **kiểm chứng E-stop và cực nguồn trước khi cấp điện** | DT9205A hoặc tương đương | Đồng hồ cơ bản ~80–120k | 80–200k | **REQUIRED** | Không có đồng hồ thì **không được** đấu nguồn động cơ |
| T2 | Bộ mỏ hàn + chì + nhựa thông | Hàn perfboard, đầu nối, sửa dây | Mỏ hàn 60 W điều chỉnh nhiệt | Mỏ hàn 40 W ~60–90k + chì 20k | 100–250k | **REQUIRED** (từ khi hàn mạch) | Có thể lùi tới khi cần chuyển từ breadboard sang perfboard |
| T3 | Kìm cắt/tuốt dây, tua vít, kìm mũi nhọn | Lắp cơ khí và điện | Bộ dụng cụ mini | Mua lẻ ~60–100k | 60–150k | **REQUIRED** | Có thể mượn |
| T4 | Súng bắn keo nến | Cố định tạm cảm biến, giá đỡ | Súng keo nhỏ | ~40–60k | 40–80k | OPTIONAL | Rất tiện khi thử nghiệm vị trí cảm biến |
| T5 | Máy khoan/máy cắt | Khoan khung, cắt mica | — | **Mượn xưởng trường/quán cắt mica** = 0đ | 0 | OPTIONAL | Nên nhờ cắt sẵn theo kích thước |
| T6 | Thước kẹp (caliper) | Đo kích thước sản phẩm, khoảng cách camera | Thước kẹp nhựa | ~30–60k | 30–120k | OPTIONAL | Thước thẳng cũng đủ cho MVP |

---

## 11. So sánh phương án cho các lựa chọn quan trọng

**Thang đo:** ⭐ = thấp/kém · ⭐⭐⭐⭐⭐ = cao/tốt.

### 11.1 Động cơ kéo băng tải (M1)

| Phương án | Giá | Performance | Difficulty | Reliability | Expandability | Ghi chú |
|---|---|:-:|:-:|:-:|:-:|---|
| TT motor (hộp số nhựa 1:48) | 25–35k | ⭐⭐ (tốc độ ~200 rpm, momen nhỏ) | ⭐⭐⭐⭐⭐ (dễ nhất) | ⭐⭐ (bánh răng nhựa, trục lỏng) | ⭐⭐ | Đủ cho đai ngắn + sản phẩm ≤ 100 g |
| **JGA25-370 12 V 30–60 rpm** | 120–180k | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ (có bản kèm encoder) | **Lựa chọn đề xuất cho bản chạy dài** |
| JGB37-520 12 V có encoder | 230–300k | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (phải xử lý encoder) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Gộp luôn M4; chọn nếu PO muốn làm OEE performance rate chuẩn |
| Động cơ bước NEMA17 + driver | 200–350k | ⭐⭐⭐⭐ (tốc độ chính xác) | ⭐⭐ (phức tạp hơn) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Không cần cho băng tải liên tục; để FUTURE |

### 11.2 Cảm biến phát hiện sản phẩm (S1, S2)

| Phương án | Giá/cái | Performance | Difficulty | Reliability | Expandability | Ghi chú |
|---|---|:-:|:-:|:-:|:-:|---|
| FC-51 IR obstacle | 12–18k | ⭐⭐ (phụ thuộc màu và ánh sáng) | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | Rẻ nhất; đủ để chạy MVP trong hộp che sáng |
| **Cặp thu-phát cắt tia (break-beam)** | 30–50k/cặp | ⭐⭐⭐⭐ (không phụ thuộc màu sản phẩm) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **Đề xuất**: ổn định nhất trong nhóm giá thấp |
| E18-D80NK | 65–90k | ⭐⭐⭐⭐ (có biến trở điều chỉnh, vỏ kín) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Gần chuẩn công nghiệp; chọn nếu FC-51 báo sai nhiều |
| Microswitch (công tắc lá) | 8–15k | ⭐⭐ (có tiếp xúc cơ khí, chậm) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | Dự phòng nếu quang học gặp vấn đề |

### 11.3 Servo gạt sản phẩm (M3)

| Phương án | Giá | Performance | Difficulty | Reliability | Expandability | Ghi chú |
|---|---|:-:|:-:|:-:|:-:|---|
| SG90 (nhựa) | 25–30k | ⭐⭐⭐ (1,8 kg·cm, ~0,1 s/60°) | ⭐⭐⭐⭐⭐ | ⭐⭐ (mòn bánh răng) | ⭐⭐ | Chấp nhận được cho sản phẩm nhẹ; **mua dự phòng 1 cái** |
| **MG90S (kim loại)** | 50–60k | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | **Đề xuất**: chênh ~25k nhưng bền hơn nhiều |
| MG996R | 90–120k | ⭐⭐⭐⭐⭐ (10 kg·cm) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Chỉ cần nếu sản phẩm > 200 g; tốn nguồn hơn |
| Solenoid đẩy 12 V | 60–120k | ⭐⭐⭐⭐ (nhanh, dứt khoát) | ⭐⭐⭐ (cần driver + diode dập) | ⭐⭐⭐⭐ | ⭐⭐⭐ | Phương án thay thế nếu servo kém dứt khoát |

### 11.4 Camera kiểm tra (C3)

| Phương án | Giá | Performance | Difficulty | Reliability | Expandability | Ghi chú |
|---|---|:-:|:-:|:-:|:-:|---|
| Webcam 720p phổ thông | 180–250k | ⭐⭐⭐ (đủ cho lỗi nhìn thấy rõ) | ⭐⭐⭐⭐⭐ (UVC, Windows tự nhận) | ⭐⭐⭐ | ⭐⭐⭐ | Phương án giá thấp |
| **Webcam 1080p có lấy nét tay** | 300–450k | ⭐⭐⭐⭐ (nét gần tốt hơn, chi tiết hơn) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Đề xuất**: lấy nét tay rất quan trọng khi chụp gần 15–25 cm |
| Điện thoại Android làm webcam (DroidCam) | 0 | ⭐⭐⭐⭐ (camera tốt) | ⭐⭐⭐ (driver, độ trễ khó đo) | ⭐⭐ (app có thể ngắt) | ⭐⭐ | Dùng được ở P1.2/P1.3 để lấy ảnh dataset sớm mà chưa mua gì |
| Camera công nghiệp USB3/GigE | 2–8 triệu | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **Không mua** cho S1 (trái chỉ thị chi phí) |

---

## 12. MINIMUM HARDWARE KIT (MVP — chạy được Phase 1 end-to-end)

Mục tiêu: đạt AC-P1-01..11 với **một** loại sản phẩm, **một** loại lỗi, tốc độ đai thấp.

| Nhóm | Item | Ghi chú |
|---|---|---|
| Compute | C1 ESP32, C3 camera USB, (C7 laptop đã có) | |
| Motion | M1 động cơ có hộp số, M2 driver, M3 servo, M5 khớp nối | |
| Sensors | S1, S2 (2 cảm biến phát hiện sản phẩm) | |
| Safety | **F1 E-stop NC**, F2 relay, F3 cầu chì, F4 che chắn, F5 nút RESET/START, F6 LED | |
| Power | P1 adapter 12 V, P2 buck 5 V, P3 tụ lọc, P4 jack/terminal | |
| Mechanics | K1 khung, K2 con lăn, K3 vòng bi, K4 trục, K5 đai, K6 căng đai, K7 cần gạt, K9 ốc vít | |
| Vision | L1 đèn LED, L2 tán sáng, L3 hộp che sáng, L4 giá camera | |
| Wiring | W1 dupont, W2 breadboard, W4/W5 dây, W6 domino, W7 gen co, W8 cáp USB | |
| Dataset | D1 sản phẩm mẫu, D2 vật tư tạo lỗi | |
| Tools | **T1 đồng hồ vạn năng** (bắt buộc trước khi cấp nguồn), T3 kìm/tua vít | T2 mỏ hàn có thể lùi lại |

**MVP COST: ≈ 1,1 – 3,0 triệu** (thấp nhất nếu chọn toàn bộ phương án giá thấp và tận dụng gỗ/carton; cao nhất nếu chọn toàn bộ bản recommended)
**Ước tính thực tế (khuyến nghị):** ≈ **1,6 – 1,9 triệu**
**Dụng cụ nếu chưa có gì:** + **0,24 – 0,6 triệu**

## 13. FULL S1 HARDWARE KIT (hoàn thành Phase 1 → 7)

| Bổ sung so với MVP | Item | Chi phí thêm |
|---|---|---|
| Phase 2 (safety zone) | C4 camera thứ hai, F7 buzzer | 0,26 – 0,42 triệu |
| Phase 3 (OCR) | D3 nhãn decal + in | 0,015 – 0,05 triệu |
| Phase 5 (machine health) | S3 gia tốc kế, S4 nhiệt độ | 0,05 – 0,13 triệu |
| Phase 6 | — (không cần phần cứng mới) | 0 |

**S1 COST (chỉ REQUIRED): ≈ 1,4 – 3,6 triệu** · **Ước tính thực tế: ≈ 2,1 – 2,5 triệu**
**Tổng gồm dụng cụ: ≈ 1,7 – 4,2 triệu** · **Ước tính thực tế: ≈ 2,4 – 3,0 triệu**

## 14. OPTIONAL UPGRADE COST (không cần cho S1)

| Item | Lợi ích | Chi phí |
|---|---|---|
| M4 encoder (hoặc động cơ có encoder) | Bù thời gian gạt khi tốc độ thay đổi; Performance rate chuẩn hơn | 25–300k |
| C2 ESP32 thứ hai | Tách health node khỏi bộ điều khiển an toàn | 120–160k |
| S5 cảm biến dòng | Phát hiện kẹt động cơ, đo năng lượng | 30–60k |
| F8 LCD/OLED | Debug tại chỗ không cần laptop | 40–70k |
| W3 perfboard + T2 mỏ hàn | Chuyển từ breadboard sang mạch hàn (tăng độ tin cậy rõ rệt) | 115–280k |
| C5 cáp USB dài, C6 router riêng | Bố trí linh hoạt, mạng ổn định hơn | 60–360k |
| E18-D80NK thay FC-51 | Cảm biến ổn định hơn | +100–150k |
| ESP32-S3 + camera (AI trên chip) | Hướng Edge AI trên vi điều khiển (FUTURE, ngoài S1) | 400–600k |

**OPTIONAL UPGRADE COST: ≈ 0,3 – 1,9 triệu** (tùy chọn bao nhiêu hạng mục)

---

## 15. Thứ tự mua đề xuất (waves)

> Nguyên tắc: **chỉ mua khi interface đã chốt và phần software tương ứng đã chạy bằng mock.**

| Wave | Khi nào mua | Mua gì | Chi phí | Mở khóa việc gì |
|---|---|---|---|---|
| **W0** | **Ngay (0đ)** | Gom nắp chai/hộp giấy làm sản phẩm mẫu; thùng carton làm hộp che sáng; mượn đồng hồ vạn năng/kìm; hỏi giá cắt gỗ-mica | **0** | Bắt đầu dataset thật ở P1.2–P1.3 bằng điện thoại làm webcam |
| **W1** | Sau khi **P1.5 + P1.7 + P1.8** xong (firmware architecture + contract + hardware interface) | C1 ESP32, C3 camera, M3 servo, S1+S2 cảm biến, F5 nút, F6 LED, P1 adapter, P2 buck, P3 tụ, P4 jack, W1/W2/W4/W6/W7/W8 dây-breadboard, **T1 đồng hồ vạn năng** | **0,65 – 1,35 triệu** | Test firmware thật trên bàn (M1.2): máy trạng thái, heartbeat fail-safe, servo, đo độ trễ MQTT thật |
| **W2** | Trước khi chạy động cơ | **F1 E-stop**, F2 relay, F3 cầu chì, F4 che chắn, M1 động cơ, M2 driver, M5 khớp nối, W5 dây nguồn | **0,3 – 0,7 triệu** | Test an toàn ST-01..03, ST-13; chạy động cơ không tải |
| **W3** | Sau khi W1+W2 chạy ổn | K1–K9 cơ khí băng tải, L1–L4 chiếu sáng + giá camera, D1/D2 dataset | **0,3 – 1,1 triệu** | M1.3 cơ khí, M1.4 dataset thật, M1.5 tích hợp đầy đủ |
| **W4** | Đầu Phase 2 | C4 camera thứ hai, F7 buzzer | 0,26 – 0,42 triệu | Giám sát vùng nguy hiểm |
| **W5** | Đầu Phase 3 | D3 nhãn decal | 0,015 – 0,05 triệu | OCR |
| **W6** | Đầu Phase 5 | S3 gia tốc kế, S4 nhiệt độ, (S5, C2 nếu muốn) | 0,05 – 0,35 triệu | Machine health |

**Lý do chia wave:** W1 cho phép kiểm chứng **phần khó nhất về mặt kỹ thuật** (firmware an toàn + độ trễ MQTT thật + camera thật) với chi phí thấp nhất, trước khi bỏ tiền vào cơ khí. Nếu độ trễ hoặc cảm biến không đạt, PO chỉ mất ~1 triệu chứ không mất toàn bộ.

## 16. Mỗi linh kiện cần cho phase nào

| Phase | Linh kiện bắt buộc mới |
|---|---|
| **P1.1 – P1.8** (software/design/mock) | **KHÔNG CẦN GÌ** (chỉ laptop) |
| P1.9 (procurement) | W1 → W2 → W3 |
| P1.10 – P1.12 (tích hợp, hiệu chuẩn, test hệ thống) | Toàn bộ MVP kit |
| Phase 2 | C4, F7 |
| Phase 3 | D3 |
| Phase 4 | (M4 encoder — tùy chọn) |
| Phase 5 | S3, S4, (S5, C2 — tùy chọn) |
| Phase 6 | — |
| Phase 7 | — |

## 17. Cái gì mô phỏng được, cái gì bắt buộc phần cứng thật

| Mô phỏng được trên laptop (P1.1–P1.8) | Bắt buộc phần cứng thật |
|---|---|
| Contract MQTT + kiểm tra payload | **Kênh E-stop phần cứng** (ST-01..03) |
| Máy trạng thái cell + safety supervisor + chốt lỗi (unit test trên host) | **Hành vi relay lúc ESP32 boot** (ST-13) |
| Product tracker FIFO + gắn verdict + chính sách no-decision | Cầu chì, che chắn cơ khí |
| Heartbeat monitor + timeout (dùng đồng hồ ảo) | Độ ổn định cơ khí của đai, hiện tượng trượt (R-02) |
| Pipeline vision với ảnh/video có sẵn hoặc ảnh chụp bằng điện thoại | Nhòe chuyển động thật, ánh sáng thật, dataset thật (R-05, R-06) |
| Decision engine + mã lý do | **Độ trễ thật qua Wi-Fi** (PT-01) và sụt áp gây reset (R-04) |
| Simulator ESP32 (mock đầy đủ contract, kể cả hành vi fail-safe) | Lực và thời gian gạt thật của servo |
| Broker MQTT thật (Mosquitto là software miễn phí) | Độ tin cậy cảm biến với sản phẩm thật |
| Tính OEE trên dữ liệu tổng hợp | Ổn định chạy dài với rung/nhiệt (LT-01) |
| Phân tích sức khỏe trên dữ liệu công khai/tổng hợp | Kiểm chứng an toàn đầy đủ (ST-*), test lỗi phần cứng (FT-05, 09, 10, 11) |

## 18. Kiểm tra khi hàng về (incoming inspection)

Làm **trước khi** lắp vào hệ thống, ghi kết quả vào TEST_REPORT:

1. **E-stop (F1):** dùng đồng hồ đo thông mạch — khi chưa nhấn phải **thông** (NC); nhấn giữ phải **hở**. Nếu ngược lại thì mua sai loại.
2. **Relay (F2):** cấp 5 V, thử mức logic ngõ vào 3,3 V xem có kích được; xác định module kích mức cao hay thấp; kiểm tra khi ngõ vào **thả nổi** thì relay ở trạng thái nào (phải là **hở**).
3. **Adapter (P1):** đo điện áp không tải và ghi lại; kiểm tra cực tính jack.
4. **Buck (P2):** điều chỉnh và đo đúng 5,0–5,2 V **trước khi** cắm servo.
5. **Động cơ (M1):** cấp nguồn qua driver, đo dòng không tải; kiểm tra hộp số không kêu lạ.
6. **Servo (M3):** quét 0–90–180° bằng ESP32, xác định giới hạn hành trình thực tế.
7. **Cảm biến (S1/S2):** đo khoảng cách phát hiện với **đúng sản phẩm mẫu** và trong điều kiện ánh sáng của hộp che sáng.
8. **Camera (C3):** cắm vào laptop, kiểm tra Windows nhận UVC, thử khóa exposure, chụp thử ở khoảng cách 15–25 cm để xác nhận nét.
9. **Cáp USB (W8):** xác nhận nạp được code (là cáp data).

## 19. Ghi chú về độ chính xác của bảng này

- Giá là **ước tính tham khảo (09/2026, ±30%)**, **chưa kiểm tra tại shop cụ thể**. PO nên đối chiếu giá thật trước khi đặt hàng và cập nhật lại bảng.
- Tất cả thông số "min/recommended" dựa trên yêu cầu chức năng trong [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) và interface trong [docs/HARDWARE_INTERFACE.md](docs/HARDWARE_INTERFACE.md); **chưa được kiểm chứng bằng phần cứng thật**.
- Không có hạng mục nào trong bảng được đặt hàng. **Mọi wave cần PO approve riêng.**
