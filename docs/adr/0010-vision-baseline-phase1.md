# ADR-0010: Hướng tiếp cận Vision cho Phase 1

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Phase 1 cần phân loại GOOD/DEFECT **đo được** (FPS, độ trễ, accuracy, FP, FN) trên sản phẩm tự làm. Dữ liệu ban đầu bằng 0. GPU laptop 4 GB VRAM.

## Các phương án

| Phương án | Dữ liệu cần | Độ phức tạp | Ghi chú |
|---|---|---|---|
| A. Luật xử lý ảnh cổ điển (màu, ngưỡng, contour) | Rất ít | Thấp | Nhanh để chạy thông pipeline; kém bền với ánh sáng |
| B. Phát hiện vật thể (YOLO) toàn khung hình | Nhiều nhãn bbox | Cao | Không cần thiết vì vị trí đã biết nhờ S1 + ROI |
| C. **Bộ phân loại CNN nhỏ trên ROI** (ví dụ MobileNetV3/ResNet18 fine-tune), xuất ONNX, chạy ONNX Runtime | Vài trăm ảnh có nhãn | Trung bình | Phù hợp khi vị trí sản phẩm được kích bởi S1 |
| D. Anomaly detection (PatchCore/EfficientAd) | Chủ yếu ảnh GOOD | Trung bình–Cao | Tốt khi hiếm ảnh lỗi. **Phase 6 tùy chọn** |

## Quyết định

Phase 1 làm **theo hai bước**, cả hai sau cùng interface `InferenceEngine`:
1. **A** làm baseline để thông toàn chuỗi và đo độ trễ sớm.
2. **C** làm mô hình chính.

Camera: webcam USB qua OpenCV (DirectShow trên Windows). Huấn luyện PyTorch trên RTX 3050.

**Dependency dự kiến thêm ở Phase 1** (ghi lý do khi thêm):
- Runtime: `numpy`, `opencv-python`, `onnxruntime` (hoặc `onnxruntime-gpu` nếu đo thấy cần).
- Nhóm tùy chọn `train`: `torch`, `torchvision`.

## Hệ quả

- Cần buồng sáng đơn giản và dataset tự thu trên băng tải thật, **chia train/val/test theo phiên chụp** để tránh rò rỉ dữ liệu.
- Mọi hạn chế (dataset, ánh sáng, camera, mô hình, suy luận) phải được báo cáo trong TEST_REPORT, **không che giấu**.
