# ai/datasets/

Dataset cho vision (Phase 1) và OCR (Phase 3).

## Quy tắc (ADR-0010, QA_PLAN mục 7)

- **Ảnh KHÔNG commit** (`.gitignore`). Chỉ commit `manifest.json` + tài liệu.
- Mỗi dataset một thư mục: `ai/datasets/<name>/`
  - `manifest.json`: danh sách file, checksum SHA-256, phiên chụp (`session_id`), điều kiện (ánh sáng, tốc độ băng tải, camera), nhãn, tập (`train`/`val`/`test`)
  - `raw/`, `images/`, `labels/`: dữ liệu thật (không commit)
  - `README.md`: cách thu thập, cách tái tạo
- **Chia tập theo phiên chụp**, không trộn ảnh cùng phiên giữa train và test (chống rò rỉ dữ liệu — VT-04).
- Ghi lại số lượng mẫu mỗi lớp; nếu mất cân bằng thì ghi rõ trong TEST_REPORT.
