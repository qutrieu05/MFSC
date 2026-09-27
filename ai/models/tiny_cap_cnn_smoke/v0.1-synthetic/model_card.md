# tiny_cap_cnn_smoke v0.1-synthetic

**Mục đích:** chứng minh pipeline `dataset -> training -> checkpoint -> ONNX export -> ONNX
Runtime inference -> postprocess() -> DecisionEngine` chạy được end-to-end (P1.3, D-033/D-035).
**Đây KHÔNG phải mô hình sản xuất** — không dùng để suy luận trên sản phẩm thật.

## Dataset

`data_source: synthetic` — ảnh "nắp chai" 128×128 sinh bởi `msfc.vision.synthetic.generate_dataset`
(docs/DATASET_SPEC.md), 3 phiên (`s01`,`s02`,`s03`), mỗi phiên 12 ảnh (6 GOOD + 2×3 DEFECT sub-label:
`MARK`, `STICKER_MISSING`, `SCRATCH`) — 36 ảnh tổng cộng. Chia theo phiên (`split_by_session`,
docs/DATASET_SPEC.md mục 6): train=s01, val=s02, test=s03. **0đ, không dùng ảnh thật.**

## Huấn luyện

`TinyCapCNN` (3 conv block + adaptive pool + linear), CPU only (R-27: `torch.cuda.is_available()`
= False trên máy này dù có RTX 3050), 2 epoch, batch size 4, Adam lr=1e-3, seed=0. Đây là
**smoke test**, không phải huấn luyện tối ưu — cố tình **không** train lâu hơn hay tinh chỉnh
hyperparameter, theo đúng chỉ thị PO ("không train lâu, không over-optimize").

## Kết quả (test split, s03, 12 ảnh)

| accuracy | precision(DEFECT) | recall(DEFECT) | F1(DEFECT) | confusion |
|---|---|---|---|---|
| 0.5 | 0.0 | 0.0 | 0.0 | tp=0, fp=0, tn=6, fn=6 |

Chi tiết: [metrics.json](metrics.json).

## Giới hạn đã biết (báo cáo trung thực, không làm đẹp số liệu)

**Mô hình dự đoán mọi ảnh là GOOD** (0 true positive, 0 false positive trên tập test) — không
phân biệt được GOOD/DEFECT trên dataset tổng hợp mặc định này sau 2 epoch. Đây là kết quả nhất
quán với giới hạn đã ghi ở [docs/RISK_REGISTER.md](../../../docs/RISK_REGISTER.md) R-28 cho
`ClassicCvBaseline`: nhiễu cảm biến + độ lệch vị trí ngẫu nhiên trong bộ sinh ảnh tổng hợp làm
tín hiệu lỗi (đường viền/vết mảnh) khó tách khỏi nền, và 2 epoch trên 12 ảnh train là quá ít để
CNN tự học được tín hiệu đó dù về lý thuyết CNN ít nhạy hơn với lệch vị trí nhỏ so với baseline
"khoảng cách tới template". **Đây là bằng chứng cho một sự thật đã biết trước (dataset tổng hợp
quá nhỏ/quá khó), không phải lỗi trong code training/export/inference** — toàn bộ pipeline chạy
đúng, có kiểm chứng bằng `test_vision_onnx_inference_smoke.py::test_onnx_output_matches_pytorch_model_on_the_same_input`
(so khớp đầu ra ONNX Runtime với PyTorch, sai lệch < 1e-4).

**Không dùng mô hình này cho bất kỳ acceptance criteria hay claim độ chính xác nào** (D-026).
Huấn luyện thật với dataset thật (ảnh chụp từ camera, ≥600 ảnh) là P1.11, sau khi có phần cứng.

## File

- `checkpoint.pt` — PyTorch state_dict + `RoiConfig`/`TrainingConfig`/`best_epoch` (không commit git).
- `model.onnx` — export bằng `torch.onnx.export(..., dynamo=False)` (xem `training.export_onnx` docstring
  về lý do dùng legacy exporter thay vì dynamo mặc định của PyTorch 2.13).
- `checksum.txt` — SHA-256 của hai file trên.
- `metrics.json` — số liệu đầy đủ (train/val history + test).

**Ngày:** 2026-09-18 · **Người tạo:** Claude Inc (theo chỉ thị PO "Phase 1 — Software Gate / AI Completion") · **data_source: synthetic**
