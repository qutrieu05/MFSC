# Mini Smart Factory Cell (MSFC)

**Edge AI Vision Controlled Manufacturing System** — một dây chuyền sản xuất thu nhỏ trong đó **Embedded Firmware** và **Edge AI / Computer Vision** là hai thành phần cốt lõi.

> ⚠️ **Prototype học tập, điện áp thấp (DC ≤ 12 V).** Các chức năng an toàn được thiết kế theo nguyên tắc fail-safe nhưng **không** được chứng nhận theo ISO 13849/IEC 62061. Giám sát vùng nguy hiểm bằng camera là **lớp bổ sung**, không thay thế che chắn cơ khí và nút dừng khẩn. Không dùng cho máy móc thật có người vận hành. Xem [docs/SAFETY_CONCEPT.md](docs/SAFETY_CONCEPT.md).

**Trạng thái:** **P1–P6 (Core S1 Software Platform) = SOFTWARE COMPLETE** + **Official Web Dashboard = COMPLETE** (giao diện người dùng chính thức, chạy trên mô phỏng — xem [OFFICIAL_DASHBOARD_ARCHITECTURE.md](OFFICIAL_DASHBOARD_ARCHITECTURE.md), [OFFICIAL_DASHBOARD_USER_GUIDE.md](OFFICIAL_DASHBOARD_USER_GUIDE.md)). **Hardware Integration** và **Real-world Validation** vẫn là giai đoạn tương lai, chưa bắt đầu — **chờ Project Owner duyệt** bước tiếp theo. Chi tiết: [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## Hệ thống làm gì (khi hoàn thành S1)

```
Sản phẩm trên băng tải → camera kiểm tra ngoại quan → OCR kiểm tra nhãn/hạn dùng
   → decision engine (GOOD/DEFECT) → ESP32 gạt sản phẩm lỗi
   → tính OEE · theo dõi sức khỏe động cơ · giám sát vùng nguy hiểm → dừng an toàn
   → dữ liệu qua MQTT về Edge Server → dashboard giám sát
```

## Kiến trúc rút gọn

| Node | Phần cứng | Vai trò |
|---|---|---|
| **Cell Controller** | ESP32 | An toàn (L0), firmware điều khiển (L2), cảm biến/actuator (L1) |
| **Edge Server** | Laptop Windows + RTX 3050 | Vision/OCR/safety vision (L3), decision (L4), MQTT (L5), service (L6), lưu trữ (L7), dashboard (L8) |

**Nguyên tắc bất buộc:** tầng embedded **tự đưa hệ thống về trạng thái an toàn** khi mất laptop / MQTT / AI. Chi tiết: [ARCHITECTURE.md](ARCHITECTURE.md).

## Cấu trúc repo

```
docs/            charter, requirements, architecture chi tiết, safety, contract, QA, risks, ADR
contracts/       mqtt/topics.toml (nguồn sự thật topic) + schemas/*.json (payload)
config/          default.toml (commit) · site.example.toml (mẫu cho site.toml không commit)
edge/            Edge Server (Python 3.11): src/msfc/<layer>, tests/
firmware/        cell_controller (ESP32) — Phase 0 chỉ có kiến trúc module
ai/              datasets/ (manifest) · models/ (model card)
hardware/        pin mapping, wiring, ảnh lắp đặt
tools/           check_env.py và script phụ trợ
```

Tài liệu quản lý ở gốc: [PROJECT_STATUS](PROJECT_STATUS.md) · [ROADMAP](ROADMAP.md) · [TASKS](TASKS.md) · [DECISIONS](DECISIONS.md) · [TEST_REPORT](TEST_REPORT.md) · [HARDWARE_BOM](HARDWARE_BOM.md) · [ARCHITECTURE](ARCHITECTURE.md) · [CHANGELOG](CHANGELOG.md)

## Chạy thử ngay (không cần phần cứng)

```bash
python tools/check_env.py          # kiểm tra môi trường phát triển
cd edge && python -m pytest        # 859 passed, 1 skipped: toàn bộ P0-P6 + Official Dashboard
python edge/run_dashboard.py       # Official Web Dashboard tại http://127.0.0.1:8000 (mô phỏng)
```

Dependency runtime: thư viện chuẩn Python 3.11 (P0-P6) + `fastapi`/`uvicorn` (Official Dashboard, dependency đầu tiên kể từ Phase 0 — xem DECISIONS.md D-064).

## Lộ trình

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| Phase 0 | Nền tảng: charter, requirements, architecture, safety, contract, config/logging, test, BOM, roadmap, risks | ✅ DONE (PO đã duyệt) |
| Phase 1 | Băng tải + vision + gạt sản phẩm lỗi + an toàn cơ bản (software-first, mô phỏng) | ✅ DONE (PO đã duyệt) |
| Phase 2 | An toàn/Interlock (E-STOP software, comm-loss, watchdog) | ✅ DONE (PO đã duyệt) |
| Phase 3 | OCR nhãn/hạn dùng | ✅ DONE (PO đã duyệt) |
| Phase 4 | OEE / Machine Monitoring | ✅ DONE (PO đã duyệt) |
| Phase 5 | Sức khỏe động cơ / Anomaly Detection / Predictive Maintenance (mô phỏng) | ✅ DONE (PO đã duyệt) |
| Phase 6 | Edge AI Platform / Final Software Integration (`msfc.services`, hợp nhất P1-P5) | ✅ DONE (PO đã duyệt) — **FINAL SOFTWARE PHASE** |
| **Official Web Dashboard** | Giao diện web chính thức (`msfc.dashboard`) — không phải phase mới | ✅ **DONE** — chờ PO duyệt |
| Hardware Integration | ESP32 thật, camera thật, cảm biến thật, MQTT broker thật | ⏳ **Giai đoạn tương lai**, chưa bắt đầu, chưa duyệt |
| Real-world Validation | Vision AI/OCR/OEE/machine-health/predictive-maintenance trên dữ liệu thật | ⏳ **Giai đoạn tương lai**, chưa bắt đầu, chưa duyệt |

**P1–P6 = Core S1 Software Platform** (nền tảng phần mềm) · **Official Dashboard = giao diện người dùng** cho nền tảng đó · **Hardware Integration** và **Real-world Validation** là các giai đoạn tương lai, cần PO duyệt riêng.

Chi tiết: [ROADMAP.md](ROADMAP.md) · [PROJECT_STATUS.md](PROJECT_STATUS.md) · [TASKS.md](TASKS.md) · Kế hoạch Phase 1: [docs/PHASE1_PLAN.md](docs/PHASE1_PLAN.md)

## Vai trò

- **Project Owner (PO):** quyết định scope, kiến trúc, mua phần cứng, feature, release; thực hiện mọi thao tác phần cứng.
- **Claude Inc:** research, system/software/firmware engineering, AI/CV, MQTT, test, tài liệu, quản lý dự án. Không tự commit, không tự mua phần cứng, không tuyên bố phần cứng hoạt động khi chưa có bằng chứng.

## Giấy phép

Chưa chọn. PO quyết định trước khi công khai repo (ghi vào DECISIONS.md).
