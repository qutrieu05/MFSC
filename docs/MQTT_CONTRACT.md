# MQTT Communication Contract — MSFC

**Contract version:** `0.1.0` (DRAFT — chờ PO duyệt) · **Ngày:** 2026-09-17

**Nguồn sự thật (machine-readable):**
- Topic: [`contracts/mqtt/topics.toml`](../contracts/mqtt/topics.toml)
- Payload schema: [`contracts/schemas/`](../contracts/schemas/) (JSON Schema 2020-12)

Tài liệu này giải thích quy tắc. **Nếu tài liệu và registry mâu thuẫn, registry thắng**; mâu thuẫn được coi là lỗi cần sửa. Test `edge/tests/contract/` kiểm tra tính nhất quán của registry và schema.

---

## 1. Ngữ pháp topic

```
factory/{line_id}/{subsystem}/{device_id}/{class}[/{name}]
```

| Thành phần | Quy tắc | Giá trị v0.1 |
|---|---|---|
| `factory` | Gốc cố định | `factory` |
| `line_id` | `[a-z0-9]+` | `line01` |
| `subsystem` | Tập cố định | `conveyor`, `system`, `vision`, `decision`, `safety`, `ocr`, `oee`, `health` |
| `device_id` | `[a-z0-9-]{3,32}` | `esp32-cc01`, `edge01`, `cam01`, `safecam01`, `ocr01`, `oee01`, `esp32-hn01` |
| `class` | Tập cố định | `status`, `state`, `heartbeat`, `event`, `telemetry`, `cmd`, `ack`, `fault` |
| `name` | `[a-z0-9_]+` | ví dụ `product_detected`, `verdict` |

**Quy tắc cho lệnh:** `cmd` nằm **dưới thiết bị nhận lệnh**. Ví dụ Decision Engine gửi verdict tới `factory/line01/conveyor/esp32-cc01/cmd/verdict`.

**Wildcard gợi ý cho bên nhận:**
- `factory/line01/conveyor/+/event/#`
- `factory/+/+/+/fault`

## 2. Envelope chung (`envelope.v1`)

Mọi payload là JSON UTF-8 dạng envelope:

```json
{
  "schema": "product_detected.v1",
  "device_id": "esp32-cc01",
  "boot_id": 7,
  "seq": 1532,
  "mono_ms": 845210,
  "data": { "product_id": "7-42", "sensor": "S1", "t_detect_mono_ms": 845198 }
}
```

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `schema` | ✅ | Tên schema của `data`, dạng `<tên>.v<số>` |
| `device_id` | ✅ | Thiết bị gửi |
| `boot_id` | Thiết bị embedded | Tăng mỗi lần khởi động (lưu NVS) |
| `seq` | ✅ | Bộ đếm tăng dần theo thiết bị. **Heartbeat an toàn phải tăng**, nếu không bị coi là cũ |
| `mono_ms` | ✅ | Đồng hồ đơn điệu của bên gửi (ms) |
| `ts` | Tùy chọn | Giờ UTC ISO 8601 khi bên gửi có đồng bộ giờ |
| `data` | ✅ | Nội dung theo schema |

**Giới hạn:**
- Payload từ ESP32 ≤ 1024 byte.
- Không dùng `NaN`/`Infinity`.
- Số thời gian là số nguyên ms.

## 3. Chính sách QoS và retain

| Class | QoS | Retain | Lý do |
|---|---|---|---|
| `status` | 1 | ✅ | Trạng thái online/offline mới nhất; dùng **Last Will** |
| `state` | 1 | ✅ | Người đăng ký mới nhận ngay trạng thái hiện tại. Luôn đọc kèm `status` để biết dữ liệu có còn "sống" |
| `heartbeat` | 0 | ❌ | Chỉ giá trị mới có ý nghĩa; mất gói được xử lý bằng timeout |
| `event` | 1 | ❌ | Mỗi sự kiện nên tới ít nhất một lần; bên nhận **phải chống trùng** theo (`device_id`, `boot_id`, `seq`) |
| `telemetry` | 0 | ❌ | Dữ liệu định kỳ, mất một mẫu chấp nhận được |
| `cmd` | 1 | ❌ | **Không bao giờ retain lệnh** (tránh thực thi lệnh cũ khi kết nối lại) |
| `ack` | 1 | ❌ | Trả lời lệnh |
| `fault` | 1 | ❌ | Sự kiện lỗi; trạng thái lỗi hiện tại nằm trong `state.active_faults` |

## 4. Danh mục topic v0.1

> Rút gọn từ registry. Cột "An toàn" đánh dấu kênh mà **sự vắng mặt** kích hoạt safe state.

