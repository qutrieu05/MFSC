# QA Plan — MSFC

**Phiên bản:** 0.1 (DRAFT) · **Ngày:** 2026-09-17 · **Kết quả test:** [TEST_REPORT.md](../TEST_REPORT.md)

## 1. Mười mức test

| Mức | Mã | Chạy ở đâu | Cần phần cứng | Bắt đầu từ phase |
|---|---|---|---|---|
| 1. Unit (Python) | `UT-*` | `pytest` trên laptop | Không | 0 |
| 2. Unit firmware (core_logic trên host) | `FWT-*` | Unity + gcc | Không | 1 |
| 3. Integration (nhiều module + simulator) | `IT-*` | pytest + broker/simulator | Không | 1 |
| 4. Hardware-in-the-loop | `HIL-*` | ESP32 + băng tải thật | **Có** | 1 |
| 5. Vision / AI | `VT-*` | dataset offline + camera | Camera | 1 |
| 6. MQTT / contract | `MT-*` | pytest + broker | Không | 0 |
| 7. Safety | `ST-*` | phần cứng thật | **Có** | 1 |
| 8. Failure & recovery | `FT-*` | simulator + phần cứng | Một phần | 1 |
| 9. Long-running stability | `LT-*` | hệ thống đầy đủ | Có | 1 |
| 10. Performance | `PT-*` | hệ thống đầy đủ | Có | 1 |

**Nguyên tắc:** không test chỉ happy path. Mỗi tính năng phải có ít nhất một test cho **đường lỗi**.

## 2. Test an toàn (ST) — bắt buộc trước khi chạy sản xuất

| ID | Nội dung | Kỳ vọng | SF | Phase |
|---|---|---|---|---|
| ST-01 | Nhấn E-stop khi băng tải chạy | Động cơ mất nguồn (đo bằng đồng hồ), băng dừng | SF-01 | 1 |
| ST-02 | Sau E-stop | Trạng thái `ESTOP` chốt, LCD hiện `F001`, lệnh reset từ xa bị từ chối (`remote_reset_forbidden`) | SF-01, SF-08 | 1 |
| ST-03 | Rút một dây ngõ vào E-stop | Hệ thống coi như đã nhấn → dừng | SAF-11 | 1 |
| ST-04 | Tắt Edge Server khi đang chạy | `FAULT(F010)`, động cơ tắt ≤ timeout + 50 ms | SF-02 | 1 |
| ST-05 | Dừng broker Mosquitto | Như ST-04 | SF-02 | 1 |
| ST-06 | Ngắt Wi-Fi của ESP32 | Như ST-04 | SF-02 | 1 |
| ST-07 | Đưa tay/người vào vùng nguy hiểm | `SAFE_STOP(F020)`; đo độ trễ phát hiện → lệnh dừng | SF-03 | 2 |
| ST-08 | Giả lập `zone_clear=false` liên tục | Không thể START; state hiện lý do | SF-03 | 2 |
| ST-09 | Vùng trống trở lại | Chỉ reset được sau `clear_hold_ms`; sau reset vẫn phải START | SF-03, SF-05 | 2 |
| ST-10 | Dừng service safety vision | `SAFE_STOP(F021)` ≤ 600 ms + 50 ms | SF-04 | 2 |
| ST-11 | Publish heartbeat với `frame_seq` **không tăng** | Coi là cũ → `SAFE_STOP(F021)` | SF-04 | 2 |
| ST-12 | `detector_ok=false` | `SAFE_STOP(F021)` | SF-04 | 2 |
| ST-13 | Cấp nguồn lần đầu | Động cơ tắt, pusher thu, chỉ `IDLE` sau self-test; cần START | SF-05 | 1 |
| ST-14 | Mất điện rồi có điện lại khi đang `RUNNING` | Không tự chạy lại | SF-05 | 1 |
| ST-15 | Ép một task treo (test firmware) | Watchdog reset → boot an toàn + ghi `F051` | SF-06 | 1 |
| ST-16 | Kiểm tra pusher ở mọi trạng thái ≠ `RUNNING` | Luôn ở vị trí thu; lệnh gạt bị bỏ | SF-07 | 1 |
| ST-17 | Nguyên nhân lỗi đã hết nhưng chưa reset | Vẫn giữ safe state | SF-08 | 1 |

