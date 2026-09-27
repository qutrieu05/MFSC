# ADR-0001: Repository riêng dạng monorepo

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Bối cảnh

`D:\project` đang chứa 4 báo cáo nghiên cứu. Project cần firmware, Edge Server, AI, contract và tài liệu **thay đổi đồng bộ**: đổi một topic MQTT phải sửa cả firmware lẫn Python trong cùng một commit.

## Các phương án

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Monorepo mới `D:\project\mini-smart-factory-cell` | Contract, firmware, edge đổi nguyên tử; báo cáo nghiên cứu tách riêng | Repo lớn dần (giảm bằng cách không commit dataset/model) |
| B. Biến `D:\project` thành repo | Không tạo thư mục mới | Lẫn tài liệu nghiên cứu với mã nguồn |
| C. Nhiều repo (firmware, edge, contracts) | Tách quyền, CI riêng | Quá nặng cho 1 người; đồng bộ contract khó |

## Quyết định

**Chọn A.** Cấu trúc cấp 1: `docs/`, `contracts/`, `config/`, `edge/`, `firmware/`, `ai/`, `hardware/`, `tools/`. Các tài liệu quản lý dự án (PROJECT_STATUS, ROADMAP, TASKS, DECISIONS, TEST_REPORT, HARDWARE_BOM, ARCHITECTURE, README, CHANGELOG) đặt ở gốc.

## Hệ quả

- Một commit có thể đổi contract + firmware + edge + test cùng lúc.
- Dataset, ảnh, trọng số mô hình **không** vào git (xem ADR-0010, `.gitignore`); chỉ commit manifest và model card.
- Thư mục làm việc riêng `.claude/company/` được đưa vào `.gitignore`.
