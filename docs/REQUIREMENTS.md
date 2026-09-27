# System Requirements Specification — MSFC

**Phiên bản:** 0.1 (DRAFT — chờ PO duyệt) · **Ngày:** 2026-09-17

## 0. Quy ước

- **Mức ưu tiên:** MUST (bắt buộc) · SHOULD (nên có) · COULD (có thì tốt)
- **Phase:** phase đầu tiên yêu cầu phải được đáp ứng
- **Kiểm chứng:** T = Test · D = Demo · I = Inspection (kiểm tra tài liệu/code) · A = Analysis
- **Thứ tự ưu tiên khi xung đột:** **SAF > NFR-REL > FR sản xuất > các yêu cầu khác**
- Các chỉ tiêu số có nhãn **(mục tiêu ban đầu)** sẽ được xác nhận hoặc điều chỉnh sau khi đo thực tế, và mọi điều chỉnh phải ghi vào [DECISIONS.md](../DECISIONS.md)

---

## 1. Yêu cầu an toàn (SAF), ưu tiên cao nhất

> ⚠️ Đây là **prototype học tập, điện áp thấp**. Các chức năng dưới đây **không** phải chức năng an toàn đạt chuẩn ISO 13849 / IEC 62061. Chi tiết xem [SAFETY_CONCEPT.md](SAFETY_CONCEPT.md).

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| SAF-01 | Nút dừng khẩn (E-stop, tiếp điểm NC) **ngắt trực tiếp nguồn động cơ bằng phần cứng**, không phụ thuộc firmware. ESP32 đọc trạng thái nút và chốt (latch) lỗi `ESTOP` | MUST | 1 | T |
| SAF-02 | Khi khởi động, cell ở trạng thái an toàn (động cơ tắt, actuator thu về) cho tới khi self-test đạt **và** có lệnh START tường minh | MUST | 1 | T |
| SAF-03 | Mất heartbeat của Edge Server quá `comm.heartbeat_timeout_ms` (mặc định 1000 ms) → `SAFE_STOP`, chốt lỗi `COMM_LOSS`. Lệnh dừng động cơ được phát trong ≤ 50 ms kể từ lúc phát hiện timeout (mục tiêu ban đầu) | MUST | 1 | T |
| SAF-04 | Khi bật giám sát vùng: heartbeat của safety vision vắng hoặc cũ quá `safety.vision_stale_ms` (mặc định 600 ms), hoặc `zone_clear=false` → `SAFE_STOP`, chốt lỗi `ZONE_INTRUSION` hoặc `SAFETY_VISION_LOST` | MUST | 2 | T |
| SAF-05 | Lỗi đã chốt chỉ được xóa qua **reset có kiểm soát**: `ESTOP` chỉ reset bằng nút RESET tại chỗ; các lỗi khác reset tại chỗ hoặc bằng lệnh từ xa **khi nguyên nhân đã hết** | MUST | 1 | T |
| SAF-06 | **Không tự khởi động lại** sau `SAFE_STOP`/`FAULT`; phải reset rồi START | MUST | 1 | T |
| SAF-07 | Actuator về vị trí thu (an toàn) khi BOOT/`SAFE_STOP`/`FAULT`; không thực hiện gạt khi không ở `RUNNING` | MUST | 1 | T |
| SAF-08 | Watchdog firmware: task treo → reset → boot về trạng thái an toàn; ghi lý do reset | MUST | 1 | T |
| SAF-09 | Logic an toàn được đánh giá **trước** logic sản xuất trong mỗi chu kỳ điều khiển; lệnh sản xuất bị từ chối khi không ở trạng thái cho phép | MUST | 1 | T/I |
| SAF-10 | Tín hiệu cho phép động cơ theo nguyên tắc **mất tín hiệu = động cơ tắt** (có điện trở kéo xuống, relay/driver mặc định ngắt) | MUST | 1 | T/I |
| SAF-11 | Đứt dây ngõ vào E-stop được hiểu là **nhấn E-stop** | MUST | 1 | T |
| SAF-12 | S1 chỉ dùng điện áp thấp DC ≤ 12 V cho động cơ, servo, actuator | MUST | 1 | I |
| SAF-13 | Tài liệu và dashboard nêu rõ giám sát bằng camera là **bổ sung**, không phải thiết bị an toàn đạt chuẩn | MUST | 2 | I |
| SAF-14 | Sự kiện an toàn được lưu tại ESP32 (bộ đệm vòng + mã lỗi trên LCD) và publish khi có kết nối | SHOULD | 1 | T |
| SAF-15 | Đo và báo cáo: độ trễ phát hiện xâm nhập, độ trễ tới lệnh dừng, thời gian tới khi băng tải dừng hẳn | MUST | 2 | T |