## 3. Test lỗi và phục hồi (FT)

| ID | Tình huống lỗi | Kỳ vọng | Cách gây lỗi | Phase |
|---|---|---|---|---|
| FT-01 | Camera bị rút | `vision` → FAULT, không phát verdict; sản phẩm bị loại vì `NO_DECISION`; log `E11x`; cắm lại → tự phục hồi | Rút USB | 1 |
| FT-02 | ESP32 mất kết nối | Dashboard/Edge đánh dấu offline (LWT); không có verdict nào bị "treo" | Rút nguồn ESP32 | 1 |
| FT-03 | Broker MQTT dừng | ESP32 → `FAULT(F010)`; Edge Server thử kết nối lại có backoff | Dừng service Mosquitto | 1 |
| FT-04 | Wi-Fi mất | Như FT-03; ESP32 kết nối lại và **không** tự START | Tắt hotspot/AP | 1 |
| FT-05 | Cảm biến S1/S2 hỏng (luôn mức thấp/cao) | Phát hiện lệch theo dõi (`F030`), có cảnh báo, không gạt sai hàng loạt | Rút cảm biến / che | 1 |
| FT-06 | Giá trị cảm biến vô lý | Bị loại + `WARNING`, không đưa vào phân tích | Giả lập trong simulator | 1 (health: 5) |
| FT-07 | Mô hình AI lỗi (thiếu file/hỏng/sai shape) | Service `FAULT`, log rõ nguyên nhân, không crash toàn hệ | Đổi tên file mô hình | 1 |
| FT-08 | OCR không đọc được | Trả `UNREADABLE` → theo chính sách quyết định (mặc định loại) | Nhãn mờ/thiếu | 3 |
| FT-09 | Động cơ không quay (kẹt/đứt dây) | Không có sản phẩm nào tới S2 → cảnh báo; (Phase 5: `F041` nếu có cảm biến dòng) | Giữ băng tải / rút dây | 1 / 5 |
| FT-10 | Servo pusher không hoạt động | Sản phẩm lỗi đi qua → phát hiện qua đếm; log `WARNING`; (Phase FUTURE: `F040` khi có phản hồi vị trí) | Rút servo | 1 |
| FT-11 | Khởi động lại nguồn giữa lúc chạy | Boot an toàn, `boot_id` tăng, không chạy lại, dữ liệu đã ghi không hỏng | Rút nguồn | 1 |
| FT-12 | Tắt đột ngột Edge Server (kill process) | Log không hỏng; ESP32 `FAULT(F010)`; sau khi chạy lại phải reset có kiểm soát | Kill task | 1 |

## 4. Test hiệu năng (PT) và ổn định (LT)

| ID | Nội dung | Chỉ tiêu (mục tiêu ban đầu) | Phase |
|---|---|---|---|
| PT-01 | Độ trễ S1 → nhận verdict (đồng hồ ESP32) | p95 ≤ 300 ms; **margin > 0 với 100% sản phẩm** | 1 |
| PT-02 | Thời gian suy luận vision | p95 ≤ 50 ms | 1 |
| PT-03 | Xâm nhập vùng → lệnh dừng | p95 ≤ 500 ms | 2 |
| PT-04 | Năng suất | ≥ N sản phẩm/phút ở tốc độ danh định (N chốt ở Phase 1) | 1 |
| PT-05 | Tài nguyên laptop | CPU/GPU/RAM không tăng trôi theo thời gian | 1 |
| LT-01 | Chạy liên tục 2 giờ | Không crash, không rò bộ nhớ, log không ngập | 1 |
| LT-02 | Chạy liên tục 8 giờ | Như trên + số liệu OEE/health hợp lý | 7 |

## 5. Test vision/AI (VT) và MQTT (MT)

