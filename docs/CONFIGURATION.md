# Configuration System

**Thực hiện:** `edge/src/msfc/core/config.py` · **Quyết định:** [ADR-0008](adr/0008-configuration-system.md) · **Test:** `edge/tests/unit/test_config.py`

## 1. Thứ tự ưu tiên

```
config/default.toml   (commit, chứa mọi khóa, có ghi chú)
      ↓ bị ghi đè bởi
config/site.toml      (KHÔNG commit: mật khẩu broker, chỉ số camera, giá trị riêng máy)
      ↓ bị ghi đè bởi
MSFC__<SECTION>__<KEY>  (biến môi trường, dùng cho test và chạy tạm)
```

Ví dụ: `set MSFC__MQTT__PORT=1884` (cmd) hoặc `$env:MSFC__MQTT__PORT="1884"` (PowerShell).

## 2. Cách dùng trong code

```python
from msfc.core import load_config, configure_logging, get_logger, ctx

cfg = load_config()                 # ném ConfigError nếu cấu hình sai
log_path = configure_logging(cfg)
log = get_logger("msfc.example")
log.info("started", extra=ctx(line_id=cfg.system.line_id))
```

- `AppConfig` là dataclass **bất biến** (`frozen=True`), truyền vào module qua constructor.
- **Không** dùng biến cấu hình toàn cục, **không** đọc `os.environ` rải rác trong code nghiệp vụ.
- Đường dẫn lấy qua `cfg.path("log_dir")`, `cfg.path("runtime_dir")`, `cfg.path("contracts_dir")` (tự resolve theo repo root; đường dẫn tuyệt đối được giữ nguyên).

## 3. Quy tắc kiểm tra (fail fast)

| Tình huống | Kết quả |
|---|---|
| Thiếu `config/default.toml` | `ConfigError: configuration file not found` |
| TOML sai cú pháp | `ConfigError: invalid TOML in …` |
| **Khóa lạ** (ví dụ gõ `prot` thay vì `port`) | `ConfigError: [mqtt] unknown key(s): prot; known keys: [...]` |
| Section lạ | `ConfigError: unknown section(s): vision` |
| Giá trị ngoài dải | `ConfigError: [mqtt.port] must be a number within [1, 65535], got 0` |
| Mức log không hợp lệ | `ConfigError: [logging.console_level] must be one of [...]` |
| `config_version` không khớp | `ConfigError: [config_version] expected 1, got 99` |
| Biến môi trường sai dạng/sai khóa | `ConfigError` nêu rõ tên biến |

## 4. Các section hiện có (config_version = 1)

| Section | Khóa | Dải hợp lệ |
|---|---|---|
| `system` | `line_id`, `device_id`, `site_name`, `timezone` | `line_id`: a–z0–9, 3–16 ký tự; `device_id`: a–z0–9 và `-`, 3–32 ký tự |
| `mqtt` | `host`, `port`, `username`, `password`, `client_id`, `keepalive_s`, `heartbeat_interval_ms`, `command_ack_timeout_ms` | `port` 1–65535; `keepalive_s` 1–300; `heartbeat_interval_ms` 50–5000; `command_ack_timeout_ms` 100–30000 |
| `paths` | `runtime_dir`, `log_dir`, `contracts_dir` | chuỗi không rỗng |
| `logging` | `console_level`, `file_level`, `json_file`, `max_bytes`, `backup_count`, `[logging.levels]` | mức log hợp lệ; `max_bytes` ≥ 4096; `backup_count` 0–100 |

## 5. Khi thêm tính năng mới (mỗi phase)

1. Thêm section/khóa vào `config/default.toml` kèm ghi chú và đơn vị (ví dụ `_ms`, `_pct`, `_mm`).
2. Thêm dataclass hoặc field tương ứng trong `config.py` + kiểm tra dải trong `__post_init__`.
3. Thêm test cho giá trị hợp lệ **và** giá trị sai.
4. Nếu thay đổi không tương thích: tăng `CONFIG_VERSION` và ghi vào [DECISIONS.md](../DECISIONS.md).

## 6. Bí mật

- Mật khẩu broker chỉ nằm trong `config/site.toml` (đã gitignore) — xem `config/site.example.toml`.
- Không log mật khẩu; không đưa vào ảnh chụp dashboard khi demo.
- Firmware lưu SSID/mật khẩu Wi-Fi và thông tin broker trong **NVS**, nạp qua console serial (Phase 1), không hard-code trong source.
