"""Local Vietnamese traffic-sign dashboard; one inference worker, latest JPEG only."""
import asyncio
import base64
import logging
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
TOPIC = 'vtsr/edge01/detections'
log = logging.getLogger(__name__)


class Config(BaseModel):
    confidence: float | None = Field(default=None, ge=0.1, le=0.9)
    resolution: Literal[320, 416, 640] | None = None
    camera_enabled: bool | None = None


class Engine:
    def __init__(self):
        self.lock = threading.RLock()
        self.infer_lock = threading.Lock()
        self.stop = threading.Event()
        self.started = time.monotonic()
        self.confidence, self.resolution, self.camera_enabled = 0.35, 416, True
        self.models = {}
        self.publisher = None
        self.model_state = 'Đang tải mô hình'
        self.camera_state = 'Đang mở camera'
        self.mqtt_error = ''
        self.count = self.sequence = 0
        self.jpeg = None
        self.detections = []
        self.latencies, self.intervals = deque(maxlen=30), deque(maxlen=30)
        self.thread = threading.Thread(target=self.run, daemon=True)

    def snapshot(self):
        with self.lock:
            connected = bool(self.publisher and self.publisher.client and self.publisher.client.is_connected())
            return dict(fps=round(len(self.intervals) / sum(self.intervals), 1) if self.intervals else 0,
                        latency_ms=round(float(np.mean(self.latencies)), 1) if self.latencies else 0,
                        latency_p95_ms=round(float(np.percentile(self.latencies, 95)), 1) if self.latencies else 0,
                        mqtt_connected=connected, frame_count=self.count,
                        uptime_s=round(time.monotonic()-self.started, 1), detections=list(self.detections),
                        model=self.model_state, camera=self.camera_state,
                        mqtt='Đã kết nối' if connected else (self.mqtt_error or 'Mất kết nối — đang thử kết nối lại'),
                        topic=TOPIC, confidence=self.confidence, resolution=self.resolution,
                        camera_enabled=self.camera_enabled)

    def predict(self, frame, confidence, resolution):
        from .realtime_detect import draw_vietnamese
        from .sign_meanings import meaning_of, group_of, short_label
        with self.infer_lock:
            model = self.models.get(resolution)
            if model is None:
                raise RuntimeError('Mô hình chưa sẵn sàng')
            start = time.perf_counter()
            result = model.predict(frame, conf=confidence, iou=0.5, imgsz=resolution,
                                   device='cpu', verbose=False)[0]
            latency = (time.perf_counter()-start)*1000
        detections, mqtt_items, labels = [], [], []
        for box in result.boxes:
            cls = int(box.cls[0])
            code, conf = result.names[cls], round(float(box.conf[0]), 3)
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0]]
            bbox = [x1, y1, x2-x1, y2-y1]
            detections.append(dict(code=code, meaning=meaning_of(code), group=group_of(code), confidence=conf, bbox=bbox))
            mqtt_items.append(dict(class_id=cls, class_name=code, meaning=meaning_of(code), confidence=conf, bbox=bbox))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 190, 0), 2)
            labels.append((x1, y1, short_label(code, conf)))
        frame = draw_vietnamese(frame, labels, f'Độ trễ: {latency:.1f} ms | Số biển: {len(detections)}')
        ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if not ok:
            raise RuntimeError('Không mã hóa được ảnh')
        return detections, mqtt_items, latency, encoded.tobytes()

    def run(self):
        grabber = None
        try:
            from .realtime_detect import FrameGrabber, MqttPublisher
            from ultralytics import YOLO
            import onnxruntime as ort
            try:
                self.publisher = MqttPublisher(enabled=True, async_connect=True)
            except Exception as exc:
                self.mqtt_error = f'Không khởi tạo được MQTT: {exc}'
            for size, filename in [(416, 'best_416.onnx'), (320, 'best_320.onnx'), (640, 'best.onnx')]:
                path = ROOT / 'weights' / filename
                if not path.exists():
                    path = ROOT / 'models' / filename
                model = YOLO(str(path), task='detect')
                model.predict(np.zeros((size, size, 3), dtype=np.uint8), imgsz=size, device='cpu', verbose=False)
                # Bound CPU threads so the three cached sessions do not contend.
                options = ort.SessionOptions()
                options.intra_op_num_threads = min(4, os.cpu_count() or 1)
                options.add_session_config_entry('session.intra_op.allow_spinning', '0')
                model.predictor.model.session = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
                with self.infer_lock:
                    self.models[size] = model
            self.model_state = 'Sẵn sàng · ONNX Runtime · CPU'
            while not self.stop.is_set():
                with self.lock:
                    enabled, confidence, size = self.camera_enabled, self.confidence, self.resolution
                if not enabled:
                    if grabber:
                        grabber.release()
                        grabber = None
                    self.clear_camera('Camera đã tắt')
                    self.stop.wait(0.1)
                    continue
                if grabber is None:
                    try:
                        grabber = FrameGrabber(os.environ.get('VTSR_CAMERA', '0'))
                    except Exception:
                        self.clear_camera('Không mở được camera — sẽ thử lại sau 3 giây')
                        self.stop.wait(3)
                        continue
                start = time.perf_counter()
                frame = grabber.read(timeout=0.5)
                if frame is None:
                    grabber.release()
                    grabber = None
                    self.clear_camera('Mất tín hiệu camera — đang kết nối lại')
                    self.stop.wait(1)
                    continue
                try:
                    detections, items, latency, jpeg = self.predict(frame, confidence, size)
                except Exception as exc:
                    self.clear_camera(f'Lỗi nhận diện: {exc}')
                    self.stop.wait(1)
                    continue
                with self.lock:
                    if not self.camera_enabled:
                        continue
                    self.latencies.append(latency)
                    self.intervals.append(time.perf_counter()-start)
                    self.count += 1
                    self.sequence += 1
                    self.jpeg, self.detections = jpeg, detections
                    self.camera_state = 'Camera đang hoạt động'
                    state = self.snapshot()
                if items and self.publisher:
                    try:
                        self.publisher.publish(dict(device_id='edge01', timestamp=datetime.now(timezone.utc).isoformat(),
                            frame_id=self.count, detections=items, latency_ms=round(latency, 2), fps=round(state['fps'], 2)), qos=0)
                    except Exception:
                        log.exception('Không gửi được MQTT')
        except Exception as exc:
            log.exception('Không khởi tạo được bộ nhận diện')
            self.model_state = f'Lỗi mô hình: {exc}'
            self.clear_camera('Camera chưa chạy do lỗi mô hình')
        finally:
            if grabber:
                grabber.release()
            if self.publisher:
                self.publisher.close()

    def clear_camera(self, message):
        with self.lock:
            self.camera_state = message
            self.jpeg, self.detections = None, []
            self.latencies.clear()
            self.intervals.clear()


