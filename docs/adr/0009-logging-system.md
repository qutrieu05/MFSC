# ADR-0009: Hệ thống logging

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Cần logging, chẩn đoán và troubleshooting.
- Log phải **đọc được bởi người** khi debug trực tiếp.
- Log phải **xử lý được bằng máy** để phân tích lỗi và đo thời gian.
- Phải gắn được `product_id`, `cmd_id`, `device_id` để truy vết.

## Các phương án

| Phương án | Dependency | Ghi chú |
|---|---|---|
| **`logging` chuẩn + formatter JSON tự viết** | Không | Đủ dùng, kiểm soát hoàn toàn |
| structlog / loguru | Có | Tiện nhưng thêm dependency không bắt buộc |

## Quyết định

**Thư viện chuẩn `logging`:**
- **Console:** định dạng dễ đọc.
- **File:** JSON lines (`logs/msfc.jsonl`), xoay vòng theo dung lượng.
- **Trường ngữ cảnh** qua `extra={"ctx": {...}}`: `product_id`, `cmd_id`, `device_id`, `fault_code`.
- **Mức log** theo logger cấu hình trong `[logging.levels]`.

**Firmware:** `ESP_LOG*` qua serial + bộ đệm vòng lỗi + publish `fault` khi có mạng.

## Hệ quả

- Không log mật khẩu/token (quy tắc trong CODING_STANDARDS).
- Chi tiết: [LOGGING.md](../LOGGING.md).