| Key | Topic (dưới `factory/{line_id}/`) | Pub → Sub | QoS / Retain | Schema | Tần suất | An toàn | Phase |
|---|---|---|---|---|---|---|---|
| conveyor.status | `conveyor/{dev}/status` | CC → ES | 1 / ✅ | device_status.v1 | LWT | | 1 |
| conveyor.state | `conveyor/{dev}/state` | CC → ES, DB | 1 / ✅ | cell_state.v1 | thay đổi + 5 s | | 1 |
| conveyor.heartbeat | `conveyor/{dev}/heartbeat` | CC → ES | 0 / ❌ | device_heartbeat.v1 | 1 Hz | | 1 |
| conveyor.event.product_detected | `conveyor/{dev}/event/product_detected` | CC → ES | 1 / ❌ | product_detected.v1 | mỗi sản phẩm | | 1 |
| conveyor.event.product_sorted | `conveyor/{dev}/event/product_sorted` | CC → ES | 1 / ❌ | product_sorted.v1 | mỗi sản phẩm | | 1 |
| conveyor.event.state_changed | `conveyor/{dev}/event/state_changed` | CC → ES | 1 / ❌ | state_changed.v1 | thay đổi | | 1 |
| conveyor.fault | `conveyor/{dev}/fault` | CC → ES | 1 / ❌ | fault.v1 | raise/clear | | 1 |
| conveyor.telemetry.timing | `conveyor/{dev}/telemetry/timing` | CC → ES | 0 / ❌ | timing_stats.v1 | 10 s | | 1 |
| conveyor.cmd.verdict | `conveyor/{dev}/cmd/verdict` | ES → CC | 1 / ❌ | verdict_cmd.v1 | mỗi sản phẩm | | 1 |
| conveyor.cmd.control | `conveyor/{dev}/cmd/control` | ES → CC | 1 / ❌ | control_cmd.v1 | theo thao tác | | 1 |
| conveyor.ack | `conveyor/{dev}/ack` | CC → ES | 1 / ❌ | cmd_ack.v1 | mỗi lệnh | | 1 |
| system.status | `system/{dev}/status` | ES → CC, DB | 1 / ✅ | device_status.v1 | LWT | | 1 |
| **system.heartbeat** | `system/{dev}/heartbeat` | ES → CC | 0 / ❌ | edge_heartbeat.v1 | **5 Hz** | **SF-02** | 1 |
| system.event.service_state | `system/{dev}/event/service_state` | ES → DB | 1 / ❌ | service_state.v1 | thay đổi | | 1 |
| vision.status | `vision/{dev}/status` | ES → DB | 1 / ✅ | device_status.v1 | thay đổi | | 1 |
| vision.event.inspection_result | `vision/{dev}/event/inspection_result` | ES → ES, DB | 1 / ❌ | inspection_result.v1 | mỗi sản phẩm | | 1 |
| vision.telemetry.perf | `vision/{dev}/telemetry/perf` | ES → DB | 0 / ❌ | vision_perf.v1 | 5 s | | 1 |
| decision.event.decision_record | `decision/{dev}/event/decision_record` | ES → DB | 1 / ❌ | decision_record.v1 | mỗi sản phẩm | | 1 |
| safety.status | `safety/{dev}/status` | ES → DB | 1 / ✅ | device_status.v1 | thay đổi | | 2 |
| **safety.heartbeat** | `safety/{dev}/heartbeat` | ES → CC | 0 / ❌ | safety_heartbeat.v1 | **≥ 5 Hz** | **SF-03/04** | 2 |
| safety.event.intrusion | `safety/{dev}/event/intrusion` | ES → DB | 1 / ❌ | intrusion_event.v1 | vào/ra | | 2 |
| ocr.event.label_result *(draft)* | `ocr/{dev}/event/label_result` | ES → ES, DB | 1 / ❌ | label_result.v1 | mỗi sản phẩm | | 3 |
| oee.state.metrics *(draft)* | `oee/{dev}/state` | ES → DB | 1 / ✅ | oee_metrics.v1 | 10 s | | 4 |
| health.telemetry.features *(draft)* | `health/{dev}/telemetry/features` | HN → ES | 0 / ❌ | health_features.v1 | 1 s | | 5 |
| health.state *(draft)* | `health/{dev}/state` | ES → DB | 1 / ✅ | health_state.v1 | thay đổi | | 5 |

*CC = Cell Controller (ESP32) · ES = Edge Server · DB = Dashboard · HN = Health Node*

## 5. Ngữ nghĩa lệnh và phản hồi

