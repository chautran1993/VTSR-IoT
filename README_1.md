# Hướng dẫn triển khai — Hệ thống IoT nhận diện biển báo giao thông Việt Nam

Đề tài: *"Nghiên cứu và triển khai hệ thống IoT nhận diện biển báo giao thông Việt Nam thời gian thực trên môi trường mô phỏng"* — GVHD: ThS. Phan Đình Duy.

Tài liệu này hướng dẫn phần **triển khai (Tuần 4 → Tuần 7)**, tiếp nối kết quả huấn luyện đã có.

---

## 0. Hiện trạng dự án

Từ `args.yaml` và `results.csv` mà nhóm đã có:

| Hạng mục | Giá trị thực tế |
|---|---|
| Mô hình | `yolov8s.pt` (transfer learning từ COCO) |
| Số epoch | 50 |
| Ảnh đầu vào | 640×640, batch 16 |
| Precision / Recall | 0.893 / 0.884 |
| **mAP@0.5** | **0.942** |
| **mAP@0.5:0.95** | **0.774** |

Kết quả này **vượt mục tiêu đề cương** (mAP@0.5 ≥ 80%, phấn đấu 85–90%). Đường loss đã bão hòa từ khoảng epoch 40 → không cần train thêm, có thể chốt `best.pt` và chuyển sang giai đoạn triển khai.

---

## 1. Cấu trúc thư mục chuẩn

```
VTSR-IoT/
├── dataset/
│   ├── train/ valid/ test/          # images + labels (YOLO format)
│   └── data.yaml
├── weights/
│   ├── best.pt                      # mô hình chính thức
│   └── best.onnx                    # bản tối ưu (tuần 5)
├── src/
│   ├── realtime_detect.py           # pipeline real-time + MQTT
│   ├── export_onnx.py               # xuất ONNX
│   ├── benchmark.py                 # đo FPS / độ trễ
│   └── mqtt_monitor.py              # subscriber kiểm chứng
├── notebooks/train_yolov8.ipynb
├── runs/detect/train/               # results.csv, các biểu đồ
├── video/                           # video hành trình dùng demo
├── logs/                            # runtime_log.csv, benchmark.csv
├── docs/                            # báo cáo, slide, sơ đồ
└── requirements.txt
```

## 2. Cài đặt môi trường (mỗi thành viên chạy 1 lần)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -c "from ultralytics import YOLO; print('OK')"
```

> Dùng **venv là bắt buộc** — nếu không, mỗi máy một phiên bản thư viện, số liệu FPS đo được sẽ không so sánh được với nhau.

---

## 3. Tuần 4 — Pipeline nhận diện thời gian thực

```bash
# Test trên video hành trình (ổn định, dễ quay demo)
python src/realtime_detect.py --weights weights/best.pt --source video/demo.mp4

# Test trên webcam (mô phỏng camera gắn xe)
python src/realtime_detect.py --weights weights/best.pt --source 0

# Vừa chạy vừa lưu file demo
python src/realtime_detect.py --weights weights/best.pt --source video/demo.mp4 \
       --save-video docs/demo_out.mp4
```

Script đã cài sẵn: đọc khung hình **đa luồng**, **bỏ khung khi xử lý trễ** (webcam), ngưỡng `conf = 0.35` / `iou = 0.5`, hiển thị bounding box + tên lớp + độ tin cậy + FPS + độ trễ, và ghi `logs/runtime_log.csv`.

**Kết quả cần đạt tuần 4:** ứng dụng chạy mượt, file `runtime_log.csv` có số liệu FPS/độ trễ, video demo thô.

---

## 4. Tuần 5 — Tích hợp MQTT và tối ưu ONNX

### 4.1. Cài Mosquitto broker

- **Windows:** tải bộ cài từ mosquitto.org → thêm 2 dòng sau vào `mosquitto.conf` rồi khởi động lại dịch vụ:
  ```
  listener 1883
  allow_anonymous true
  ```
- **Ubuntu:** `sudo apt install mosquitto mosquitto-clients && sudo systemctl start mosquitto`
- **macOS:** `brew install mosquitto && brew services start mosquitto`

Kiểm tra broker sống: mở 2 terminal, chạy `mosquitto_sub -t test` và `mosquitto_pub -t test -m hello`.

### 4.2. Chạy luồng IoT hoàn chỉnh

```bash
# Terminal 1 — giám sát
python src/mqtt_monitor.py --broker localhost --topic vtsr/edge01/detections

# Terminal 2 — thiết bị biên
python src/realtime_detect.py --weights weights/best.pt --source video/demo.mp4 --mqtt
```

Bản tin JSON đúng lược đồ đã đăng ký ở báo cáo tuần 3:

```json
{
  "device_id": "edge01",
  "timestamp": "2026-09-01T08:15:22.481Z",
  "frame_id": 152,
  "detections": [
    {"class_id": 3, "class_name": "P.130", "confidence": 0.91, "bbox": [412, 188, 64, 66]}
  ],
  "latency_ms": 41.7,
  "fps": 23.4
}
```

### 4.3. Dashboard Node-RED

```bash
npm install -g node-red node-red-dashboard
node-red        # mở http://127.0.0.1:1880
```

Luồng tối thiểu (5 node, đủ để bảo vệ):
`mqtt in (vtsr/edge01/detections)` → `json` → 3 nhánh:
1. `function` lấy `msg.payload.fps` → **gauge** (FPS thời gian thực)
2. `function` đếm số lần xuất hiện từng `class_name` → **bar chart** (thống kê biển báo)
3. `function` format 1 dòng text → **text/table** (log nhận diện gần nhất)

Nhớ **Export → Clipboard** file `flows.json` lưu vào `docs/` để nộp kèm báo cáo.

### 4.4. Xuất ONNX

```bash
python src/export_onnx.py --weights weights/best.pt
```

---

## 5. Tuần 6 — Đánh giá và kiểm thử

### 5.1. Đo trên tập test (số liệu chính của báo cáo)

```bash
yolo val model=weights/best.pt data=dataset/data.yaml split=test imgsz=640 plots=True
```

Lệnh này sinh `confusion_matrix.png`, `PR_curve.png`, `F1_curve.png` và bảng chỉ số **theo từng lớp** — phần quan trọng nhất để phân tích lớp nào yếu và vì sao.

### 5.2. So sánh .pt và .onnx

```bash
python src/benchmark.py --models weights/best.pt weights/best.onnx \
       --source video/demo.mp4 --device cpu --n 200
