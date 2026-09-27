# ADR-0002: Phân bổ tính toán giữa laptop, ESP32, Raspberry Pi và Jetson Nano

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

PO có laptop RTX 3050 (4 GB VRAM, xác nhận bằng `nvidia-smi` ngày 2026-09-17), ESP32, Raspberry Pi, Jetson Nano. S1 cần vision + OCR + safety vision + server + dashboard, và yêu cầu **tối thiểu chi phí**.

## Các phương án cho suy luận thị giác/OCR

| Phương án | Chi phí | Độ phức tạp | Độ tin cậy / hiệu năng | Ghi chú |
|---|---|---|---|---|
| A. Laptop RTX 3050 | 0 | Thấp | Cao; đủ cho phân loại + OCR + phát hiện người song song | Laptop là điểm lỗi đơn cho **sản xuất** (không phải cho an toàn, nhờ ADR-0003) |
| B. Jetson Nano | 0 (đã có) | Cao | JetPack 4 đã hết hỗ trợ, Ubuntu 18.04/Python 3.6; 4 GB RAM dùng chung; OCR + phát hiện người cùng lúc khó | Hợp làm **node camera phụ** sau này |
| C. Raspberry Pi (CPU) | 0 | Trung bình | Chậm cho OCR/phát hiện người thời gian thực | Hợp chạy broker/dashboard |
| D. ESP32-S3 camera (AI trên chip) | Phải mua | Cao | Không đủ cho OCR và anomaly | Phase 6 tùy chọn |

## Quyết định

- **Laptop (N2):** vision, OCR, safety vision, decision engine, broker, service, lưu trữ, dashboard trong S1.
- **ESP32 (N1, N3):** an toàn tầng embedded, điều khiển thời gian thực, cảm biến.
- **Jetson Nano:** FUTURE / Phase 6 tùy chọn, làm node camera suy luận tại chỗ (N4) publish cùng schema `inspection_result.v1`.
- **Raspberry Pi:** không dùng trong S1; FUTURE, nếu cần tách broker/dashboard khỏi laptop.

## Hệ quả

- Không phải mua board AI.
- Laptop phải đặt chế độ nguồn không ngủ khi demo; mất laptop → Cell Controller dừng an toàn (SF-02), sản xuất gián đoạn.
- Kiến trúc giữ khả năng chuyển suy luận sang node khác mà không sửa Decision Engine.
