"""
realtime_detect.py
Pipeline nhan dien bien bao giao thong thoi gian thuc (may tinh dong vai Edge Device).
Nguon anh: webcam (0) hoac video hanh trinh (.mp4).
Ket qua: ve bounding box + FPS len khung hinh, gui JSON qua MQTT, ghi log CSV.

Chay:
    python realtime_detect.py --weights weights/best.pt --source video/demo.mp4
    python realtime_detect.py --weights weights/best.pt --source 0 --mqtt
"""

import argparse
import csv
import json
import time
import threading
import queue
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

from sign_meanings import meaning_of, short_label

# ---------------------------------------------------------------------------
# Ve chu tieng Viet co dau len khung hinh.
# OpenCV khong ho tro Unicode nen phai ve qua PIL roi chuyen nguoc lai.
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]


def _load_font(size):
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


FONT_LABEL = _load_font(17)
FONT_HUD = _load_font(22)


def draw_vietnamese(frame_bgr, items, hud_text):
    """Ve nhan tieng Viet va dong HUD len khung hinh (BGR).

    items: danh sach (x1, y1, label) — nhan se ve phia tren hop gioi han.
    """
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    for x1, y1, label in items:
        box = draw.textbbox((0, 0), label, font=FONT_LABEL)
        tw, th = box[2] - box[0], box[3] - box[1]
        ty = y1 - th - 8
        if ty < 0:                       # nhan vuot len tren -> ve ben duoi
            ty = y1 + 4
        tx = min(x1, img.width - tw - 8)
        tx = max(tx, 0)
        draw.rectangle([tx, ty, tx + tw + 8, ty + th + 8], fill=(0, 190, 0))
        draw.text((tx + 4, ty + 2), label, font=FONT_LABEL, fill=(255, 255, 255))

    draw.rectangle([6, 6, 8 + draw.textlength(hud_text, font=FONT_HUD), 40],
                   fill=(0, 0, 0))
    draw.text((10, 9), hud_text, font=FONT_HUD, fill=(0, 230, 255))

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

# ----------------------------------------------------------------------------
# 1. Doc khung hinh tren luong rieng -> tranh nghen I/O lam tut FPS
# ----------------------------------------------------------------------------
class FrameGrabber:
    def __init__(self, source, drop_late=True):
        self.source = int(source) if str(source).isdigit() else source
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Khong mo duoc nguon anh: {source}")
        self.q = queue.Queue(maxsize=1 if drop_late else 64)
        self.stopped = False
        self.is_file = not str(source).isdigit()
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        while not self.stopped:
            ok, frame = self.cap.read()
            if not ok:
                self.stopped = True
                break
            if self.q.full():
                if self.is_file:
                    # Voi file video: khong bo khung -> giu du lieu danh gia
                    self.q.put(frame)
                    continue
                try:
                    self.q.get_nowait()  # bo khung cu (webcam: uu tien do tuoi)
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self, timeout=2.0):
        if self.stopped and self.q.empty():
            return None
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def release(self):
        self.stopped = True
        self.cap.release()


# ----------------------------------------------------------------------------
# 2. Publisher MQTT (tuy chon - chay duoc ca khi khong bat MQTT)
# ----------------------------------------------------------------------------
class MqttPublisher:
    def __init__(self, host="localhost", port=1883, topic="vtsr/edge01/detections",
                 device_id="edge01", enabled=False):
        self.enabled = enabled
        self.topic = topic
        self.device_id = device_id
        self.client = None
        if not enabled:
            return
        import paho.mqtt.client as mqtt
        try:  # paho-mqtt >= 2.0
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                      client_id=device_id)
        except (AttributeError, TypeError):  # paho-mqtt 1.x
            self.client = mqtt.Client(client_id=device_id)
        self.client.connect(host, port, keepalive=60)
        self.client.loop_start()
        print(f"[MQTT] Da ket noi {host}:{port} -> topic '{topic}'")

    def publish(self, payload, qos=0):
        if not self.enabled or self.client is None:
            return
        self.client.publish(self.topic, json.dumps(payload, ensure_ascii=False), qos=qos)

    def close(self):
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()


