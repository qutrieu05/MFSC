# ADR-0013: Chiến lược Git

- **Trạng thái:** PROPOSED · **Ngày:** 2026-09-17 · **Người quyết định cuối:** PO

## Quyết định

Chi tiết thao tác: [GIT_STRATEGY.md](../GIT_STRATEGY.md).

- **Trunk-based:** nhánh `main` luôn qua được test. Làm việc trên nhánh ngắn hạn `feat/<TASK-ID>-<slug>`, `fix/…`, `docs/…`, `test/…`.
- **Conventional Commits** kèm mã task, ví dụ: `feat(firmware): add heartbeat monitor [P1-07]`.
- **Tag khi phase được PO chấp nhận:** `phase-0-accepted`, `phase-1-accepted`, …; bản phát hành cuối `v1.0.0`.
- **CHANGELOG** theo Keep a Changelog.
- **Không commit:** dataset, ảnh, trọng số mô hình, log, `config/site.toml`, `.claude/company/`. Chỉ commit manifest/model card (Git LFS: FUTURE nếu cần).
- Claude Inc **chỉ tạo commit khi PO yêu cầu hoặc cho phép**; PO có quyền cuối về merge và tag.

## Lý do

- Một người làm nên không cần Git Flow nhiều nhánh dài hạn.
- Tag theo phase tạo mốc phục hồi và bằng chứng tiến độ rõ ràng.