## 2. Yêu cầu chức năng

### 2.1 Băng tải và điều khiển (FR-CNV), firmware ESP32

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-CNV-01 | Điều khiển tốc độ động cơ băng tải bằng PWM có ramp tăng/giảm; setpoint cấu hình được | MUST | 1 | T |
| FR-CNV-02 | Phát hiện sản phẩm tại cảm biến kiểm tra S1 (chống dội); gán `product_id` duy nhất theo `boot_id` + bộ đếm | MUST | 1 | T |
| FR-CNV-03 | Theo dõi sản phẩm bằng FIFO từ S1 tới S2; phát hiện lệch theo dõi (S2 kích khi hàng đợi rỗng, tràn hàng đợi) | MUST | 1 | T |
| FR-CNV-04 | Tại S2: gạt nếu verdict = `DEFECT` **hoặc không có verdict trước hạn** (chính sách mặc định `reject_on_no_decision=true`, cấu hình được) | MUST | 1 | T |
| FR-CNV-05 | Độ trễ gạt sau S2, thời gian đẩy/thu cấu hình được | MUST | 1 | T |
| FR-CNV-06 | Publish sự kiện: sản phẩm phát hiện, sản phẩm đã phân loại, đổi trạng thái, lỗi | MUST | 1 | T |
| FR-CNV-07 | Hiển thị tại chỗ: LED xanh/vàng/đỏ + LCD (trạng thái, mã lỗi, IP, số đếm) | SHOULD | 1 | D |
| FR-CNV-08 | Nhận lệnh `start`, `stop`, `reset`, `set_speed`, `pusher_test`; trả `ack` gồm kết quả và lý do từ chối | MUST | 1 | T |
| FR-CNV-09 | Ghi timestamp theo đồng hồ ESP32 cho: phát hiện S1, nhận verdict, kích S2, gạt | MUST | 1 | T |
| FR-CNV-10 | Đo tốc độ băng tải bằng encoder | COULD | 4 | T |

### 2.2 Thị giác kiểm tra ngoại quan (FR-VIS), Edge Server

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-VIS-01 | Thu khung hình từ camera USB (độ phân giải, phơi sáng cấu hình được) vào bộ đệm vòng có timestamp | MUST | 1 | T |
| FR-VIS-02 | Khi nhận `product_detected`, chọn khung hình phù hợp và cắt ROI | MUST | 1 | T |
| FR-VIS-03 | Tiền xử lý là pipeline các bước cấu hình được | MUST | 1 | T |
| FR-VIS-04 | Suy luận qua interface `InferenceEngine` thay được backend (baseline cổ điển, mô hình ONNX) | MUST | 1 | T/I |
| FR-VIS-05 | Hậu xử lý → `GOOD` / `DEFECT` / `UNCERTAIN` + độ tin cậy; ngưỡng cấu hình được | MUST | 1 | T |
| FR-VIS-06 | Publish kết quả kiểm tra kèm tên + phiên bản mô hình + thời gian từng bước | MUST | 1 | T |
| FR-VIS-07 | Lưu ảnh kiểm tra (theo tỷ lệ mẫu, mọi ảnh DEFECT/UNCERTAIN) kèm metadata; giới hạn lưu trữ cấu hình được | SHOULD | 1 | T |
| FR-VIS-08 | Số liệu: FPS, độ trễ p50/p95, phân bố độ tin cậy | MUST | 1 | T |
| FR-VIS-09 | Mất camera → trạng thái vision `FAULT`, không phát verdict, phát sự kiện lỗi | MUST | 1 | T |
| FR-VIS-10 | Công cụ đánh giá offline trên dataset có nhãn: accuracy, precision, recall, confusion matrix, FP, FN | MUST | 1 | T |