# ----------------------------------------------------------------------------
# 3. Vong lap chinh
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/best.pt",
                    help="Duong dan trong so .pt hoac .onnx")
    ap.add_argument("--source", default="0", help="0 = webcam, hoac duong dan video")
    ap.add_argument("--conf", type=float, default=0.35, help="Nguong tin cay")
    ap.add_argument("--iou", type=float, default=0.5, help="Nguong IoU cho NMS")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu", help="cpu | 0 (GPU)")
    ap.add_argument("--mqtt", action="store_true", help="Bat gui ket qua qua MQTT")
    ap.add_argument("--broker", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="vtsr/edge01/detections")
    ap.add_argument("--device-id", default="edge01")
    ap.add_argument("--log", default="logs/runtime_log.csv")
    ap.add_argument("--save-video", default="", help="Duong dan file mp4 de luu demo")
    ap.add_argument("--no-show", action="store_true", help="Khong mo cua so hien thi")
    args = ap.parse_args()

    model = YOLO(args.weights)
    names = model.names
    grabber = FrameGrabber(args.source)
    publisher = MqttPublisher(args.broker, args.port, args.topic,
                              args.device_id, enabled=args.mqtt)

    Path(args.log).parent.mkdir(parents=True, exist_ok=True)
    log_file = open(args.log, "w", newline="", encoding="utf-8")
    logger = csv.writer(log_file)
    logger.writerow(["frame_id", "timestamp", "latency_ms", "fps", "num_detections"])

    writer = None
    frame_id, fps, t_prev = 0, 0.0, time.time()
    latencies = []

    print("[INFO] Dang chay... nhan 'q' de dung.")
    try:
        while True:
            frame = grabber.read()
            if frame is None:
                break
            frame_id += 1

            t0 = time.perf_counter()
            results = model.predict(frame, conf=args.conf, iou=args.iou,
                                    imgsz=args.imgsz, device=args.device,
                                    verbose=False)[0]
            latency_ms = (time.perf_counter() - t0) * 1000
            latencies.append(latency_ms)

            # FPS trung binh truot (he so 0.9 de so lieu on dinh)
            t_now = time.time()
            inst_fps = 1.0 / max(t_now - t_prev, 1e-6)
            fps = inst_fps if frame_id == 1 else 0.9 * fps + 0.1 * inst_fps
            t_prev = t_now

            detections = []
            labels = []
            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
                cls_name = names[cls_id]
                detections.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "meaning": meaning_of(cls_name),
                    "confidence": round(conf, 3),
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                })
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 190, 0), 2)
                labels.append((x1, y1, short_label(cls_name, conf)))

            hud = (f"FPS: {fps:.1f}  |  Do tre: {latency_ms:.1f} ms  "
                   f"|  So bien: {len(detections)}")
            frame = draw_vietnamese(frame, labels, hud)

            # Ban tin JSON theo dung luoc do da thong nhat o bao cao tuan 3
            if detections:
                payload = {
                    "device_id": args.device_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "frame_id": frame_id,
                    "detections": detections,
                    "latency_ms": round(latency_ms, 2),
                    "fps": round(fps, 2),
                }
                publisher.publish(payload, qos=0)

            logger.writerow([frame_id, datetime.now().isoformat(),
                             round(latency_ms, 2), round(fps, 2), len(detections)])

            if args.save_video:
                if writer is None:
                    Path(args.save_video).parent.mkdir(parents=True, exist_ok=True)
                    h, w = frame.shape[:2]
                    writer = cv2.VideoWriter(args.save_video,
                                             cv2.VideoWriter_fourcc(*"mp4v"),
                                             20.0, (w, h))
                writer.write(frame)

            if not args.no_show:
                cv2.imshow("VTSR - Edge Device", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        grabber.release()
        if writer is not None:
            writer.release()
        log_file.close()
        publisher.close()
        cv2.destroyAllWindows()

    if latencies:
        avg = sum(latencies) / len(latencies)
        p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
        print(f"\n[KET QUA] {frame_id} khung hinh | do tre TB {avg:.1f} ms "
              f"| p95 {p95:.1f} ms | FPS TB {1000/avg:.1f}")
        print(f"[KET QUA] Log chi tiet: {args.log}")


if __name__ == "__main__":
    main()
