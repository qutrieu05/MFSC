# ADR-0007: Edge Server bằng Python 3.11, phân package theo layer

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Yêu cầu:
- Không có file Python khổng lồ.
- Mỗi layer có interface rõ.
- Không thêm dependency khi không cần.

Máy đã có Python 3.11.9 và pytest 9.1.1.

## Các phương án

| Phương án | Độ phức tạp | Bảo trì | Ghi chú |
|---|---|---|---|
| A. Một script lớn | Thấp lúc đầu | Rất kém | Bị loại theo yêu cầu PO |
| B. Nhiều process/microservice | Cao | Trung bình | Quá nặng cho 1 người trong S1 |
| C. **Modular monolith**: một process, package theo layer, service có vòng đời chung, giao tiếp nội bộ qua interface | Trung bình | Tốt | Tách process sau này nếu cần, vì mọi giao tiếp liên node đã qua `MessageBus` |

## Quyết định

**Chọn C.**
- Mã nguồn tại `edge/src/msfc/` (src layout).
- Package và quy tắc phụ thuộc theo [ARCHITECTURE.md](../../ARCHITECTURE.md) mục 7, **được kiểm tra bằng test tự động** (`edge/tests/unit/test_layer_dependencies.py`).
- Dependency thêm theo phase, mỗi dependency ghi lý do trong DECISIONS.md.

## Hệ quả

- Phase 0 chỉ dùng thư viện chuẩn (+ pytest cho test).
- Hướng dẫn kích thước: ≤ ~400 dòng/file, ≤ ~50 dòng/hàm; vượt phải có lý do.
