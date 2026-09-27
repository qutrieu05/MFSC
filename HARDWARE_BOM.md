# Hardware BOM — MSFC (bản tóm tắt theo phase)

**Cập nhật:** 2026-09-18 · **Baseline phần cứng: NONE** (PO xác nhận chưa có bất kỳ linh kiện nào)
**Trạng thái:** ⏳ **CHƯA MUA GÌ — mọi wave cần PO approve**

> 📋 **BOM chi tiết đầy đủ (60 hạng mục, 12 trường mỗi hạng mục, so sánh phương án, kiểm tra khi hàng về):**
> **[HARDWARE_MASTER_BOM.md](HARDWARE_MASTER_BOM.md)**
>
> File này chỉ là bản tóm tắt theo phase và theo chi phí. Nếu hai file lệch nhau, **Master BOM là bản chuẩn**.

## Ba mức chi phí

| Mức | Nội dung | Chi phí ước tính | Chi phí thực tế khuyến nghị |
|---|---|---|---|
| **MVP COST** | Đủ để chạy Phase 1 end-to-end (1 sản phẩm, 1 loại lỗi, tốc độ thấp) | 1,1 – 3,0 triệu | **≈ 1,6 – 1,9 triệu** |
| **S1 COST** | MVP + Phase 2 (camera an toàn) + Phase 3 (nhãn OCR) + Phase 5 (cảm biến sức khỏe) | 1,4 – 3,6 triệu | **≈ 2,1 – 2,5 triệu** |
| **OPTIONAL UPGRADE** | Encoder, ESP32 thứ hai, cảm biến dòng, LCD, perfboard, router, cảm biến tốt hơn | 0,3 – 1,9 triệu | tùy nhu cầu |
| Dụng cụ (nếu chưa có) | Đồng hồ vạn năng (bắt buộc), kìm/tua vít, mỏ hàn | 0,24 – 0,6 triệu | ≈ 0,3 triệu |

## Thứ tự mua (wave) — không mua tất cả cùng lúc

| Wave | Điều kiện để mua | Nội dung | Chi phí |
|---|---|---|---|
| **W0** | Ngay, 0đ | Gom nắp chai/hộp giấy làm sản phẩm mẫu, thùng carton làm hộp che sáng, mượn dụng cụ | **0** |
| **W1** | Sau khi P1.5 + P1.7 + P1.8 hoàn thành (firmware architecture + contract + hardware interface) | ESP32, camera USB, servo, 2 cảm biến, nút, LED, nguồn 12 V + buck + tụ, dây/breadboard, **đồng hồ vạn năng** | 0,65 – 1,35 tr |
| **W2** | Trước khi chạy động cơ | **E-stop NC**, relay, cầu chì, che chắn, động cơ có hộp số, driver, khớp nối, dây nguồn | 0,3 – 0,7 tr |
| **W3** | Sau khi W1 + W2 chạy ổn trên bàn | Cơ khí băng tải, chiếu sáng, giá camera, vật tư dataset | 0,3 – 1,1 tr |
| **W4** | Đầu Phase 2 | Camera thứ hai, buzzer | 0,26 – 0,42 tr |
| **W5** | Đầu Phase 3 | Nhãn decal in hạn sử dụng | 0,015 – 0,05 tr |
| **W6** | Đầu Phase 5 | Gia tốc kế, cảm biến nhiệt độ (tùy chọn: cảm biến dòng, ESP32 thứ hai) | 0,05 – 0,35 tr |

**Lý do:** W1 kiểm chứng phần rủi ro kỹ thuật cao nhất (firmware an toàn, độ trễ MQTT thật, camera thật) với chi phí thấp nhất, **trước khi** bỏ tiền vào cơ khí. Nếu không đạt, PO chỉ mất khoảng 1 triệu.

## Phase nào cần gì

| Phase | Cần mua mới |
|---|---|
| **P1.1 – P1.8** (software + design + mock) | **KHÔNG CẦN GÌ** — chỉ laptop |
| P1.9 procurement | W1 → W2 → W3 |
| P1.10 – P1.12 tích hợp và test | Toàn bộ MVP kit |
| Phase 2 | Camera thứ hai, buzzer |
| Phase 3 | Nhãn decal |
| Phase 4 | (encoder — tùy chọn) |
| Phase 5 | Gia tốc kế, nhiệt độ (+ tùy chọn) |
| Phase 6, 7 | — |

## Nguyên tắc giữ nguyên

1. Không giả định PO có sẵn bất cứ thứ gì.
2. Không mua PLC công nghiệp, camera công nghiệp, Jetson mới hay board AI đắt tiền cho S1.
3. Ưu tiên: giá thấp · dễ mua ở VN · dễ sửa · dễ lập trình · có tài liệu · mở rộng được.
4. Chỉ mua khi **interface đã chốt** ([docs/HARDWARE_INTERFACE.md](docs/HARDWARE_INTERFACE.md)) và phần software tương ứng đã chạy bằng mock.
5. **E-stop NC đã được APPROVED về mặt thiết kế** nhưng chỉ mua ở wave W2, sau khi PO duyệt.

## Phần mềm cần cài (tất cả miễn phí)

| Phần mềm | Mục đích | Cần từ |
|---|---|---|
| Mosquitto (Windows) | MQTT broker local | P1.7 (test contract runtime) |
| Python packages: `paho-mqtt`, `jsonschema`, `numpy`, `opencv-python`, `onnxruntime` | Edge Server | P1.2–P1.4 |
| PyTorch (nhóm `train`) | Huấn luyện mô hình trên RTX 3050 | P1.3 |
| ESP-IDF 5.x | Build/nạp firmware | P1.5 (biên dịch), P1.10 (nạp thật) |
| MSYS2 + MinGW-w64 gcc | Unit test firmware trên host | P1.5 |
| MQTT Explorer | Xem MQTT khi debug | tùy chọn |
