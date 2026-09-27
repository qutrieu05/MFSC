# Risk Register — MSFC

**Phiên bản:** 0.1 · **Ngày:** 2026-09-17 · Cập nhật ở mỗi lần review phase.

**Thang đo:** Xác suất (XS) và Tác động (TĐ): T = thấp, TB = trung bình, C = cao.
**Mức:** `XS×TĐ` → 🔴 cao (cần biện pháp trước khi vào phase liên quan) · 🟡 trung bình (theo dõi) · 🟢 thấp.

| ID | Rủi ro | XS | TĐ | Mức | Dấu hiệu sớm | Biện pháp / Kế hoạch dự phòng | Phase |
|---|---|:-:|:-:|:-:|---|---|---|
| R-01 | **Wi-Fi chập chờn gây dừng oan** (heartbeat timeout) | C | TB | 🔴 | Log `F010` xuất hiện khi không có lỗi thật | Đo tỷ lệ mất heartbeat ở Phase 1 trước khi chạy sản xuất; chỉnh timeout trong dải 300–3000 ms; dùng AP riêng 2,4 GHz đặt gần; nếu vẫn tệ → cân nhắc bridge USB-serial cho kênh điều khiển (ADR mới) | 1 |
| R-02 | **Băng tải tự chế không chạy ổn định** (trượt đai, lệch, rung) | C | C | 🔴 | Sản phẩm dừng giữa đường, tốc độ không đều | Thiết kế đơn giản, con lăn PVC + căng đai điều chỉnh được; chạy thử 30 phút trước khi tích hợp vision; dự phòng: máng trượt + cảm biến (giảm phạm vi V03) | 1 |
| R-03 | ~~Chưa rõ model ESP32/camera/động cơ đang có~~ → **ĐÃ GIẢI QUYẾT 2026-09-18: PO xác nhận không có linh kiện nào** (D-019). Rủi ro chuyển thành R-21..R-26 | – | – | ✅ đóng | – | Thay bằng chiến lược mua theo wave + interface-first | 0→1 |
| R-04 | **Nguồn động cơ/servo gây sụt áp làm ESP32 reset** | C | TB | 🔴 | ESP32 reset khi động cơ khởi động; `F052` | Nguồn riêng cho động cơ/servo, chung GND; tụ lọc; dây đủ lớn; đo điện áp khi khởi động | 1 |
| R-05 | Dataset quá ít hoặc thiên lệch → mô hình ảo tốt | C | C | 🔴 | Accuracy cao bất thường, FN cao khi thay ánh sáng | Chia dữ liệu theo phiên chụp (VT-04); báo cáo giới hạn; tăng mẫu, đa dạng ánh sáng; baseline cổ điển để so sánh | 1 |
| R-06 | Ánh sáng thay đổi làm vision/OCR sai | C | TB | 🟡 | Độ tin cậy giảm theo giờ trong ngày | Hộp che sáng + đèn LED cố định; ghi điều kiện sáng vào metadata; đo lại theo VT-02 | 1, 3 |
| R-07 | **Phạm vi phình to** (thêm tính năng ngoài S1) | C | C | 🔴 | TASKS.md mọc thêm task không có ID yêu cầu | Mọi đề xuất mới vào FUTURE/OPTIONAL; cần PO duyệt để đổi scope; review cuối mỗi phase | mọi phase |
| R-08 | Một người làm, dễ kiệt sức / dở dang | TB | C | 🟡 | Phase kéo dài quá 1,5× dự kiến | Mỗi phase tự demo được; ưu tiên phần chạy trên laptop trước; cho phép hạ mục tiêu (MVP-first) và ghi quyết định | mọi phase |
| R-09 | Toolchain firmware (ESP-IDF/gcc) cài đặt tốn thời gian | TB | TB | 🟡 | Quá 1 tuần chưa build được ví dụ hello world | Cài theo hướng dẫn ở đầu Phase 1, kiểm bằng `idf.py --version`; dự phòng ADR-0006 phương án C (PlatformIO) | 1 |
| R-10 | **Camera-based safety bị hiểu là an toàn đạt chuẩn** | TB | C | 🔴 | Tài liệu/demo nói "hệ thống an toàn" | Ghi giới hạn ở SAFETY_CONCEPT, README, dashboard; E-stop cứng là biện pháp chính; che chắn cơ khí | 2 |
| R-11 | Quyền riêng tư khi quay người (Luật 91/2025) | TB | TB | 🟡 | Lưu video thô có mặt người | Không lưu video thô; làm mờ mặt; giới hạn lưu giữ; chỉ quay người tình nguyện | 2 |
| R-12 | Laptop là điểm lỗi đơn cho sản xuất | C | T | 🟢 | Mất laptop → dây chuyền dừng | Chấp nhận trong S1 (an toàn không phụ thuộc laptop); FUTURE: chuyển broker sang Raspberry Pi | 1 |
| R-13 | 4 GB VRAM không đủ khi chạy đồng thời vision + OCR + phát hiện người | TB | TB | 🟡 | CUDA OOM, FPS tụt khi bật đủ service | Mô hình nano/ROI nhỏ; chạy tuần tự theo sự kiện thay vì stream liên tục; đo ở PT-02/PT-05; dự phòng: chuyển OCR sang CPU | 3–6 |
| R-14 | OCR không đạt độ chính xác mong đợi trên nhãn tự in | TB | TB | 🟡 | Tỷ lệ `UNREADABLE` cao | Chuẩn hóa nhãn (font, tương phản, vị trí); thử 2 engine; chấp nhận `UNREADABLE` → loại theo chính sách; báo cáo giới hạn | 3 |
| R-15 | Không đủ dữ liệu để nói về bảo trì dự đoán | C | T | 🟢 | Chỉ có vài giờ dữ liệu | Theo FR-HLT-07: chỉ dùng baseline + ngưỡng + phát hiện bất thường; ghi rõ đường nâng cấp | 5 |
| R-16 | Cảm biến sức khỏe (rung/dòng/nhiệt) chưa có | TB | T | 🟢 | Không lắp được Phase 5 | Bắt đầu bằng cảm biến có sẵn; kiến trúc bật/tắt từng cảm biến qua config; đề xuất mua sau (rẻ) | 5 |
| R-17 | Timing S1→S2 không đủ biên khi tăng tốc | TB | TB | 🟡 | `margin_ms` nhỏ hoặc âm | Giữ tốc độ thấp + khoảng S1–S2 đủ dài; nếu cần: encoder (ADR-0005 phương án C) hoặc dừng-rồi-chụp (phương án D) | 1 |
| R-18 | Chốt lỗi làm demo khó (phải reset nhiều lần) | TB | T | 🟢 | Mất thời gian khi demo | Có nút RESET tại chỗ; quy trình recovery rõ; không nới lỏng an toàn để demo mượt | 1+ |
| R-19 | Tài liệu tụt lại so với code | TB | TB | 🟡 | Contract lệch với code | Test đồng bộ registry ↔ docs (MT-01 ✅); checklist review yêu cầu cập nhật tài liệu | mọi phase |
| R-20 | Chi phí vượt dự kiến do mua lẻ nhiều lần | TB | T | 🟢 | Nhiều đơn nhỏ, phí ship cộng dồn | Gom đơn theo phase; BOM đánh dấu REQUIRED/OPTIONAL/FUTURE; PO duyệt trước khi mua | mọi phase |

