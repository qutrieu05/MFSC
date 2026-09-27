# Documentation Index

## Đọc theo thứ tự này nếu bạn mới vào project

1. [../README.md](../README.md) — tổng quan hệ thống, cách chạy test Phase 0
2. [PROJECT_CHARTER.md](PROJECT_CHARTER.md) — mục tiêu, vai trò, phạm vi, ràng buộc
3. [REQUIREMENTS.md](REQUIREMENTS.md) — yêu cầu có ID (an toàn trước, rồi chức năng, rồi NFR)
4. [../ARCHITECTURE.md](../ARCHITECTURE.md) — 9 layer, node, máy trạng thái, luồng, interface
5. [SAFETY_CONCEPT.md](SAFETY_CONCEPT.md) — **đọc trước khi chạm vào phần cứng**
6. [MQTT_CONTRACT.md](MQTT_CONTRACT.md) — giao tiếp giữa firmware và Edge Server
7. [PHASE1_PLAN.md](PHASE1_PLAN.md) — việc sắp làm

## Theo chủ đề

| Chủ đề | Tài liệu |
|---|---|
| Quyết định kiến trúc | [adr/](adr/) (0001–0013) · [../DECISIONS.md](../DECISIONS.md) |
| Chuẩn code và quy trình | [CODING_STANDARDS.md](CODING_STANDARDS.md) · [GIT_STRATEGY.md](GIT_STRATEGY.md) |
| Cấu hình và logging | [CONFIGURATION.md](CONFIGURATION.md) · [LOGGING.md](LOGGING.md) |
| Kiểm thử | [QA_PLAN.md](QA_PLAN.md) · [../TEST_REPORT.md](../TEST_REPORT.md) |
| Phần cứng | [HARDWARE_INVENTORY.md](HARDWARE_INVENTORY.md) · [../HARDWARE_BOM.md](../HARDWARE_BOM.md) · [../hardware/PIN_MAPPING_DRAFT.md](../hardware/PIN_MAPPING_DRAFT.md) |
| Quản lý dự án | [../PROJECT_STATUS.md](../PROJECT_STATUS.md) · [../ROADMAP.md](../ROADMAP.md) · [../TASKS.md](../TASKS.md) · [RISK_REGISTER.md](RISK_REGISTER.md) |
| Thay đổi | [../CHANGELOG.md](../CHANGELOG.md) |

## Tài liệu sẽ được tạo ở các phase sau

| Tài liệu | Phase | Nội dung |
|---|---|---|
| `../hardware/WIRING_GUIDE.md` | 1 | Hướng dẫn đấu dây từng bước + checklist + quy trình test (phát hành **trước khi** PO đấu dây) |
| `TROUBLESHOOTING.md` | 1+ | Mỗi mã lỗi: triệu chứng → nguyên nhân → cách kiểm tra → cách xử lý → phòng ngừa |
| `INSTALLATION.md`, `USER_MANUAL.md`, `DEVELOPER_GUIDE.md` | 7 | Bàn giao |
| `BENCHMARK.md` | 7 | Tổng hợp số liệu hiệu năng |
| `DEMO_PROCEDURE.md` | 7 | Quy trình demo 20 bước (ACC-01..20) |
