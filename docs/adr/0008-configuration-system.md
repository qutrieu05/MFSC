# ADR-0008: Hệ thống cấu hình

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Ngưỡng, thời gian, hình học băng tải, địa chỉ broker, đường dẫn… **không được hard-code**. Cấu hình sai phải bị phát hiện **lúc khởi động**, không phải lúc đang chạy.

## Các phương án

| Định dạng | Dependency | Comment | Ghi chú |
|---|---|---|---|
| YAML | PyYAML | Có | Thêm dependency; dễ sai do thụt lề |
| JSON | Không | **Không** | Khó ghi chú cho người vận hành |
| **TOML** | **Không** (`tomllib` có sẵn từ Python 3.11) | Có | Kiểu dữ liệu rõ, phổ biến |

## Quyết định

**TOML + `tomllib`**, phân lớp theo thứ tự ghi đè:

1. `config/default.toml` (commit, đầy đủ mọi khóa, có ghi chú)
2. `config/site.toml` (không commit: mật khẩu broker, chỉ số camera, giá trị riêng theo máy)
3. Biến môi trường `MSFC__<SECTION>__<KEY>` (ví dụ `MSFC__MQTT__PORT=1884`)

Kiểm tra **nghiêm ngặt** khi nạp:
- **Khóa lạ → lỗi** (bắt lỗi gõ sai).
- Sai kiểu hoặc ngoài dải → lỗi có đường dẫn khóa rõ ràng.

Kết quả là dataclass **bất biến**, truyền vào module qua constructor (không dùng biến toàn cục).

**Firmware:** giá trị mặc định biên dịch sẵn + ghi đè trong NVS qua lệnh console serial (Phase 1); cùng tên khóa với phần tương ứng của TOML khi hợp lý.

## Hệ quả

- Thêm tính năng = thêm section/khóa mới vào `default.toml` + dataclass + test.
- `config_version` tăng khi thay đổi không tương thích.
- Chi tiết: [CONFIGURATION.md](../CONFIGURATION.md).