### 2.3 Decision Engine (FR-DEC)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-DEC-01 | Kết hợp kết quả vision (và OCR từ Phase 3) thành verdict cuối kèm **mã lý do** theo luật cấu hình | MUST | 1 | T |
| FR-DEC-02 | Không gửi verdict đã quá hạn (theo ước lượng thời điểm tới S2); ghi nhận `LATE` | SHOULD | 1 | T |
| FR-DEC-03 | Nhật ký quyết định cho từng sản phẩm (đầu vào, luật áp dụng, đầu ra) để truy vết | MUST | 1 | T |
| FR-DEC-04 | `UNCERTAIN` được xử lý theo chính sách cấu hình (mặc định: `DEFECT`) | MUST | 1 | T |

### 2.4 Giám sát vùng nguy hiểm (FR-SVS)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-SVS-01 | Cấu hình một hoặc nhiều vùng nguy hiểm dạng đa giác | MUST | 2 | T |
| FR-SVS-02 | Phát hiện người (và/hoặc tay) trong khung hình | MUST | 2 | T |
| FR-SVS-03 | Quyết định vùng bị chiếm có debounce/hysteresis cấu hình được | MUST | 2 | T |
| FR-SVS-04 | Heartbeat an toàn ≥ 5 Hz gồm `zone_clear`, `frame_seq`, `frame_age_ms`, `detector_ok` | MUST | 2 | T |
| FR-SVS-05 | Sự kiện xâm nhập; ảnh sự kiện (nếu lưu) phải được làm mờ khuôn mặt | SHOULD | 2 | T |
| FR-SVS-06 | Đo độ trễ phát hiện, tỷ lệ báo nhầm (FP), bỏ sót (FN) trên kịch bản có nhãn | MUST | 2 | T |

### 2.5 OCR hạn sử dụng / nhãn (FR-OCR)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-OCR-01 | Phát hiện/định vị nhãn trên sản phẩm | MUST | 3 | T |
| FR-OCR-02 | Nhận dạng văn bản trên nhãn | MUST | 3 | T |
| FR-OCR-03 | Trích xuất hạn sử dụng theo các định dạng cấu hình được | MUST | 3 | T |
| FR-OCR-04 | Kiểm tra hợp lệ → mã lý do: `OK`, `EXPIRED`, `FORMAT_INVALID`, `UNREADABLE`, `LABEL_MISSING`, `LABEL_MISALIGNED` | MUST | 3 | T |
| FR-OCR-05 | Đo độ chính xác OCR, thời gian xử lý, thống kê các trường hợp lỗi | MUST | 3 | T |
| FR-OCR-06 | Bộ test gồm: đúng hạn, hết hạn, sai định dạng, không đọc được, thiếu nhãn, nhãn lệch, nhiều điều kiện ánh sáng | MUST | 3 | T |

### 2.6 OEE (FR-OEE)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-OEE-01 | Mô hình trạng thái máy (RUNNING, IDLE, STOPPED, SAFE_STOP, FAULT, …) với timestamp chuyển trạng thái | MUST | 4 | T |
| FR-OEE-02 | Đếm tổng, GOOD, DEFECT | MUST | 4 | T |
| FR-OEE-03 | Downtime có kế hoạch / không kế hoạch kèm nguyên nhân | MUST | 4 | T |
| FR-OEE-04 | Tính Availability, Performance (theo ideal cycle time cấu hình), Quality, OEE theo cửa sổ/ca | MUST | 4 | T |
| FR-OEE-05 | Kiểm chứng phép tính OEE bằng dữ liệu tổng hợp có đáp án tính tay | MUST | 4 | T |

### 2.7 Sức khỏe động cơ (FR-HLT)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-HLT-01 | Thu rung động, nhiệt độ, dòng điện (mỗi cảm biến bật/tắt theo phần cứng thực có) | MUST | 5 | T |
| FR-HLT-02 | Quy trình thu baseline có ghi điều kiện vận hành | MUST | 5 | T |
| FR-HLT-03 | Đặc trưng (RMS, peak, crest factor, nhiệt độ, dòng trung bình) và ngưỡng → `NORMAL` / `WARNING` / `CRITICAL` | MUST | 5 | T |
| FR-HLT-04 | Phát hiện bất thường thống kê so với baseline | MUST | 5 | T |
| FR-HLT-05 | Phát hiện lỗi cảm biến: giá trị ngoài dải, kẹt giá trị, mất dữ liệu | MUST | 5 | T |
| FR-HLT-06 | Ghi sự kiện sức khỏe; hành động khi `CRITICAL` cấu hình được (mặc định: chỉ cảnh báo, **PO quyết định**) | MUST | 5 | T |
| FR-HLT-07 | **Không** gọi là "predictive maintenance AI" khi chưa có dữ liệu suy giảm đủ tin cậy | MUST | 5 | I |

