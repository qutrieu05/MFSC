# ai/models/

Mô hình đã huấn luyện + model card.

## Quy tắc

- **Trọng số KHÔNG commit** (`*.pt`, `*.onnx`, `*.engine` đã gitignore).
- Mỗi mô hình một thư mục `ai/models/<name>/<version>/` gồm:
  - `model_card.md`: mục đích, dataset dùng, cách huấn luyện, chỉ số đánh giá (accuracy/precision/recall/FP/FN), **giới hạn đã biết**, ngày, người tạo
  - `metrics.json`: số liệu đánh giá do script sinh ra
  - `config.toml`: tiền xử lý, kích thước đầu vào, ngưỡng độ tin cậy
  - `checksum.txt`: SHA-256 của file trọng số
- Registry mô hình và cơ chế cập nhật/rollback: Phase 6 (FR-AIP-01, FR-AIP-02).
- Mô hình chỉ được dùng trong sản xuất sau khi có báo cáo đánh giá trong TEST_REPORT.
