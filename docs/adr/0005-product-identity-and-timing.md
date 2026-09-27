# ADR-0005: Danh tính sản phẩm và thời điểm gạt do ESP32 sở hữu

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Laptop suy luận qua Wi-Fi với độ trễ **không xác định**. Actuator phải gạt **đúng sản phẩm** trên băng tải đang chạy.

## Các phương án

| Phương án | Chi phí | Độ phức tạp | Độ tin cậy |
|---|---|---|---|
| A. Vision tự phát hiện sản phẩm, gửi lệnh "gạt ngay" | 0 | Thấp | Kém: độ trễ mạng làm gạt sai sản phẩm |
| B. **ESP32 phát hiện tại S1 → cấp `product_id` → FIFO → gắn verdict theo ID → S2 quyết định; không có verdict = gạt** | 1 cảm biến hồng ngoại thêm (~10–20k nếu chưa có) | Trung bình | Tốt: thời gian do ESP32 quyết; mạng chậm chỉ làm tăng số loại bỏ |
| C. B + encoder theo dõi vị trí chính xác | Encoder (~20–40k) | Cao hơn | Tốt nhất khi tốc độ thay đổi |
| D. Dừng băng tải tại trạm kiểm tra rồi chụp | 0 | Thấp | Cao nhưng kém thực tế, năng suất thấp |

## Quyết định

**Chọn B** cho Phase 1. **C** là nâng cấp tùy chọn (Phase 4/5). **D** là phương án dự phòng nếu đo thời gian ở Phase 1 không đạt (ghi quyết định nếu dùng).

## Hệ quả

- Sản phẩm không được vượt nhau trên băng tải; khoảng cách tối thiểu giữa sản phẩm và độ sâu FIFO cấu hình được.
- Độ trễ quan trọng `t_verdict_rx − t_detect` đo trên **cùng đồng hồ ESP32**, không cần đồng bộ giờ.
- Chính sách `reject_on_no_decision=true` là mặc định: lỗi AI/mạng không làm lọt sản phẩm lỗi.
