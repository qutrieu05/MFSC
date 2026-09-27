# ADR-0012: Công nghệ dashboard — hoãn quyết định tới Phase 4

- **Trạng thái:** PROPOSED (DEFERRED) · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Dashboard là yêu cầu bắt buộc (Phase 4, 6) nhưng PO không muốn project thành "web thuần túy". Chọn công nghệ quá sớm dễ tốn công mà chưa biết dữ liệu thật trông thế nào.

## Các phương án sẽ đánh giá ở đầu Phase 4

| Phương án | Ưu | Nhược |
|---|---|---|
| Grafana (+ SQLite datasource) | Mạnh cho số liệu time-series, ít code | Hiển thị trạng thái/sự kiện thời gian thực qua MQTT cần plugin; thêm dịch vụ |
| Node-RED Dashboard | Nối MQTT rất nhanh | Logic dễ phân tán vào flow, khó test |
| Web nhẹ tự viết (HTTP + WebSocket, JS thuần) | Kiểm soát hoàn toàn, nhẹ | Tốn công giao diện |
| Streamlit | Viết nhanh bằng Python | Mô hình chạy lại toàn trang, không hợp thời gian thực |

**Tiêu chí:** chạy offline trong LAN · cập nhật trạng thái ≤ 1 s · số dependency · công sức · kiểm thử được · không lấn át phần embedded/AI.

## Quyết định tạm thời

Phase 1–3 dùng **CLI monitor** (`msfc monitor`) và công cụ xem MQTT tùy chọn (ví dụ MQTT Explorer) để quan sát. Quyết định công nghệ dashboard ở đầu Phase 4 bằng một ADR mới.
