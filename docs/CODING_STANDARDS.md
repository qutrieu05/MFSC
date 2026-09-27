# Coding Standards

Áp dụng cho toàn bộ repo. Mục tiêu: **modularity, maintainability, reliability, reproducibility**.

## 1. Quy tắc chung

| # | Quy tắc |
|---|---|
| G1 | **Ngôn ngữ:** code, tên hàm/biến, comment và docstring viết bằng **tiếng Anh**; tài liệu trong `docs/` viết tiếng Việt |
| G2 | Mỗi module có: interface rõ, xử lý lỗi, logging, cấu hình, test, tài liệu (NFR-MNT-03) |
| G3 | Hướng dẫn kích thước: ≤ ~400 dòng/file, ≤ ~50 dòng/hàm, ≤ 4 mức lồng nhau; vượt thì tách hoặc ghi lý do |
| G4 | **Không magic number**: mọi ngưỡng/thời gian/hình học nằm trong config (Python) hoặc `config_store`/hằng số có tên (firmware) |
| G5 | **Không hard-code topic MQTT**: lấy từ registry (Python) hoặc header sinh tự động (firmware) |
| G6 | Không thêm dependency khi thư viện chuẩn làm được; mỗi dependency mới ghi lý do trong DECISIONS.md |
| G7 | Không đổi kiến trúc/contract tùy tiện: sửa ADR hoặc contract trước, code sau |
| G8 | Không commit dataset, ảnh, trọng số mô hình, log, bí mật |

## 2. Python (Edge Server)

| # | Quy tắc |
|---|---|
| P1 | Python 3.11; `from __future__ import annotations`; type hint cho mọi hàm public |
| P2 | `src` layout: `edge/src/msfc/<package>`; import tuyệt đối (`from msfc.core import ...`) |
| P3 | Tuân thủ quy tắc phụ thuộc layer trong ARCHITECTURE 7.2 (test `test_layer_dependencies.py` kiểm tra) |
| P4 | Dữ liệu dùng chung là **dataclass bất biến** trong `msfc.domain`; không truyền dict tự do giữa các layer |
| P5 | Interface định nghĩa bằng `typing.Protocol` hoặc abstract base; implementation nằm cạnh nhau (`vision/inference/onnx_engine.py`) |
| P6 | Exception: chỉ ném lớp con của `MsfcError`; thông điệp phải nêu giá trị/khóa gây lỗi |
| P7 | Không `except Exception: pass`; vòng lặp service bắt exception, log, cập nhật trạng thái service, rồi tiếp tục hoặc chuyển FAULT |
| P8 | Không I/O hay `sleep` trong hàm tính toán thuần (để test được); tách phần "quyết định" khỏi phần "thực thi" |
| P9 | `print()` chỉ dùng trong `cli`/`tools`; phần còn lại dùng logger |
| P10 | Định dạng: dòng ≤ 110 ký tự, 4 space; `ruff`/`black` là tùy chọn, không bắt buộc |
| P11 | Test: `pytest`, tên `test_<đối tượng>_<hành vi>`; mỗi bug được sửa phải kèm một test tái hiện |

## 3. C / firmware (ESP32)

| # | Quy tắc |
|---|---|
| C1 | C99 (ESP-IDF); tên hàm `module_action()` (ví dụ `product_tracker_push()`); kiểu `stdint` (`uint32_t`) |
| C2 | `components/core_logic` **không include ESP-IDF** → test được trên host bằng Unity |
| C3 | Không cấp phát động sau khi khởi tạo trong đường điều khiển; dùng buffer tĩnh/queue kích thước cố định |
| C4 | ISR: chỉ chụp timestamp và đẩy vào queue; **không** log, không cấp phát, dùng `IRAM_ATTR` khi cần |
| C5 | `control_task` chu kỳ cố định (10 ms), **không bao giờ chờ mạng**; giao tiếp với `comm_task` qua queue không chặn |
| C6 | Máy trạng thái viết dạng **bảng chuyển trạng thái** + hàm `on_enter/on_exit`, không rải `if` khắp nơi |
| C7 | Mọi trạng thái lỗi có **mã trong bảng mã lỗi**; không có lỗi "im lặng" |
| C8 | Ngõ ra an toàn (motor enable, safety relay) chỉ được set ở **một chỗ duy nhất**, sau khi `safety_supervisor` cho phép |
| C9 | Kiểm tra giá trị trả về của mọi API ESP-IDF; lỗi khởi tạo → `SELF_TEST_FAILED` |
| C10 | Watchdog: mọi task dài phải feed watchdog; không tắt watchdog để "cho dễ" |

## 4. Quy trình cho mỗi tính năng

```
REQUIREMENT (ID trong REQUIREMENTS.md)
 → DESIGN (cập nhật ARCHITECTURE/contract/ADR nếu cần)
 → IMPLEMENTATION
 → UNIT TEST
 → INTEGRATION TEST (có simulator hoặc phần cứng)
 → REVIEW (checklist mục 5)
 → DOCUMENTATION (docs + CHANGELOG + TEST_REPORT)
```

Không gộp nhiều tính năng vào một task. Không ghép module khi module riêng chưa ổn định (quy tắc solo).

## 5. Checklist review

- [ ] Có ID yêu cầu và ID task tương ứng
- [ ] Có test, và test **fail** trước khi sửa (với bug)
- [ ] Không hard-code ngưỡng/topic/đường dẫn
- [ ] Xử lý lỗi và log đầy đủ ở ranh giới module
- [ ] Không phá quy tắc phụ thuộc layer
- [ ] Ảnh hưởng tới an toàn được xem xét rõ (nếu có, cập nhật SAFETY_CONCEPT + test ST-xx)
- [ ] Tài liệu, CHANGELOG, TEST_REPORT được cập nhật
- [ ] Giới hạn đã biết được ghi lại, **không che giấu**