```

### 5.3. Kiểm thử theo điều kiện

Cắt video thành các đoạn riêng: **ban ngày / chiều tối / trời mưa / biển ở xa / biển bị che một phần**, chạy `benchmark.py` hoặc `yolo val` trên từng đoạn rồi lập bảng. Đây là phần cho thấy nhóm kiểm thử thật chứ không chỉ chạy một lần.

**Ba bảng cần có trong báo cáo:**

| Bảng | Nội dung |
|---|---|
| Bảng A | Precision / Recall / mAP@0.5 / mAP@0.5:0.95 **theo từng lớp** trên tập test |
| Bảng B | Kích thước mô hình, FPS, độ trễ trung bình & p95 — `.pt` vs `.onnx` trên CPU |
| Bảng C | mAP và FPS theo từng điều kiện môi trường |

---

## 6. Tuần 7 — Báo cáo, slide, video demo

Kịch bản demo 3–4 phút, quay một mạch không cắt:
1. Mở cấu trúc thư mục dự án, giới thiệu `best.pt` (10s)
2. Chạy `realtime_detect.py` trên video hành trình — chỉ rõ bounding box, tên biển, FPS (60s)
3. Bật webcam, giơ ảnh biển báo in sẵn trước camera (30s)
4. Chia màn hình: bên trái ứng dụng, bên phải dashboard Node-RED cập nhật đồng thời (60s)
5. Chốt bằng bảng số liệu mAP / FPS (20s)

---

## 7. Bốn điểm cần xử lý trước khi nộp

1. **Số lớp lệch so với đề cương.** File `_annotations.csv` cho thấy bộ dữ liệu có **56 lớp**, trong khi đề cương và báo cáo tuần 3 ghi **15 lớp**. Cần chọn một trong hai hướng: (a) giữ 56 lớp và sửa lại đề cương/báo cáo, hoặc (b) gộp/lọc về đúng danh mục 15 lớp đã đăng ký rồi train lại. Hội đồng gần như chắc chắn sẽ hỏi chỗ này.

2. **`fliplr = 0.5` trong `args.yaml`.** Báo cáo tuần 3 khẳng định đã tắt lật ngang (`fliplr = 0.0`) vì lật ảnh làm sai lệch ngữ nghĩa biển có hướng — nhưng lần train thực tế vẫn **bật** lật ngang. Điều này có thể là nguyên nhân khiến cặp P.123a (cấm rẽ trái) / P.123b (cấm rẽ phải) và R.301c/d/e bị nhầm lẫn. Kiểm tra `confusion_matrix.png` ở đúng các ô này; nếu nhầm nhiều, train lại 50 epoch với `fliplr=0.0` — chi phí khoảng 1–2 giờ trên Colab T4 và sẽ là một kết quả thực nghiệm rất đáng giá để đưa vào báo cáo.

3. **Mô hình là `yolov8s`, không phải `yolov8n`.** Phần cơ sở lý thuyết lập luận khá dài về việc chọn YOLOv8 **Nano**, nhưng thực tế nhóm train bản **Small**. Hoặc sửa lại lập luận, hoặc train thêm một bản `yolov8n` để so sánh — cách sau tốt hơn vì tạo ra đúng bảng đánh đổi *độ chính xác ↔ tốc độ* mà đề tài edge cần.

4. **Mất cân bằng lớp nghiêm trọng.** P.127 có 804 đối tượng trong khi P.245a chỉ có 1, P.125 có 5, P.124b có 7. Các lớp dưới ~20 mẫu gần như chắc chắn cho recall rất thấp và sẽ kéo mAP tổng xuống. Xử lý: gộp các lớp quá hiếm vào nhóm chung, hoặc loại khỏi phạm vi và ghi rõ lý do trong phần "Hạn chế của đề tài" — cách này hoàn toàn được chấp nhận về mặt học thuật miễn là trình bày minh bạch.

---

## 8. Sự cố thường gặp

| Triệu chứng | Cách xử lý |
|---|---|
| Webcam không mở được trên Windows | Đổi `cv2.VideoCapture(0)` → `cv2.VideoCapture(0, cv2.CAP_DSHOW)` |
| FPS quá thấp trên CPU | Giảm `--imgsz 416`, dùng `.onnx`, hoặc `--device 0` nếu máy có GPU |
| `ConnectionRefusedError` khi bật `--mqtt` | Broker chưa chạy — kiểm tra dịch vụ Mosquitto |
| Node-RED không nhận bản tin | Sai topic, hoặc thiếu node `json` sau `mqtt in` |
| Tiếng Việt có dấu bị vỡ trên khung hình | OpenCV không vẽ được Unicode — dùng mã biển (P.130) hoặc vẽ bằng PIL |
