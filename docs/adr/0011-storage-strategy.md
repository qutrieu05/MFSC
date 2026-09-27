# ADR-0011: Chiến lược lưu trữ dữ liệu

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Phase 1 cần log sự kiện và kết quả để đo đạc. Phase 4 cần truy vấn OEE, downtime, sự kiện cho dashboard. Ràng buộc: tối thiểu dependency và dịch vụ phải cài thêm.

## Các phương án

| Phương án | Cài đặt | Truy vấn | Ghi chú |
|---|---|---|---|
| **JSONL append-only** | Không | Kém (phải đọc file) | Đủ cho Phase 1, dễ phân tích bằng script |
| **SQLite (`sqlite3` có sẵn)** | Không | Tốt (SQL, index) | Một file, sao lưu dễ; đủ tải của 1 cell |
| InfluxDB / TimescaleDB | Cần cài dịch vụ | Rất tốt cho time-series | Thừa cho S1; FUTURE nếu cần |

## Quyết định

- **Phase 1–3:** JSONL theo ngày trong `runtime/events/`.
- **Phase 4 trở đi:** SQLite qua interface `Repository` (IF-08). Dữ liệu JSONL của các phase trước có thể import lại.
- **Ảnh:** lưu trên đĩa trong `runtime/images/` theo chính sách giữ lại cấu hình được; DB chỉ lưu đường dẫn.

## Hệ quả

- Không cần cài dịch vụ cơ sở dữ liệu.
- Đổi sang InfluxDB/Timescale sau này chỉ cần thêm implementation `Repository` mới.
