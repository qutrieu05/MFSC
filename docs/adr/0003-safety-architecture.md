# ADR-0003: Kiến trúc an toàn tầng embedded

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Nguyên tắc bắt buộc của PO: camera/AI/MQTT/dashboard **không được là điểm lỗi đơn** cho chức năng an toàn. Mất kết nối thì động cơ và actuator phải về trạng thái an toàn, ghi lỗi, và có reset có kiểm soát.

## Các phương án

| Phương án | Chi phí | Độ phức tạp | Độ tin cậy an toàn |
|---|---|---|---|
| A. Dừng bằng lệnh MQTT từ laptop | 0 | Thấp | **Không chấp nhận**: mất mạng thì không dừng được |
| B. **E-stop cứng ngắt nguồn động cơ + ESP32 fail-safe theo heartbeat + chốt lỗi + reset có kiểm soát** | ~30–70k (nút E-stop) + relay có sẵn | Trung bình | Tốt cho prototype: mất bất kỳ tín hiệu nào → dừng |
| C. B + MCU an toàn thứ hai / module safety relay | Cao hơn | Cao | Tốt hơn (dự phòng kênh), vượt nhu cầu S1 |

## Quyết định

**Chọn B.** Chi tiết trong [SAFETY_CONCEPT.md](../SAFETY_CONCEPT.md):
- E-stop NC nối tiếp nguồn động cơ (kênh phần cứng) và được ESP32 đọc.
- ESP32 dừng khi mất heartbeat Edge Server (1000 ms) hoặc heartbeat safety vision (600 ms, Phase 2), hoặc khi `zone_clear=false`.
- Lỗi được chốt; `ESTOP` chỉ reset tại chỗ; không tự khởi động lại.
- Logic an toàn đánh giá trước logic sản xuất; động cơ và relay mặc định tắt.

**Phương án C** ghi vào FUTURE.

## Hệ quả

- Wi-Fi chập chờn có thể gây **dừng không mong muốn**. Phase 1 phải đo tỷ lệ mất heartbeat và chỉnh timeout trong giới hạn (300–3000 ms), mọi thay đổi ghi lại.
- Luôn phải ghi rõ: đây **không phải** hệ thống an toàn đạt chuẩn.
