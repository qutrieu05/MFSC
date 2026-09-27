# ADR-0004: MQTT contract, broker và định dạng payload

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

Yêu cầu:
- Thu thập dữ liệu toàn hệ thống qua MQTT.
- Không hard-code topic.
- Có contract ghi rõ topic, publisher, subscriber, payload, QoS, retain, timestamp, device ID, schema, error state.

## Các phương án

**Broker:**

| Phương án | Chi phí | Độ phức tạp | Độ tin cậy |
|---|---|---|---|
| **Mosquitto 2.x trên laptop** | Miễn phí | Thấp | Cao, phổ biến, nhẹ |
| EMQX | Miễn phí | Trung bình (nặng hơn) | Cao |
| Broker Python nhúng (amqtt) | Miễn phí | Thấp | Kém phổ biến, rủi ro bảo trì |

**Payload:** JSON (dễ debug, cJSON có sẵn trong ESP-IDF) · CBOR/Protobuf (gọn hơn nhưng khó debug).

**Nguồn sự thật topic:** tài liệu Markdown (dễ lệch) · **registry TOML + JSON Schema** (máy đọc được, test được, sinh header cho firmware).

## Quyết định

- **Mosquitto 2.x**, MQTT **3.1.1**, bắt buộc xác thực, chỉ trong LAN.
- **JSON** với envelope chung.
- **Registry `contracts/mqtt/topics.toml` + `contracts/schemas/*.json`** là nguồn sự thật; `docs/MQTT_CONTRACT.md` giải thích.
- Firmware dùng header sinh tự động từ registry (công cụ ở Phase 1).

## Hệ quả

- PO cần cài Mosquitto (miễn phí) trước Phase 1 tích hợp.
- Kiểm tra payload ở Edge Server cần thư viện JSON Schema. **Đề xuất thêm dependency `jsonschema` ở Phase 1** (sẽ ghi lý do khi thêm).
- Thay đổi contract theo quy tắc phiên bản (MQTT_CONTRACT mục 8).
