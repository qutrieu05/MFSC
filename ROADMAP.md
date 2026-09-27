# Roadmap — MSFC

**Giả định:** 1 người, 10–15 giờ/tuần. Thời lượng là **ước tính**, không phải cam kết.
**Quy tắc:** không sang phase mới khi phase trước chưa đạt acceptance criteria, hoặc chưa có lý do kỹ thuật ghi trong [DECISIONS.md](DECISIONS.md). **Mỗi phase cần PO duyệt để bắt đầu.**

| Phase | Tên | Mục tiêu chính | Deliverable | Acceptance | Ước tính | Trạng thái |
|---|---|---|---|---|---|---|
| **0** | Project Foundation | Nền tảng tài liệu + kỹ thuật để không phải làm lại | Charter, Requirements, Architecture, Safety Concept, MQTT contract v0.1, 13 ADR, config + logging + test, BOM, Risk Register, Roadmap, TASKS | Test Phase 0 pass; tài liệu đủ; **PO duyệt** | 1–2 tuần | ✅ hoàn thành phần Claude Inc, **chờ PO duyệt** |
| **1** | Conveyor + Basic Vision Control | Băng tải chạy, vision phân loại, ESP32 gạt đúng sản phẩm, an toàn cơ bản, đo thời gian | Firmware cell_controller, `msfc.contracts/comm/vision/decision/services/sim/cli`, dataset + model v1, WIRING_GUIDE, TEST_REPORT Phase 1 | [AC-P1-01..11](docs/PHASE1_PLAN.md#5-acceptance-criteria-của-phase-1) | 5–7 tuần | 📋 kế hoạch xong |
| **2** | Safety System (V14) | Vùng nguy hiểm, phát hiện người, safe state, đo độ trễ dừng | `msfc.safety_vision`, heartbeat an toàn, cấu hình vùng, test ST-07..12 | ST-07..12 pass; PT-03 đo được; FP/FN có số liệu; che chắn cơ khí xong | 3–4 tuần | ⏳ |
| **3** | OCR (V04) | Đọc nhãn/hạn dùng, hợp nhất vào quyết định | `msfc.ocr`, bộ test 7 điều kiện, mã lý do | VT-05, FT-08; báo cáo accuracy + thời gian xử lý + trường hợp lỗi | 3–4 tuần | ⏳ |
| **4** | OEE (V07) | Trạng thái máy, đếm, downtime, A/P/Q/OEE + dashboard | `msfc.analytics`, `msfc.storage` (SQLite), dashboard v1, ADR chọn công nghệ dashboard | Kiểm chứng OEE bằng dữ liệu có đáp án tay; dashboard hiển thị đủ 6 mục | 3–4 tuần | ⏳ |
| **5** | Machine Health (V09) | Rung/nhiệt/dòng, baseline, ngưỡng, phát hiện bất thường | Health node firmware hoặc mở rộng N1, `msfc.analytics.health`, quy trình baseline | NORMAL/WARNING/CRITICAL hoạt động; FT-06; **không tuyên bố quá năng lực** (FR-HLT-07) | 4–6 tuần | ⏳ |
| **6** | Edge AI Platform (V01) | Quản lý mô hình, phiên bản, ngưỡng, số liệu; dashboard tổng hợp | Model registry, cơ chế cập nhật + rollback, dashboard 8 mục | FR-AIP-01/02, FR-DSH-02; so sánh hiệu năng giữa các phiên bản mô hình | 4–6 tuần | ⏳ |
| **7** | Integration & Release | Demo 20 bước, hardening, bàn giao | 20 deliverable cuối (installation guide, user manual, troubleshooting, benchmark, demo procedure), tag `v1.0.0` | ACC-01..20 + LT-02 (8 giờ) | 3–4 tuần | ⏳ |

**Tổng ước tính:** ≈ **26–37 tuần** làm việc thực tế (không tính thời gian chờ mua/vận chuyển và thời gian PO học toolchain).

> Phase 7 là **đề xuất thêm** của Claude Inc so với danh sách phase gốc của PO (gốc có Phase 0–6): cần một phase riêng để tích hợp, hardening và bàn giao 20 deliverable. PO có thể gộp Phase 7 vào Phase 6 nếu muốn.

## Đường găng

```
PO duyệt Phase 0
   └─► B2 (xác nhận phần cứng) + B4 (cài toolchain)
          └─► Phase 1 M1.1 (laptop) ──┐
          └─► Phase 1 M1.2 (bàn thử) ─┤
                  M1.3 (cơ khí, PO làm tay) ─► M1.4 (dataset) ─► M1.5 (tích hợp) ─► Phase 2 …
```

Các phase sau chủ yếu **cộng thêm module** vào cùng một kiến trúc, nên rủi ro tích hợp giảm dần nếu Phase 1 làm chắc.

## Quy tắc thay đổi roadmap

1. Thêm/bớt phạm vi → ghi vào DECISIONS.md kèm lý do và ảnh hưởng tới thời lượng.
2. Tính năng ngoài S1 → **FUTURE/OPTIONAL**, không làm ngay (chống rủi ro R-07).
3. Nếu một phase vượt 1,5× ước tính → review lại phạm vi với PO thay vì kéo dài vô hạn.