### 2.8 Truyền thông (FR-COM)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-COM-01 | MQTT broker chạy local trên mạng LAN | MUST | 1 | T |
| FR-COM-02 | **Registry topic là nguồn sự thật duy nhất**; không hard-code topic rải rác trong code | MUST | 1 | T/I |
| FR-COM-03 | Mọi payload dùng envelope chung có `schema`, `device_id`, `seq`, `mono_ms` (và `ts` nếu có đồng bộ giờ) | MUST | 1 | T |
| FR-COM-04 | QoS và retain đúng theo [MQTT_CONTRACT.md](MQTT_CONTRACT.md); `status` dùng Last Will | MUST | 1 | T |
| FR-COM-05 | Lệnh có `cmd_id` và luôn nhận `ack` (thành công/từ chối + lý do) | MUST | 1 | T |
| FR-COM-06 | Edge Server kiểm tra hợp lệ payload đầu vào; payload sai bị loại và ghi log | MUST | 1 | T |
| FR-COM-07 | Tự kết nối lại với backoff; không mất trạng thái an toàn khi kết nối lại | MUST | 1 | T |

### 2.9 Edge Server, lưu trữ, dashboard, vận hành

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| FR-SRV-01 | Bộ điều phối khởi động các service theo cấu hình; self-check lúc khởi động; tắt êm | MUST | 1 | T |
| FR-SRV-02 | Mỗi service báo trạng thái (`OK`/`DEGRADED`/`FAULT`) và heartbeat | MUST | 1 | T |
| FR-SRV-03 | Bộ mô phỏng ESP32 và camera để test không cần phần cứng | MUST | 1 | T |
| FR-DB-01 | Lưu sản phẩm, quyết định, sự kiện, lỗi, số liệu OEE, sức khỏe vào SQLite | MUST | 4 | T |
| FR-DB-02 | Chính sách lưu giữ và xuất CSV | SHOULD | 4 | T |
| FR-DSH-01 | Dashboard hiển thị: trạng thái máy, số đếm, GOOD/DEFECT, downtime, OEE, sự kiện | MUST | 4 | D |
| FR-DSH-02 | Dashboard tổng hợp: VISION, OCR, MACHINE, SAFETY, OEE, HEALTH, MQTT, SYSTEM STATUS | MUST | 6 | D |
| FR-OPS-01 | Log có cấu trúc (JSON lines) + log console dễ đọc; mã tương quan (`product_id`, `cmd_id`) | MUST | 0 | T |
| FR-OPS-02 | Cấu hình phân lớp (mặc định → site → biến môi trường), kiểm tra hợp lệ lúc khởi động, lỗi rõ ràng | MUST | 0 | T |
| FR-OPS-03 | Lệnh chẩn đoán (trạng thái các service, kết nối broker, camera, thiết bị) | MUST | 1 | T |
| FR-OPS-04 | Tài liệu troubleshooting cho mọi mã lỗi | MUST | 7 | I |
| FR-AIP-01 | Quản lý mô hình: tên, phiên bản, checksum, model card, ngưỡng; chọn mô hình qua cấu hình | MUST | 6 | T |
| FR-AIP-02 | Cơ chế cập nhật mô hình có kiểm tra và rollback; OTA **chỉ khi phần cứng thực tế hỗ trợ** | MUST | 6 | T |
| FR-EXT-01 | Thêm camera/máy/mô hình/cảm biến bằng `device_id` + cấu hình + registry, **không sửa code của layer khác** (mục tiêu) | SHOULD | 6 | A/T |

## 3. Yêu cầu phi chức năng (NFR)

