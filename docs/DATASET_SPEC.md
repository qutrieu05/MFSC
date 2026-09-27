# Dataset Specification (Phase 1 vision, Phase 3 OCR)

**Phiên bản:** 1.0 · **Ngày:** 2026-09-18 · **Trạng thái:** đề xuất, chờ PO chọn sản phẩm mẫu
**Nguyên tắc:** sản phẩm mẫu **tự chế / giá thấp**, không dùng sản phẩm công nghiệp thật.

---

## 1. Chọn sản phẩm mẫu

| Phương án | Chi phí | Ưu | Nhược | Đánh giá |
|---|---|---|---|---|
| **Nắp chai nhựa cùng loại** (Ø 28–30 mm) | **0đ** (gom từ chai nước) hoặc ~20–40k/100 cái | Rất đồng nhất, phẳng, dễ tạo lỗi, dễ đứng trên đai, dễ gom số lượng lớn | Bề mặt bóng → dễ lóa, cần tán sáng | **Đề xuất cho MVP** |
| Hộp giấy nhỏ cùng cỡ (hộp thuốc, hộp diêm) | 0–30k | Mặt phẳng lớn, dán nhãn dễ (tốt cho Phase 3 OCR) | Dễ móp, kém đồng nhất khi gom lẻ | **Đề xuất cho Phase 3** |
| Khối in 3D / khối gỗ cắt | 30–80k | Đồng nhất tuyệt đối, kích thước tùy chọn | Cần máy in 3D/xưởng; mất thời gian | Phương án thay thế |
| Viên kẹo/vỉ thuốc | 20–50k | Giống bài toán thật | Không đồng nhất, dễ hỏng | Không khuyến nghị |

**Quyết định đề xuất:** dùng **nắp chai** cho Phase 1 (phân loại ngoại quan) và **hộp giấy nhỏ có dán nhãn in** cho Phase 3 (OCR). Cả hai đều dùng chung băng tải và cùng khoảng cách camera.

## 2. Số class và loại lỗi

**Phase 1 (MVP): bài toán phân loại nhị phân trên ROI.**

| Class | Nhãn | Ghi chú |
|---|---|---|
| 0 | `GOOD` | Sản phẩm bình thường |
| 1 | `DEFECT` | Có bất kỳ một trong các lỗi bên dưới |

**Nhãn phụ (sub-label) — lưu trong metadata, không dùng để huấn luyện ở MVP** nhưng **bắt buộc báo cáo recall theo từng loại**:

| Sub-label | Cách tạo lỗi (lặp lại được) | Mức độ khó cho AI |
|---|---|---|
| `MARK` | Vạch 1 nét bút lông dầu dài 8–12 mm trên mặt nắp | Dễ (tương phản cao) |
| `STICKER_MISSING` | Sản phẩm GOOD có dán nhãn tròn Ø 12 mm; bản lỗi **không dán** | Dễ–trung bình |
| `SCRATCH` | Chà nhẹ giấy nhám mịn 3 lần theo một hướng | **Khó** (tương phản thấp) |
| `DEFORM` (tùy chọn) | Bóp méo mép nắp bằng kìm | Trung bình |

**Lý do thiết kế như vậy:** có đủ một lỗi dễ (để chứng minh chuỗi hoạt động), một lỗi trung bình và một lỗi khó (để báo cáo giới hạn thật của mô hình thay vì chỉ khoe số đẹp).

Mở rộng về sau (FUTURE, không làm ở MVP): chuyển thành 4 class (GOOD + 3 loại lỗi), hoặc dùng anomaly detection chỉ học ảnh GOOD.

## 3. Kích thước dataset

| Tập | Số ảnh tối thiểu (MVP) | Khuyến nghị | Ghi chú |
|---|---|---|---|
| `GOOD` | 300 | 500 | Nhiều góc quay, vị trí khác nhau |
| `DEFECT` | 300 (100/loại × 3 loại) | 500 (≈165/loại) | Giữ cân bằng với GOOD |
| **Tổng** | **600** | **≈ 1.000** | Chia theo phiên chụp (mục 6) |
| Bổ sung ảnh "khó" | 50 | 100 | Sản phẩm lệch ROI, nghiêng, hai sản phẩm sát nhau, không có sản phẩm (ảnh trống) |

Với ROI 128–224 px và mô hình nhỏ fine-tune (MobileNetV3/ResNet18) trên RTX 3050, 600–1.000 ảnh + augmentation là **đủ để có kết quả có ý nghĩa**, và đủ nhỏ để một người chụp trong 2–3 buổi.