| ID | Nội dung | Phase |
|---|---|---|
| VT-01 | Đánh giá offline trên tập test: accuracy, precision, recall, confusion matrix, FP, FN | 1 |
| VT-02 | Thay đổi ánh sáng/vị trí → báo cáo mức suy giảm | 1 |
| VT-03 | Quét ngưỡng độ tin cậy → chọn điểm làm việc, ghi lý do | 1 |
| VT-04 | Kiểm tra chia dữ liệu: **không** trùng phiên chụp giữa train và test (chống rò rỉ) | 1 |
| VT-05 | OCR: ma trận điều kiện (đúng hạn, hết hạn, sai định dạng, không đọc được, thiếu nhãn, lệch, nhiều mức sáng) | 3 |
| MT-01 | Registry + schema + đồng bộ tài liệu | 0 ✅ |
| MT-02 | Payload sai (JSON lỗi, thiếu trường, sai enum) bị loại, ghi `E101`, không crash | 1 |
| MT-03 | Retained `state`/`status` và Last Will hoạt động đúng | 1 |
| MT-04 | Kết nối lại có backoff, không mất trạng thái an toàn | 1 |
| MT-05 | Chống trùng thông điệp QoS 1 theo (`device_id`, `boot_id`, `seq`) | 1 |

## 6. Điều kiện vào/ra của mỗi phase

| Phase | Điều kiện vào | Điều kiện ra (acceptance) |
|---|---|---|
| 0 | – | UT + MT-01 pass; tài liệu nền tảng đủ; PO duyệt |
| 1 | PO duyệt Phase 0; toolchain đã cài; phần cứng tối thiểu sẵn sàng | Acceptance criteria trong [PHASE1_PLAN.md](PHASE1_PLAN.md); ST-01..06, 13..17; FT-01..05, 07, 09..12; PT-01, 02, 04; LT-01; VT-01..04 |
| 2 | Phase 1 đạt | ST-07..12; PT-03; FT-06 |
| 3 | Phase 2 đạt | VT-05; FT-08 |
| 4 | Phase 3 đạt | Kiểm chứng phép tính OEE bằng dữ liệu có đáp án tay; dashboard hiển thị đủ mục |
| 5 | Phase 4 đạt | Baseline + ngưỡng + phát hiện bất thường + FT-06; **không tuyên bố quá năng lực** |
| 6 | Phase 5 đạt | Quản lý mô hình/phiên bản/ngưỡng; dashboard tổng hợp |
| 7 | Phase 6 đạt | Workflow demo 20 bước (ACC-01..20); LT-02; tài liệu bàn giao đầy đủ |

## 7. Quản lý dữ liệu test

- Dataset trong `ai/datasets/<tên>/` với `manifest.json` (danh sách file + checksum + phiên chụp + điều kiện ánh sáng) — **manifest commit, ảnh không commit**.
- Chia train/val/test **theo phiên chụp**, khai báo trong manifest; không trộn ảnh cùng phiên giữa các tập.
- Kịch bản test an toàn/lỗi có checklist in ra giấy để PO tick khi chạy thật, kèm ảnh/video làm bằng chứng.

## 8. Báo cáo test

Mỗi mục trong TEST_REPORT.md gồm: **ID · ngày · môi trường (commit, phiên bản firmware, cấu hình) · cách chạy · kết quả quan sát được · PASS/FAIL/NOT RUN · giới hạn**.

Quy tắc: **"chưa chạy" phải ghi là NOT RUN**, không được ghi PASS. Kết quả trên simulator phải ghi rõ là simulator, không phải phần cứng thật.

## 9. Ma trận truy vết (cập nhật mỗi phase)

| Yêu cầu | Test |
|---|---|
| FR-OPS-02 (cấu hình) | UT `test_config.py` (20 case) ✅ |
| FR-OPS-01 (logging) | UT `test_logging_setup.py` (8 case) ✅ |
| NFR-MNT-01 (layer) | UT `test_layer_dependencies.py` ✅ |
| FR-COM-02, FR-COM-03, FR-COM-04 | MT-01 `test_contract_files.py` (13 case) ✅ |
| SAF-01..17 | ST-01..17 (Phase 1–2) |
| FR-CNV-*, FR-VIS-*, FR-DEC-* | IT/HIL/VT/PT ở Phase 1 |
| FR-OCR-* | VT-05, FT-08 (Phase 3) |
| FR-OEE-* | Phase 4 |
| FR-HLT-* | Phase 5 |
| FR-AIP-*, FR-DSH-02 | Phase 6 |
| ACC-01..20 | Demo cuối Phase 7 |