| ID | Yêu cầu | Mức | Phase | KC |
|---|---|---|---|---|
| NFR-PERF-01 | Từ lúc S1 phát hiện đến lúc ESP32 nhận verdict (đo trên đồng hồ ESP32): p95 ≤ 300 ms (mục tiêu ban đầu); **100% verdict tới trước khi sản phẩm đến S2** ở tốc độ danh định | MUST | 1 | T |
| NFR-PERF-02 | Suy luận ảnh ROI trên RTX 3050: p95 ≤ 50 ms (mục tiêu ban đầu) | SHOULD | 1 | T |
| NFR-PERF-03 | Xâm nhập vùng → ESP32 phát lệnh dừng: p95 ≤ 500 ms (mục tiêu ban đầu, giám sát bổ sung) | MUST | 2 | T |
| NFR-REL-01 | Chạy liên tục 2 giờ (Phase 1) và 8 giờ (Phase 7) không crash, bộ nhớ ổn định | MUST | 1 | T |
| NFR-REL-02 | Mọi failure case trong [QA_PLAN.md](QA_PLAN.md) áp dụng cho phase phải được test | MUST | 1 | T |
| NFR-REL-03 | Quy trình recovery có tài liệu và đã được test | MUST | 1 | T |
| NFR-MNT-01 | Tuân thủ quy tắc phụ thuộc giữa các layer ([ARCHITECTURE.md](../ARCHITECTURE.md)); có test kiểm tra import | MUST | 1 | T |
| NFR-MNT-02 | Không hard-code topic, đường dẫn, ngưỡng trong code nghiệp vụ; có test quét chuỗi topic | MUST | 1 | T |
| NFR-MNT-03 | Mỗi module có interface, xử lý lỗi, logging, cấu hình, test, tài liệu | MUST | 0 | I |
| NFR-SEC-01 | Broker bắt buộc username/password; chỉ mở trong LAN; không mở ra Internet | MUST | 1 | T/I |
| NFR-SEC-02 | Không lưu bí mật trong git | MUST | 0 | I |
| NFR-PRV-01 | Camera an toàn: mặc định không lưu video thô; ảnh sự kiện được ẩn danh; có giới hạn lưu giữ | MUST | 2 | I/T |
| NFR-PRT-01 | Edge Server chạy trên Windows 11 + Python 3.11; firmware trên ESP32 với ESP-IDF 5.x (chờ ADR-0006 được duyệt) | MUST | 0 | I |
| NFR-REP-01 | Tái lập được: khóa phiên bản dependency theo phase; dataset có manifest + checksum; mô hình có model card | MUST | 1 | I |
| NFR-DEP-01 | Chỉ thêm dependency khi cần; mỗi dependency mới ghi lý do trong DECISIONS.md | MUST | 0 | I |

## 4. Tiêu chí chấp nhận cuối cùng (ACC), workflow demo 20 bước

| Bước | Nội dung | Yêu cầu liên quan |
|---|---|---|
| ACC-01 | Power on | SAF-02 |
| ACC-02 | System self-check (ESP32 + Edge Server + camera + broker) | FR-SRV-01, FR-OPS-03 |
| ACC-03 | Camera bắt đầu hoạt động | FR-VIS-01 |
| ACC-04 | Băng tải bắt đầu chạy (sau lệnh START) | FR-CNV-01, SAF-06 |
| ACC-05 | Sản phẩm xuất hiện | FR-CNV-02 |
| ACC-06 | Vision AI nhận diện sản phẩm | FR-VIS-02..06 |
| ACC-07 | OCR kiểm tra nhãn/hạn dùng | FR-OCR-01..04 |
| ACC-08 | Decision engine ra quyết định | FR-DEC-01..04 |
| ACC-09 | ESP32 điều khiển actuator | FR-CNV-04, 05 |
| ACC-10 | Sản phẩm GOOD đi qua | FR-CNV-04 |
| ACC-11 | Sản phẩm DEFECT bị gạt | FR-CNV-04 |
| ACC-12 | Thống kê sản xuất được cập nhật | FR-OEE-02 |
| ACC-13 | OEE được cập nhật | FR-OEE-04 |
| ACC-14 | Sức khỏe động cơ được theo dõi | FR-HLT-01..06 |
| ACC-15 | Vùng an toàn được giám sát | FR-SVS-01..04 |
| ACC-16 | Người vào vùng → băng tải về safe state | SAF-04, SAF-15 |
| ACC-17 | MQTT truyền dữ liệu về Edge Server | FR-COM-01..07 |
| ACC-18 | Dashboard hiển thị toàn hệ thống | FR-DSH-02 |
| ACC-19 | Fault được ghi log | FR-OPS-01, SAF-14 |
| ACC-20 | Có quy trình recovery sau fault | SAF-05, NFR-REL-03 |

## 5. Truy vết

Ma trận yêu cầu → test được duy trì trong [QA_PLAN.md](QA_PLAN.md) (mục Traceability) và cập nhật mỗi phase.