**Nếu số lượng thực tế thấp hơn:** phương án dự phòng là **anomaly detection chỉ học ảnh GOOD** (cần ~200–400 ảnh GOOD, ảnh lỗi chỉ để test) — đã ghi trong ADR-0010 như hướng Phase 6.

## 4. Cách chụp

| Thông số | Giá trị đề xuất | Lý do |
|---|---|---|
| Khoảng cách camera → mặt đai | **15–25 cm** (cố định, ghi lại số đo) | Sản phẩm chiếm ≥ 200×200 px trong khung |
| Góc camera | Vuông góc mặt đai (90°), lệch tối đa 10° | Tránh biến dạng phối cảnh |
| ROI | Vùng bao sản phẩm + lề 20–30% | Đủ chỗ cho sai số vị trí |
| Độ phân giải chụp | 1280×720 trở lên, lưu ROI cắt ra + ảnh full (tùy chọn) | ROI để huấn luyện, full để kiểm tra lại |
| Định dạng | JPEG chất lượng ≥ 90 hoặc PNG | Tránh nén quá mạnh làm mất chi tiết vết xước |
| Exposure / White balance / Focus | **KHÓA (manual)**, ghi giá trị vào metadata phiên | Nếu để auto, mô hình sẽ học theo độ sáng thay vì theo lỗi |
| Chế độ chụp | **(a) Tĩnh**: băng tải dừng · **(b) Động**: băng tải chạy ở tốc độ danh định | (b) là bắt buộc cho **tập test** vì có nhòe chuyển động thật |
| Vị trí sản phẩm | Ngẫu nhiên ±10 mm quanh tâm ROI, quay ngẫu nhiên 0–360° | Tránh mô hình học theo vị trí |
| Trigger | Bằng cảm biến S1 (khi có phần cứng) hoặc bấm tay (khi chụp sớm bằng điện thoại) | Giống điều kiện chạy thật |

## 5. Chiếu sáng

| Thông số | Giá trị đề xuất |
|---|---|
| Nguồn sáng | LED **DC** (12 V), không dùng đèn AC/huỳnh quang (nhấp nháy 50 Hz gây sọc ảnh) |
| Kiểu chiếu | Chiếu chéo 30–45° từ hai bên + tấm tán sáng (giấy nến/mica trắng sữa) |
| Chống lóa | Bắt buộc có tán sáng vì nắp chai bóng; nếu vẫn lóa thì tăng góc chiếu hoặc dùng nền tối |
| Ánh sáng môi trường | Che bằng hộp carton; ghi lại điều kiện (đèn phòng bật/tắt) trong metadata |
| Kiểm tra | Histogram ảnh: tránh vùng cháy sáng (> 250) và vùng tối chết (< 5) trên bề mặt sản phẩm |
| Nền đai | Màu **tối, nhẵn, không bóng** để tương phản với nắp sáng màu |

## 6. Phiên chụp (session) và chia tập

**Nguyên tắc chống rò rỉ dữ liệu (VT-04):** chia theo **phiên chụp**, không chia ngẫu nhiên theo ảnh.

| Phiên | Khi nào | Chế độ | Dùng cho |
|---|---|---|---|
| `s01` | Buổi 1 | Tĩnh | train |
| `s02` | Buổi 2 (khác ngày, **tháo và gắn lại camera**, chiếu sáng dựng lại) | Tĩnh | train + val (80/20 ngẫu nhiên trong phiên) |
| `s03` | Buổi 3 | **Động** (băng tải chạy) | **test (giữ kín, chỉ dùng 1 lần cuối)** |
| `s04` (tùy chọn) | Buổi 4 | Động, đổi điều kiện sáng | test độ bền (VT-02), báo cáo riêng |

Yêu cầu bắt buộc:
- **Không** ảnh nào của `s03` được xuất hiện trong train/val.
- Mỗi phiên ghi `session.json`: ngày, khoảng cách camera, exposure, đèn, tốc độ đai, người chụp, ghi chú.
- Báo cáo kết quả **theo từng phiên** để thấy mô hình có suy giảm khi đổi điều kiện hay không.

## 7. Annotation

Phân loại nhị phân trên ROI ⇒ **không cần vẽ bounding box**. Nhãn lưu trong CSV/JSON:

```
ai/datasets/caps_v1/
├── README.md                # cách thu thập, cách tái tạo
├── manifest.json            # danh sách file + sha256 + session + split (commit được)
├── labels.csv               # image_path, label, sub_label, session_id, capture_mode, notes
├── sessions/s01.json        # thông số phiên (exposure, distance, lighting...)
└── images/                  # ảnh ROI (KHÔNG commit)
    ├── s01/good/*.jpg
    ├── s01/defect_mark/*.jpg
    ├── s01/defect_sticker_missing/*.jpg
    └── s01/defect_scratch/*.jpg
```

