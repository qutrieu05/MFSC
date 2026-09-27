# Project Charter — Mini Smart Factory Cell (MSFC)

**Tên đầy đủ:** Mini Smart Factory Cell — Edge AI Vision Controlled Manufacturing System
**Mã hệ thống tham chiếu:** S1 = V01 + V03 + V04 + V07 + V09 + V14
**Phiên bản charter:** 0.1 (DRAFT — chờ Project Owner duyệt)
**Ngày:** 2026-09-17

---

## 1. Mục đích

Xây dựng **một dây chuyền sản xuất thu nhỏ** mà trong đó **Embedded Firmware** và **Edge AI / Computer Vision** là hai thành phần cốt lõi.

- Sản phẩm chạy trên băng tải và được kiểm tra ngoại quan cùng nhãn hạn sử dụng.
- Sản phẩm lỗi bị gạt ra bằng actuator do ESP32 điều khiển.
- Hệ thống tính OEE, theo dõi sức khỏe động cơ và giám sát vùng nguy hiểm.
- Toàn bộ dữ liệu về Edge Server qua MQTT và hiển thị trên dashboard.

Đây là **project học tập và portfolio cá nhân**, không phải sản phẩm thương mại hay thiết bị an toàn đạt chuẩn.

## 2. Vai trò và quyền hạn

| Vai trò | Người/Đơn vị | Quyền hạn / Trách nhiệm |
|---|---|---|
| **Project Owner (PO)** | Sinh viên IUH (chủ dự án) | Quyết định cuối cùng về scope, architecture, mua phần cứng, feature, release. Thực hiện mọi thao tác phần cứng vật lý (đấu dây, lắp ráp, cấp nguồn, đo đạc) |
| **Claude Inc (CEO + CTO + các vai trò kỹ thuật)** | Assistant | Research, system engineering, kiến trúc phần mềm/firmware, AI/CV, backend, MQTT, dashboard, test, tài liệu, review code, quản lý dự án, lập kế hoạch tích hợp |

**Giới hạn cần biết:** các "vai trò" của Claude Inc là các lượt phân tích do **cùng một assistant** thực hiện. Đây **không phải review độc lập của nhiều người**. Claude Inc **không** thể kiểm chứng phần cứng vật lý; mọi trạng thái phần cứng chỉ được ghi nhận là "đã kiểm chứng" khi có bằng chứng do PO cung cấp (log, số đo, ảnh, video).

## 3. Mục tiêu (Objectives)

| ID | Mục tiêu | Đo bằng |
|---|---|---|
| OBJ-1 | Dây chuyền kiểm tra và gạt sản phẩm lỗi tự động bằng Edge AI | Tỷ lệ phân loại/gạt đúng, độ trễ đo được (Phase 1, 3) |
| OBJ-2 | Chức năng an toàn chạy ở tầng embedded, **không phụ thuộc** laptop/MQTT/AI | Test mất kết nối, test xâm nhập vùng, thời gian dừng (Phase 1, 2) |
| OBJ-3 | Dữ liệu sản xuất, OEE, sức khỏe động cơ và sự kiện được thu thập và hiển thị | Dashboard + cơ sở dữ liệu (Phase 4, 5) |
| OBJ-4 | Nền tảng Edge AI có quản lý mô hình, phiên bản, cấu hình, số liệu hiệu năng | Phase 6 |
| OBJ-5 | Tài liệu và test đủ để người khác cài đặt, chạy lại và hiểu hệ thống | 20 deliverable cuối |

## 4. Phạm vi

### 4.1 Trong phạm vi (S1)

1. Băng tải, phát hiện sản phẩm, gạt sản phẩm lỗi (V03).
2. Kiểm tra ngoại quan GOOD/DEFECT bằng Edge AI.
3. OCR hạn sử dụng/nhãn (V04).
4. Trạng thái máy, đếm sản phẩm, OEE (V07).
5. Sức khỏe động cơ băng tải: rung, nhiệt, dòng (V09), bắt đầu bằng baseline + phát hiện bất thường.
6. Giám sát vùng nguy hiểm và đưa máy về trạng thái an toàn (V14).
7. MQTT, Edge Server, cơ sở dữ liệu, dashboard, logging, cấu hình, chẩn đoán.
8. Chuẩn hóa pipeline AI / camera node (V01).

### 4.2 Ngoài phạm vi (đưa vào FUTURE nếu cần)

- Cloud, tài khoản người dùng nhiều vai trò, truy cập Internet từ xa.
- Thiết bị an toàn đạt chuẩn (ISO 13849/IEC 62061), chứng nhận EMC.
- Điện lưới 220 V cho actuator hoặc động cơ (S1 chỉ dùng **điện áp thấp DC ≤ 12 V**).
- Robot gắp, robot tự hành, board PCB tự thiết kế.
- "Predictive maintenance AI" dự báo thời gian sống còn lại khi chưa có dữ liệu suy giảm dài hạn.

## 5. Ràng buộc

| ID | Ràng buộc |
|---|---|
| CON-01 | Một người phát triển (solo) |
| CON-02 | Ngân sách thấp; **không mua phần cứng khi chưa có PO duyệt**; ưu tiên tận dụng thiết bị có sẵn |
| CON-03 | Suy luận AI chạy local/edge; **không phụ thuộc cloud** cho quyết định thời gian thực |
| CON-04 | Tầng embedded phải tự đưa hệ thống về trạng thái an toàn khi mất kết nối với laptop/MQTT/AI |
| CON-05 | Máy phát triển: Windows 11, i5-12450H, RAM 15,7 GB, RTX 3050 Laptop 4 GB VRAM |
| CON-06 | Không thêm dependency khi không cần; không thay đổi kiến trúc tùy tiện |
| CON-07 | Chỉ dùng điện áp thấp DC (≤ 12 V) cho động cơ, servo và actuator trong S1 |

## 6. Tiêu chí hoàn thành cuối cùng (tóm tắt)

S1 chỉ **COMPLETE** khi demo được **workflow 20 bước** thống nhất: power on → self-check → camera → băng tải → vision → OCR → decision → actuator → thống kê → OEE → sức khỏe động cơ → vùng an toàn → safe state → MQTT → dashboard → fault logging → recovery.

Chi tiết và cách kiểm chứng: [REQUIREMENTS.md](REQUIREMENTS.md) (mục ACC) và [ROADMAP.md](../ROADMAP.md).

## 7. Quy trình làm việc

- Mỗi phase đi theo: DISCOVER → REQUIREMENTS → ARCHITECTURE → PLAN → BUILD → TEST → REVIEW → INTEGRATE → DOCUMENT → RELEASE.
- **Không chuyển phase** khi phase trước chưa đạt acceptance criteria (hoặc chưa có lý do kỹ thuật được ghi trong [DECISIONS.md](../DECISIONS.md)).
- **Mỗi phase cần PO approve trước khi bắt đầu.**
- Khi cần thao tác phần cứng, Claude Inc dừng lại và cung cấp: kết nối, pin mapping, đấu dây, cảnh báo an toàn, quy trình test, kết quả mong đợi.

## 8. Giả định cần xác nhận

Xem [HARDWARE_INVENTORY.md](HARDWARE_INVENTORY.md). Các thiết bị PO liệt kê (ESP32, camera, motor, servo, cảm biến, LED, LCD, Raspberry Pi, Jetson Nano) **chưa được xác nhận model cụ thể**, và audit máy tính ngày 2026-09-17 **không phát hiện camera nào đang kết nối**.

## 9. Phê duyệt

| Mục | Trạng thái |
|---|---|
| Charter v0.1 | ⏳ Chờ PO duyệt |
