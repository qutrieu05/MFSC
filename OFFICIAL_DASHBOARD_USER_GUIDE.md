# Official Dashboard — User Guide

**Trạng thái:** SOFTWARE SIMULATION — không có phần cứng thật. Xem [OFFICIAL_DASHBOARD_ARCHITECTURE.md](OFFICIAL_DASHBOARD_ARCHITECTURE.md) cho kiến trúc chi tiết.

## 1. Yêu cầu

- Python 3.11+ (đã có sẵn trong môi trường phát triển).
- Dependency: `fastapi`, `uvicorn` (khai báo trong `edge/pyproject.toml`; đã cài sẵn trong môi trường phát triển này — nếu môi trường khác chưa có, chạy `pip install fastapi uvicorn`).
- **Không cần** ESP32, camera, cảm biến, MQTT broker, hay bất kỳ phần cứng nào.

## 2. Cách khởi động Dashboard

Từ thư mục gốc repo:

```bash
python edge/run_dashboard.py
```

Hoặc từ thư mục `edge/`:

```bash
cd edge
python -m msfc.dashboard
```

Mặc định chạy tại `http://127.0.0.1:8000`. Mở trình duyệt tới địa chỉ đó.

Tùy chọn cổng/host khác:

```bash
python edge/run_dashboard.py --host 0.0.0.0 --port 9000
```

**Dừng:** `Ctrl+C` trong terminal đang chạy server.

## 3. Cách chạy mô phỏng (Simulation)

Dashboard tự động tạo MỘT "demo cell" mô phỏng ngay khi server khởi động (một `SimCellController` thật + một `CellRuntime` thật, không có gì giả lập ở tầng hiển thị). Bạn không cần chạy lệnh gì thêm để "bật" mô phỏng — nó luôn ở chế độ mô phỏng vì chưa có phần cứng.

## 4. Cách chạy Full Demo

Nhấn nút **"▶ RUN FULL DEMO"** ở thanh điều khiển phía dưới màn hình. Hệ thống sẽ tự động chạy tuần tự 14 bước (khởi động → máy chạy → vài sản phẩm tốt/lỗi → cảnh báo sức khỏe máy → E-STOP → phục hồi → sản xuất lại → tổng kết), dùng đúng các control thật (không có phím tắt ẩn nào). Sau khi chạy xong, một cửa sổ tóm tắt hiện ra: số sản phẩm, OEE, tình trạng sức khỏe, sự kiện an toàn, lỗi đã xảy ra.

## 5. Ý nghĩa từng mục trên Dashboard

| Mục | Ý nghĩa |
|---|---|
| **Overview** | Tổng quan một trang: trạng thái hệ thống, sản xuất, OEE, sức khỏe máy, an toàn, pipeline sản phẩm mới nhất, sự kiện gần đây |
| **Production** | Bảng lịch sử từng sản phẩm: kết quả Vision/OCR/Decision/Controller, có bộ lọc |
| **Vision & OCR** | Sơ đồ pipeline chi tiết cho sản phẩm mới nhất — Vision, OCR, Decision, Safety Gate hiển thị **riêng biệt**, không gộp làm một |
| **Safety** | Mức độ an toàn hiện tại (SAFE/WARNING/FAULT/ESTOP/SAFE_STOP/UNKNOWN), trạng thái relay, pusher, hàng đợi, lỗi đang hoạt động |
| **Machine Health** | Tình trạng sức khỏe máy (mô phỏng phần mềm), điểm số, cảm biến mới nhất, bất thường đang hoạt động |
| **OEE** | Availability/Performance/Quality/OEE và chi tiết sản xuất — số liệu lấy trực tiếp từ backend, không tính lại ở giao diện |
| **Event Log** | Nhật ký sự kiện theo thời gian, lọc theo mức độ nghiêm trọng |
| **Diagnostics** | Trạng thái runtime, subsystem, mã lỗi, phiên bản contract |

## 6. Ý nghĩa các trạng thái hệ thống

| Trạng thái | Ý nghĩa |
|---|---|
| `SAFE` / `HEALTHY` | Bình thường |
| `WARNING` | Có dấu hiệu bất thường nhẹ, chưa nguy hiểm |
| `ANOMALY` / `FAULT` | Bất thường/lỗi cần chú ý |
| `CRITICAL` | Nghiêm trọng |
| `ESTOP` | Dừng khẩn cấp — chỉ vào lại `IDLE` khi RESET đúng quy trình |
| `SAFE_STOP` | Máy đã tự dừng an toàn |
| `UNKNOWN` | Chưa có dữ liệu — **không bao giờ** được hiển thị ngầm thành "bình thường" |
| `SIMULATION` | Nhắc lại: đây là phần mềm mô phỏng, không phải phần cứng thật |

## 7. Các nút điều khiển

| Nút | Hành động thật đằng sau |
|---|---|
| START / STOP / RESET | Gửi `ControlCommand` thật tới Cell Controller — giống hệt một nút bấm vận hành thật |
| SIMULATE GOOD / DEFECT / UNCERTAIN | Đặt điểm số camera mô phỏng cho sản phẩm tiếp theo, rồi chạy toàn bộ pipeline thật |
| SIMULATE OCR FAILURE | Làm kênh OCR tạm thời không khả dụng (lỗi thật, không phải đọc sai nội dung) cho một chu kỳ |
| SIMULATE HEALTH WARNING / CRITICAL / RECOVERY | Đẩy một giá trị cảm biến qua đúng cổng vào `CellRuntime.process_sensors()` |
| E-STOP | Gọi đúng hàm mô phỏng nút E-stop vật lý (`sim.press_estop()`) |
| RUN FULL DEMO | Chạy kịch bản 14 bước ở mục 4 |

Mọi nút đều đi qua đúng kiến trúc thật (an toàn/pipeline/quyết định) — không có "cửa sau" nào bỏ qua logic đã kiểm chứng ở Phase 1–6.

## 8. Xử lý sự cố (Troubleshooting)

| Vấn đề | Nguyên nhân/cách xử lý |
|---|---|
| Trang trắng / không load được CSS/JS | Kiểm tra server còn chạy; xem log terminal |
| "SYSTEM OFFLINE / DATA UNAVAILABLE" trên giao diện | Backend gặp lỗi nội bộ — xem log terminal server; đây là hành vi **đúng thiết kế** (không bao giờ hiển thị dữ liệu cũ như thể còn mới) |
| Nút bấm không phản hồi | Kiểm tra Console trình duyệt (F12) để xem lỗi JS/network |
| Cổng 8000 đã bị chiếm | Chạy với `--port` khác |
| Muốn xem API thô | Mở `http://127.0.0.1:8000/docs` (Swagger UI tự sinh) hoặc `/openapi.json` |

## 9. Giới hạn cần biết

- Đây là **một** phiên demo dùng chung cho mọi người xem cùng lúc (không có đăng nhập/nhiều phiên riêng).
- Không có phần cứng thật — mọi số liệu là kết quả mô phỏng/host, không phải đo đạc thật.
- Không claim độ chính xác AI/OCR/OEE/machine-health/predictive-maintenance thật — xem PHASE_DASHBOARD_COMPLETION_REPORT.md mục Validation Status.