## Rủi ro mới do baseline phần cứng = NONE (cập nhật 2026-09-18)

| ID | Rủi ro | XS | TĐ | Mức | Dấu hiệu sớm | Biện pháp / Kế hoạch dự phòng | Phase |
|---|---|:-:|:-:|:-:|---|---|---|
| R-21 | **Software viết theo giả định sai về phần cứng** → phải sửa nhiều khi hàng về | TB | C | 🔴 | Interface thay đổi liên tục trong P1.1–P1.7 | Chốt [HARDWARE_INTERFACE.md](HARDWARE_INTERFACE.md) **trước** khi code (P1.8 đã xong); HAL 3 lớp (esp32 / host mock / simulator); simulator mô phỏng cả trường hợp xấu (cảm biến rung, trễ, mất gói) | 1 |
| R-22 | **Thời gian giao hàng làm trễ Phase 1** | C | TB | 🔴 | Đặt hàng xong mà 1–2 tuần chưa nhận | Mua theo wave, đặt W1 ngay khi AC-SW-07 đạt; trong lúc chờ vẫn làm P1.3 và P1.5; ưu tiên shop nội địa có sẵn hàng | 1 |
| R-23 | **Mua sai linh kiện** (E-stop loại NO, relay kích mức thấp, cáp USB chỉ sạc, động cơ không hộp số) | C | TB | 🔴 | Hàng về không đúng hành vi mong đợi | Min spec ghi rõ trong Master BOM; **checklist kiểm tra hàng về (Master BOM mục 18)** làm ngay khi nhận; giữ hóa đơn để đổi | 1 |
| R-24 | **Mô hình huấn luyện trên ảnh tổng hợp không dùng được với ảnh thật** | C | TB | 🟡 | Accuracy synthetic cao, ảnh thật kém | Không dùng số liệu synthetic cho acceptance (D-026); huấn luyện lại ở P1.11 với dataset thật theo DATASET_SPEC | 1 |
| R-25 | **Chi phí vượt dự kiến do mua lẻ nhiều lần** (phí ship cộng dồn) | TB | TB | 🟡 | Nhiều đơn nhỏ trong cùng tuần | Gom theo wave; so giá 2–3 shop; ưu tiên phương án giá thấp; PO duyệt từng wave | mọi phase |
| R-26 | **Không có dụng cụ đo → không kiểm chứng được an toàn** | TB | C | 🔴 | Không đo được E-stop/điện áp trước khi cấp nguồn | **Đồng hồ vạn năng nằm trong wave W1 và là REQUIRED**; nếu chưa có thì **không** cấp nguồn động cơ (quy tắc cứng) | 1 |
| R-27 | **`torch.cuda.is_available()` = False dù có RTX 3050** (phát hiện 2026-09-18 khi cài môi trường P1.3) | TB | TB | 🟡 | Huấn luyện chạy CPU, chậm hơn dự kiến trong ADR-0002 | P1.3 chỉ chạy smoke-test rất nhỏ trên CPU (không cần GPU); trước P1.11 (huấn luyện thật), PO cài lại `torch` bản CUDA khớp driver 610.78 theo hướng dẫn chính thức của PyTorch | 3, 11 |
| **R-28** | **`ClassicCvBaseline` (khoảng cách tới template trung bình) gần như không phân biệt được GOOD/DEFECT trên dữ liệu tổng hợp mặc định** — phát hiện 2026-09-18 khi nối pipeline end-to-end (đo thực nghiệm: điểm GOOD ≈ 21,9, điểm DEFECT ≈ 21,9–23,2, gần như trùng nhau) | C | TB | 🟡 | Bất kỳ pipeline nào dùng baseline này với dataset thật đều có thể phân loại kém nếu vị trí sản phẩm không được cố định cơ khí tốt | Nguyên nhân đã xác định: độ lệch vị trí ngẫu nhiên khi lấy trung bình nhiều ảnh mẫu làm mờ template + nhiễu nền lớn hơn tín hiệu lỗi. Trước P1.11: (a) cố định vị trí sản phẩm bằng cơ khí (khớp đúng khuyến nghị DATASET_SPEC về giá đỡ camera), và/hoặc (b) cải tiến baseline để bền với lệch vị trí (căn tâm trước khi so sánh), và/hoặc (c) chuyển sang CNN (khi có dataset thật) vốn ít nhạy hơn với lệch vị trí nhỏ. Không dùng ngưỡng hiện tại (đã hiệu chỉnh trên dữ liệu tổng hợp) cho dữ liệu thật mà không hiệu chỉnh lại | 1 (baseline), 11 (dataset thật) |

## Rủi ro cần xử lý trước khi vào Phase 1

R-01, R-02, R-04, R-05, R-07, R-21, R-22, R-23, R-26 (🔴). Biện pháp tương ứng đã được đưa vào [PHASE1_PLAN.md](PHASE1_PLAN.md) như task hoặc điều kiện tiên quyết.
