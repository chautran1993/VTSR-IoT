"""Integration checks against a running dashboard; uses existing dependencies only."""
import asyncio
import json
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
import websockets

BASE = 'http://127.0.0.1:8000'
ROOT = Path(__file__).resolve().parents[1]


def request(path, data=None, content='application/json'):
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': content})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


class DashboardTests(unittest.TestCase):
    def test_dashboard(self):
        initial = request('/health')
        try:
            for _ in range(60):
                if request('/health')['model'].startswith('Sẵn sàng'):
                    break
                time.sleep(1)
            else:
                self.fail('Model did not become ready')
            raw = next((ROOT / 'dataset/test/images').glob('*.jpg')).read_bytes()
            body = (b'--test\r\nContent-Disposition: form-data; name="file"; filename="test.jpg"\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + raw + b'\r\n--test--\r\n')
            for size in (320, 416, 640):
                request('/config', json.dumps(dict(resolution=size, confidence=0.1)).encode())
                result = request('/upload', body, 'multipart/form-data; boundary=test')
                self.assertTrue(result['image_base64'])
                self.assertTrue(result['detections'])
                self.assertIn('meaning', result['detections'][0])
                print('ONNX', size, 'latency_ms', result['latency_ms'])
            with self.assertRaises(urllib.error.HTTPError) as error:
                request('/config', b'{"resolution":500}')
            self.assertEqual(error.exception.code, 422)
            bad = body.replace(raw, b'not an image')
            with self.assertRaises(urllib.error.HTTPError) as error:
                request('/upload', bad, 'multipart/form-data; boundary=test')
            self.assertEqual(error.exception.code, 400)
            request('/config', b'{"camera_enabled":false}')
            time.sleep(1)
            paused = request('/health')
            time.sleep(0.5)
            self.assertEqual(paused['frame_count'], request('/health')['frame_count'])
            self.assertEqual(paused['fps'], 0)
            self.assertFalse(paused['detections'])
            asyncio.run(self.check_ws())
            request('/config', b'{"camera_enabled":true,"resolution":416}')
            # Verify MJPEG when a physical camera is available; do not require one.
            for _ in range(12):
                state = request('/health')
                if state['camera'] == 'Camera đang hoạt động':
                    with urllib.request.urlopen(BASE + '/video_feed', timeout=10) as stream:
                        chunk = stream.read(256)
                        self.assertIn(b'Content-Type: image/jpeg', chunk)
                        self.assertIn(b'\xff\xd8', chunk)
                    print('MJPEG camera OK; fps', state['fps'])
                    break
                time.sleep(1)
        finally:
            request('/config', json.dumps({k: initial[k] for k in ('confidence', 'resolution', 'camera_enabled')}).encode())

    async def check_ws(self):
        async with websockets.connect('ws://127.0.0.1:8000/ws/events') as ws:
            times = []
            for _ in range(4):
                data = json.loads(await asyncio.wait_for(ws.recv(), 3))
                self.assertIn('latency_p95_ms', data)
                times.append(time.monotonic())
            self.assertTrue(all(0.12 < b-a < 0.7 for a, b in zip(times, times[1:])))


if __name__ == '__main__':
    unittest.main()
