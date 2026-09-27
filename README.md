# Dashboard nhận diện biển báo giao thông Việt Nam

Ứng dụng FastAPI + HTML/CSS/JavaScript nội tuyến, chạy offline, dùng YOLOv8s qua ONNX Runtime trên CPU. Tài liệu triển khai trước đây nằm trong [README_1.md](README_1.md).

## Chạy trên Windows / Python 3.13

Mở terminal tại `C:\Users\vungo\VTSR-IoT`:

```powershell
# Chỉ tạo nếu chưa có môi trường:
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\Activate.ps1
python -m uvicorn src.web_app:app --host 127.0.0.1 --port 8000
```

Hoặc nhấp đúp **run_dashboard.bat** để kích hoạt `.venv`, mở trình duyệt và chạy server. Nếu trình duyệt mở trước khi server sẵn sàng, tải lại trang. Truy cập http://127.0.0.1:8000. Dừng server bằng Ctrl+C. Chạy một worker duy nhất, không dùng `--reload` khi trình diễn để tránh tranh chấp camera.

Nếu đã cài môi trường cũ, chỉ cần thêm bốn phụ thuộc trực tiếp:

```powershell
.venv\Scripts\python -m pip install fastapi uvicorn python-multipart websockets
```

## Mô hình và camera

Dùng các model đã xuất sẵn: `weights/best_320.onnx`, `weights/best_416.onnx`, `weights/best.onnx` (640). Đây là ba model kích thước cố định; đổi dropdown sẽ chuyển sang model tương ứng, không chỉ đổi kích thước ảnh hiển thị. Thư mục `models/` cũng được kiểm tra nếu không có file trong `weights/`. Không tự tải trọng số hoặc tự xuất model khi chạy demo.

Mặc định: CPU, độ phân giải 416, confidence 0,35, IoU 0,5, camera 0. Lần khởi động đầu tiên cần thời gian nạp và làm nóng ba model. Có thể chọn camera khác bằng `$env:VTSR_CAMERA="1"` trước khi chạy. Nút Bật/Tắt camera áp dụng chung cho tất cả trình duyệt, giải phóng camera khi tắt. Khi thiếu camera, ứng dụng thử mở lại mỗi 3 giây; vẫn tải ảnh tĩnh được khi mô hình đã sẵn sàng.

## Sử dụng

- Kéo ngưỡng tin cậy hoặc chọn 320 / 416 / 640: áp dụng vào khung hình kế tiếp sau khi cấu hình được nhận (khung hình đang suy luận sẽ hoàn tất trước).
- Tải ảnh lên: xem ảnh có khung, nhãn và bảng ý nghĩa tiếng Việt trong hộp thoại riêng. Ảnh tối đa 10 MB, 25 triệu điểm ảnh. Không lưu ảnh lên đĩa, không publish ảnh tải lên qua MQTT.
- Bảng và chỉ số cập nhật mỗi 200 ms. FPS tính bằng số khung / tổng thời gian xử lý vòng lặp trên tối đa 30 khung; độ trễ TB và p95 đo riêng suy luận, gồm tiền/hậu xử lý của YOLO. FPS thực tế phụ thuộc máy, camera và độ phân giải; không mặc định luôn đạt 22 FPS.
- Đồ thị lưu 60 mẫu (12 giây). Nhật ký giữ 20 dòng, giới hạn một sự kiện mỗi mã trong 2 giây để tránh tràn.

## MQTT và trạng thái lỗi

Broker `localhost:1883`, topic `vtsr/edge01/detections`, QoS 0, device ID `edge01`. Tái sử dụng `MqttPublisher`, chỉ gửi khi khung camera có phát hiện, giữ schema gốc (`class_id`, `class_name`, `meaning`, `confidence`, `bbox`), timestamp UTC và frame ID. Bbox là `[x, y, rộng, cao]` theo điểm ảnh gốc cho cả MQTT và HTTP/WS.

Kết nối bất đồng bộ và tự thử lại. Broker tắt không dừng video; chấm MQTT phản ánh trạng thái kết nối thực của client. Phát hiện mất kết nối có thể mất vài giây theo keepalive 5 giây. Vì broker nằm trên localhost, rút cáp mạng không nhất thiết làm mất MQTT; tắt Mosquitto để kiểm tra tình huống này. Không chạy đồng thời chương trình realtime cũ với cùng client ID `edge01`.

Lỗi model/camera xuất hiện trên giao diện và `/health`; server vẫn phục vụ trang. Khi thiếu model, đặt đủ ba file ONNX đúng kích thước rồi khởi động lại. Không cần Mosquitto để demo video/ảnh.

## API

- `GET /`: trang HTML.
- `GET /video_feed`: MJPEG; mỗi client nhận JPEG mới nhất, không xếp hàng frame cũ.
- `WS /ws/events`: số liệu và detections mỗi 200 ms, kèm trạng thái model/camera/MQTT và cấu hình hiện tại.
- `POST /upload`: multipart trường `file`; trả `detections`, `latency_ms`, `image_base64`, `mime_type`.
- `POST /config`: JSON với các trường tùy chọn `confidence` (0.1–0.9), `resolution` (320/416/640), `camera_enabled` (boolean).
- `GET /health`: trạng thái các thành phần, số liệu, cấu hình.

Suy luận và đọc camera chạy ngoài event loop. Dùng lại `FrameGrabber`, `draw_vietnamese`, `sign_meanings`; truy cập model từ camera và upload được khóa để tránh suy luận đồng thời trên cùng predictor. Upload có thể làm giảm FPS tạm thời. Ứng dụng dành cho demo nội bộ tại địa chỉ loopback, không có xác thực người dùng.

## Kiểm tra

Khi server đang chạy, kiểm tra API, ảnh thật ở ba độ phân giải, WebSocket, tắt camera, MJPEG và MQTT reconnect bằng:

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
```

Bài kiểm tra ảnh dùng một ảnh trong `dataset/test/images`, tạm đổi cấu hình rồi khôi phục. Bài kiểm tra MQTT dùng socket broker giả lập riêng trên cổng ngẫu nhiên, không tắt Mosquitto đang chạy. Phiên ONNX giới hạn tối đa 4 luồng CPU và tắt spinning để tránh ba model tranh chấp CPU lúc nhàn rỗi.