1. Bên gửi tạo `cmd_id` duy nhất, publish `cmd/control` (QoS 1).
2. Cell Controller **luôn** trả `ack`: `ACCEPTED` (bắt đầu thực hiện), `DONE`, `REJECTED` (kèm `reason`) hoặc `FAILED`.
3. Bên gửi chờ `ack` tối đa `comm.command_ack_timeout_ms` (mặc định 2000). Không nhận được thì báo lỗi, **không tự gửi lại lệnh `start`**.
4. Cell Controller bỏ qua `cmd_id` trùng (chống trùng do QoS 1 gửi lại).

**Lý do từ chối chuẩn:** `estop_latched`, `fault_latched`, `safe_stop_latched`, `not_idle`, `not_running`, `cause_not_cleared`, `remote_reset_forbidden`, `invalid_params`, `safety_vision_unavailable`, `edge_heartbeat_missing`.

**Verdict (`cmd/verdict`)** không có `ack` riêng. Kết quả thực tế nằm trong `event/product_sorted` (`verdict_received`, `reason`). Verdict cho `product_id` không còn trong hàng đợi bị bỏ và tính `DECISION_LATE`.

## 6. Heartbeat và phát hiện mất kết nối

| Kênh | Bên giám sát | Timeout (config) | Phản ứng |
|---|---|---|---|
| `system.heartbeat` | Cell Controller | `comm.heartbeat_timeout_ms` = 1000 | `FAULT(F010)` khi đang chạy; chặn START khi IDLE |
| `safety.heartbeat` | Cell Controller | `safety.vision_stale_ms` = 600 + kiểm tra `frame_seq` tăng | `SAFE_STOP(F021)` |
| `conveyor.heartbeat` | Edge Server | `edge.device_timeout_ms` = 3000 | Đánh dấu thiết bị offline trên dashboard, ghi log |
| Last Will (`status`) | Mọi bên | Theo keepalive của broker | `online=false` được retain |

## 7. Trạng thái lỗi trong contract

- **Payload không hợp lệ** (JSON sai, thiếu trường, sai schema): bên nhận loại bỏ, ghi log `E101 PAYLOAD_INVALID` kèm topic và lý do, **không crash**.
- **Schema version không hỗ trợ:** loại bỏ, ghi `E102 SCHEMA_UNSUPPORTED`.
- **Topic không có trong registry:** bỏ qua, ghi `E103 TOPIC_UNKNOWN` (mức DEBUG để tránh spam).
- **Lỗi phía thiết bị:** publish `fault` và cập nhật `state.active_faults`.

## 8. Quy tắc phiên bản

| Loại thay đổi | Cách xử lý |
|---|---|
| Thêm trường tùy chọn | Giữ `.v1`, tăng patch của `contract_version` |
| Thêm topic mới | Tăng minor của `contract_version` |
| Đổi tên/xóa trường, đổi kiểu, đổi nghĩa | Tạo schema `.v2`, tăng major của `contract_version`, ghi ADR |
| Đổi ngữ pháp topic | Major + ADR + migration plan |

## 9. Bảo mật

- Broker yêu cầu username/password riêng cho từng vai trò (`cell_controller`, `edge_server`, `dashboard`).
- Chỉ lắng nghe trong LAN; **không** mở port ra Internet.
- ACL (Phase 1 hoặc muộn hơn): Cell Controller chỉ được publish dưới `conveyor/esp32-cc01/*` và chỉ subscribe `cmd/*`, `system/+/heartbeat`, `safety/+/heartbeat`.
- Thông tin đăng nhập nằm trong `config/site.toml` (gitignored) và NVS của ESP32, **không đưa vào git**.
- TLS: FUTURE (ESP32 hỗ trợ nhưng tăng độ trễ/bộ nhớ; đánh giá sau khi đo Phase 1).

## 10. Ví dụ payload

**Verdict:**

```json
{"schema":"verdict_cmd.v1","device_id":"edge01","seq":88,"mono_ms":1203344,
 "data":{"product_id":"7-42","verdict":"DEFECT","decision_id":"d-7-42","reason_codes":["VISION_DEFECT"],"confidence":0.93}}
```

**Sản phẩm đã phân loại:**

```json
{"schema":"product_sorted.v1","device_id":"esp32-cc01","boot_id":7,"seq":1540,"mono_ms":848400,
 "data":{"product_id":"7-42","action":"REJECTED","reason":"VERDICT_DEFECT","verdict_received":true,
         "t_detect_mono_ms":845198,"t_verdict_rx_mono_ms":845391,"t_s2_mono_ms":848310,
         "t_push_mono_ms":848390,"latency_detect_to_verdict_ms":193,"margin_ms":2919}}
```

**Heartbeat an toàn (Phase 2):**

```json
{"schema":"safety_heartbeat.v1","device_id":"safecam01","seq":50211,"mono_ms":990120,
 "data":{"zone_clear":true,"detector_ok":true,"frame_seq":49870,"frame_age_ms":41,"persons_in_zone":0}}
```
