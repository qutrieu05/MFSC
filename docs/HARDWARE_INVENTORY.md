# Hardware Inventory

**Cập nhật:** 2026-09-18 · **Kết luận: HARDWARE AVAILABLE = NONE** (PO xác nhận)

---

## 1. Tuyên bố của PO (2026-09-18)

PO xác nhận **chưa có bất kỳ linh kiện nào** cho S1:

| Hạng mục | Có sẵn? |
|---|---|
| ESP32 | ❌ Không |
| Camera | ❌ Không |
| Motor | ❌ Không |
| Motor driver | ❌ Không |
| Servo | ❌ Không |
| Encoder | ❌ Không |
| Sensor | ❌ Không |
| E-stop | ❌ Không |
| Conveyor | ❌ Không |

**Hệ quả:** mọi tài liệu **không được giả định** có sẵn linh kiện nào (quyết định [D-019](../DECISIONS.md)). Toàn bộ phần cứng đều nằm trong [HARDWARE_MASTER_BOM.md](../HARDWARE_MASTER_BOM.md) và chỉ mua theo wave sau khi PO duyệt.

## 2. Tài nguyên PO thực sự đang có

| Hạng mục | Chi tiết (đã kiểm chứng bằng lệnh ngày 2026-09-17) | Dùng cho |
|---|---|---|
| Laptop | Windows 11 Pro build 26200 · Intel i5-12450H · 15,7 GB RAM · ổ D còn ≈ 29,7 GB | Edge Server, huấn luyện, mô phỏng, dashboard |
| GPU | **NVIDIA RTX 3050 Laptop, 4096 MiB VRAM**, driver 610.78 | Suy luận + huấn luyện mô hình nhỏ |
| Python | 3.11.9 · pip 24.0 · pytest 9.1.1 | Toàn bộ Edge Server |
| Git | 2.55.0 | Quản lý mã nguồn |
| Node.js | v24.19.0 | (không dùng trong S1) |
| Điện thoại (giả định có) | Có thể dùng làm webcam qua USB (DroidCam) — **0đ** | Thu ảnh dataset sớm ở P1.2–P1.3 |

**Chưa cài (miễn phí, cần trước Phase 1):** Mosquitto · ESP-IDF 5.x · MSYS2 MinGW-w64 gcc. Kiểm tra bằng `python tools/check_env.py`.

## 3. PO cần quyết định gì (thay cho việc "khai báo thiết bị có sẵn")

| # | Quyết định | Lựa chọn | Ảnh hưởng |
|---|---|---|---|
| 1 | **Động cơ** | TT motor (~30k, nhẹ, kém bền) **hay** JGA25-370 12 V (~150k, bền, momen tốt) | Độ ổn định băng tải (R-02) |
| 2 | **Cảm biến sản phẩm** | FC-51 (~15k/cái, nhạy ánh sáng) **hay** cặp cắt tia (~40k/cặp, ổn định) **hay** E18-D80NK (~80k/cái) | Độ chính xác `product_id` và timestamp |
| 3 | **Servo** | SG90 (~30k, bánh răng nhựa) **hay** MG90S (~55k, kim loại) | Độ bền khi gạt hàng nghìn lần |
| 4 | **Camera** | Webcam 720p (~200k) **hay** 1080p có lấy nét tay (~350k) | Chất lượng ảnh khi chụp gần 15–25 cm |
| 5 | **Khung băng tải** | Gỗ/MDF (~70k) **hay** nhôm định hình 2020 (~180k) | Độ cứng, rung, thời gian lắp |
| 6 | **Ngân sách tối đa** cho S1 | Ví dụ: 1,5 tr / 2,5 tr / 3,5 tr | Claude Inc chọn phương án phù hợp trong khoảng đó |

Chi tiết so sánh cost / performance / difficulty / reliability / expandability: [HARDWARE_MASTER_BOM.md](../HARDWARE_MASTER_BOM.md) mục 11.

## 4. Việc PO có thể làm ngay với 0đ (wave W0)

| # | Việc | Lợi ích |
|---|---|---|
| 1 | Gom **50–100 nắp chai nhựa cùng loại** (từ chai nước uống) | Sản phẩm mẫu cho dataset (D-024) |
| 2 | Giữ lại **1 thùng carton** + giấy nến/giấy trắng | Hộp che sáng cho camera |
| 3 | Cài **Mosquitto**, **ESP-IDF 5.x**, **MSYS2 gcc** (miễn phí) | Mở khóa P1.5 và P1.7 |
| 4 | Hỏi giá **cắt gỗ/mica theo kích thước** ở cửa hàng gần nhà | Chuẩn bị cho wave W3, tránh phải tự cắt |
| 5 | Mượn **đồng hồ vạn năng** nếu có thể | Tiết kiệm 80–200k; bắt buộc có trước khi cấp nguồn động cơ (R-26) |
| 6 | Thử dùng **điện thoại làm webcam** (DroidCam) và chụp thử vài ảnh nắp chai | Bắt đầu dataset thật trước khi mua camera |

## 5. Ghi chú

- Claude Inc **không thể kiểm chứng phần cứng vật lý**. Mọi trạng thái phần cứng chỉ được ghi là "đã kiểm chứng" khi có bằng chứng do PO cung cấp (ảnh, số đo, log).
- Danh sách phần cứng **không có gì được đặt hàng**. Mọi wave cần PO approve riêng.
