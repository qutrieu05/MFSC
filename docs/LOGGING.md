# Logging, Diagnostics & Troubleshooting

**Thực hiện:** `edge/src/msfc/core/logging_setup.py` · **Quyết định:** [ADR-0009](adr/0009-logging-system.md) · **Test:** `edge/tests/unit/test_logging_setup.py`

## 1. Hai đích log

| Đích | Định dạng | Mức mặc định | Dùng khi |
|---|---|---|---|
| Console | `12:01:02.345 INFO     msfc.vision: message {product_id=7-42}` | `INFO` | Chạy trực tiếp, demo, debug nhanh |
| File `logs/msfc.jsonl` | Một JSON object mỗi dòng, xoay vòng 5 MiB × 5 file | `DEBUG` | Phân tích sau, đo thời gian, điều tra lỗi |

Trường JSON: `ts` (UTC, ms, hậu tố `Z`), `level`, `logger`, `msg`, `module`, `func`, `line`, `ctx` (tùy chọn), `exc` (khi có exception).

## 2. Quy tắc viết log

```python
log = get_logger("msfc.decision")
log.info("verdict sent", extra=ctx(product_id=pid, verdict="DEFECT", confidence=0.93))
```

| Nên | Không nên |
|---|---|
| Đặt dữ liệu vào `ctx(...)` để máy đọc được | Nhồi giá trị vào câu văn rồi phải regex lại |
| Tên logger bắt đầu bằng `msfc.<package>` | Dùng `print()` trong code nghiệp vụ |
| `log.exception()` trong `except` | Log rồi vẫn để exception lan ra không kiểm soát |
| `DEBUG` cho chi tiết, `INFO` cho mốc, `WARNING` cho suy giảm, `ERROR` cho lỗi thật | Log `ERROR` cho tình huống bình thường |
| Log một lần ở nơi xử lý lỗi | Log lặp ở mọi tầng gọi |

**Khóa ngữ cảnh chuẩn:** `product_id`, `decision_id`, `cmd_id`, `device_id`, `fault_code`, `topic`, `latency_ms`.

**Không log:** mật khẩu, token, chuỗi kết nối, ảnh khuôn mặt nhận dạng được.

## 3. Chống ngập log

- Thông điệp lặp trong vòng lặp nhanh (mỗi khung hình) chỉ log ở `DEBUG`, hoặc tổng hợp theo cửa sổ (ví dụ mỗi 5 s).
- Payload MQTT không hợp lệ: log ở `WARNING` kèm topic + lý do, có giới hạn tần suất.
- Topic ngoài registry: `DEBUG`.

## 4. Log phía firmware (Phase 1)

| Kênh | Nội dung |
|---|---|
| Serial (`ESP_LOG*`) | Khởi động, self-test, chuyển trạng thái, lỗi, số liệu thời gian |
| LCD tại chỗ | Trạng thái, mã lỗi (ví dụ `F010`), IP, số đếm |
| Bộ đệm vòng trong RAM | N sự kiện an toàn/lỗi gần nhất, publish khi có mạng (SAF-14) |
| MQTT | `event/state_changed`, `fault`, `telemetry/timing` |

## 5. Chẩn đoán (sẽ hoàn thiện ở Phase 1)

| Công cụ | Mục đích |
|---|---|
| `python tools/check_env.py` | Kiểm tra môi trường: Python, pytest, git, GPU, broker, toolchain |
| `msfc doctor` (Phase 1) | Kiểm tra cấu hình, kết nối broker, camera, trạng thái thiết bị |
| `msfc monitor` (Phase 1) | Xem sự kiện MQTT trực tiếp trên console |
| `logs/msfc.jsonl` | Truy vết theo `product_id` / `fault_code` |

## 6. Troubleshooting

Bảng mã lỗi phần cứng/firmware: [SAFETY_CONCEPT.md](SAFETY_CONCEPT.md) mục 5.
Mã lỗi phía Edge Server (`E1xx`) và cách xử lý từng mã sẽ được ghi dần vào `docs/TROUBLESHOOTING.md` (tạo ở Phase 1, yêu cầu FR-OPS-04).

Mẫu một mục troubleshooting: **Triệu chứng → Nguyên nhân có thể → Cách kiểm tra → Cách xử lý → Cách phòng ngừa.**