@asynccontextmanager
async def lifespan(app):
    app.state.engine = Engine()
    app.state.engine.thread.start()
    yield
    app.state.engine.stop.set()
    await asyncio.to_thread(app.state.engine.thread.join, 10)


app = FastAPI(title='Nhận diện biển báo giao thông Việt Nam', lifespan=lifespan)


@app.get('/')
async def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/health')
async def health():
    return app.state.engine.snapshot()


@app.post('/config')
async def config(settings: Config):
    engine = app.state.engine
    with engine.lock:
        for name, value in settings.model_dump(exclude_none=True).items():
            setattr(engine, name, value)
        if settings.camera_enabled is False:
            engine.clear_camera('Camera đã tắt')
    return engine.snapshot()


@app.get('/video_feed')
async def video_feed():
    async def frames():
        sequence = -1
        while not app.state.engine.stop.is_set():
            engine = app.state.engine
            with engine.lock:
                jpeg, current = engine.jpeg, engine.sequence
            if jpeg is not None and sequence != current:
                sequence = current
                yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg + b'\r\n'
            await asyncio.sleep(0.01)
    return StreamingResponse(frames(), media_type='multipart/x-mixed-replace; boundary=frame',
                             headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})


@app.websocket('/ws/events')
async def events(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json(app.state.engine.snapshot())
            await asyncio.sleep(0.2)
    except (WebSocketDisconnect, RuntimeError, OSError):
        pass


@app.post('/upload')
async def upload(file: UploadFile = File(...)):
    try:
        raw = await file.read(10 * 1024 * 1024 + 1)
    finally:
        await file.close()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, 'Ảnh phải nhỏ hơn 10 MB')
    engine = app.state.engine
    with engine.lock:
        confidence, resolution = engine.confidence, engine.resolution
    def process():
        frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('Tệp không phải ảnh hợp lệ')
        if frame.shape[0] * frame.shape[1] > 25_000_000:
            raise ValueError('Ảnh không được vượt quá 25 triệu điểm ảnh')
        detections, _, latency, jpeg = engine.predict(frame, confidence, resolution)
        return dict(detections=detections, latency_ms=round(latency, 2),
                    image_base64=base64.b64encode(jpeg).decode(), mime_type='image/jpeg')
    try:
        return await asyncio.to_thread(process)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

