# Git Strategy

**Quyết định:** [ADR-0013](adr/0013-git-strategy.md)

## 1. Nhánh

| Nhánh | Mục đích |
|---|---|
| `main` | Luôn chạy được và **qua toàn bộ test**. Là nhánh demo |
| `feat/<TASK-ID>-<slug>` | Một task trong TASKS.md, ví dụ `feat/P1-04-product-tracker` |
| `fix/<TASK-ID>-<slug>` | Sửa lỗi |
| `docs/<slug>`, `test/<slug>`, `chore/<slug>` | Tài liệu, test, việc phụ trợ |

Nhánh sống ngắn (vài ngày). Merge vào `main` bằng `--no-ff` để giữ dấu vết task.

## 2. Commit

Theo **Conventional Commits**, kèm mã task ở cuối:

```
feat(firmware): add heartbeat monitor with seq check [P1-07]
fix(edge): reject verdict for unknown product_id [P1-12]
docs(contract): document safety heartbeat semantics [P0-05]
test(vision): add offline evaluation for defect recall [P1-15]
```

Kiểu: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`.
Scope: `firmware`, `edge`, `contract`, `config`, `ai`, `hardware`, `docs`, `tools`.

Quy tắc:
- Một commit = một thay đổi có nghĩa; **không** commit "wip" vào `main`.
- Chỉ commit khi `pytest` (và test firmware nếu có thay đổi firmware) đã pass.
- Thay đổi contract phải nằm **cùng một commit** với code hai phía dùng nó.

## 3. Tag và phát hành

| Tag | Khi nào |
|---|---|
| `phase-<N>-accepted` | PO chấp nhận acceptance criteria của phase |
| `v0.x.0` | Mốc chức năng |
| `v1.0.0` | FINAL DEMO / RELEASE của S1 |

CHANGELOG cập nhật theo **Keep a Changelog** mỗi khi có thay đổi đáng kể.

## 4. Không đưa vào git

`config/site.toml` · `logs/` · `runtime/` · dataset và ảnh (`ai/datasets/**/raw`, `images`, `labels`) · trọng số mô hình (`*.pt`, `*.onnx`, `*.engine`) · build firmware (`build/`, `.pio/`, `managed_components/`) · `.claude/company/` · mọi bí mật.

Thay vào đó commit: **manifest dataset** (danh sách file + checksum + nguồn), **model card** (tên, phiên bản, dữ liệu huấn luyện, kết quả đánh giá, giới hạn), script tái tạo.

## 5. Ai commit

Claude Inc **không tự commit**; chỉ tạo/sửa file rồi báo cáo. PO quyết định thời điểm commit, merge, tag. Khi PO yêu cầu, Claude Inc chuẩn bị nội dung commit theo quy tắc trên.

## 6. Lệnh hay dùng

```bash
git switch -c feat/P1-04-product-tracker
python -m pytest            # trong edge/
git add -A && git commit -m "feat(firmware): add product tracker FIFO [P1-04]"
git switch main && git merge --no-ff feat/P1-04-product-tracker
git tag -a phase-1-accepted -m "Phase 1 accepted by PO"
```