`labels.csv` ví dụ:

```
image_path,label,sub_label,session_id,capture_mode,notes
images/s01/good/0001.jpg,GOOD,,s01,static,
images/s01/defect_mark/0001.jpg,DEFECT,MARK,s01,static,net but 10mm
images/s03/defect_scratch/0007.jpg,DEFECT,SCRATCH,s03,moving,belt 80mm/s
```

**Quy tắc chất lượng:**
- Loại ảnh trùng (so sánh hash) và ảnh mờ (dùng ngưỡng variance of Laplacian).
- Ảnh không có sản phẩm hoặc sản phẩm ngoài ROI → gán class riêng `EMPTY` và **loại khỏi tập huấn luyện nhị phân**, nhưng giữ để test hành vi hệ thống.
- Mỗi ảnh chỉ một nhãn; nếu sản phẩm có 2 lỗi cùng lúc thì ghi sub_label chính + ghi chú.

## 8. Tiêu chí báo cáo (bắt buộc, không được che giấu)

| Chỉ số | Yêu cầu báo cáo |
|---|---|
| Accuracy, Precision, Recall, F1 | Trên tập test `s03` (chưa từng dùng) |
| **Recall theo từng sub_label** | Đặc biệt `SCRATCH` (lỗi khó) — nếu thấp thì ghi rõ giới hạn |
| Ma trận nhầm lẫn | Bắt buộc |
| Tỷ lệ loại oan (false reject) | GOOD bị gạt = tổn thất sản xuất |
| Tỷ lệ bỏ sót (false accept) | DEFECT lọt qua = lỗi nghiêm trọng hơn |
| Đường cong theo ngưỡng | Chọn ngưỡng làm việc và **ghi lý do** (VT-03) |
| Số lượng ảnh từng class/phiên | Để người khác đánh giá được độ tin cậy |
| Giới hạn | Dataset nhỏ, một loại sản phẩm, một điều kiện sáng, camera rẻ, chỉ 3 loại lỗi tự tạo |

## 9. Dữ liệu tổng hợp (dùng tạm trước khi có phần cứng)

Ở P1.2–P1.3 (chưa mua gì), pipeline được kiểm chứng bằng:
1. **Ảnh tổng hợp do script sinh** (vẽ hình tròn trên nền tối, thêm vạch/nhiễu/nhòe/biến đổi sáng) — để test đúng/sai của code, **không** để tuyên bố độ chính xác.
2. **Ảnh thật chụp bằng điện thoại** (0đ) với sản phẩm mẫu gom miễn phí và đèn bàn — đủ để huấn luyện mô hình thử nghiệm đầu tiên.

Mọi kết quả trên dữ liệu tổng hợp phải được **đánh dấu rõ là synthetic** trong TEST_REPORT và không dùng cho acceptance criteria.

## 10. Dataset OCR (Phase 3) — phác thảo

| Điều kiện | Số ảnh tối thiểu | Nhãn |
|---|---|---|
| Hạn dùng còn hiệu lực | 20 | text + `OK` |
| Hết hạn | 20 | text + `EXPIRED` |
| Sai định dạng (ví dụ `32/13/2026`) | 20 | text + `FORMAT_INVALID` |
| In mờ/nhòe không đọc được | 20 | `UNREADABLE` |
| Thiếu nhãn | 20 | `LABEL_MISSING` |
| Nhãn dán lệch/nghiêng > 15° | 20 | `LABEL_MISALIGNED` |
| Thay đổi ánh sáng (sáng/tối hơn) | 20 | theo nội dung |
| **Tổng** | **140** | |

Nhãn OCR = **văn bản chuẩn (ground truth)** + trạng thái; dùng để đo cả độ chính xác đọc ký tự và độ chính xác quyết định.

## 11. Cần mua gì cho dataset

| Item (Master BOM) | Nội dung | Chi phí |
|---|---|---|
| D1 | 50–100 sản phẩm mẫu đồng nhất (nắp chai gom miễn phí hoặc mua) | **0 – 40k** |
| D2 | Bút lông dầu, nhãn tròn, giấy nhám | 15 – 40k |
| D3 (Phase 3) | Giấy decal + in nhãn hạn dùng | 15 – 50k |

**Không cần mua gì khác cho dataset.** Việc chụp sớm có thể dùng điện thoại (0đ) trước khi có camera USB.
