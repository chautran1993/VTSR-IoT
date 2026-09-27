"""Test the real MQTT client against an isolated local broker protocol fixture."""
import socket
import time
import unittest
from src.realtime_detect import MqttPublisher


class MqttTests(unittest.TestCase):
    def wait_for(self, predicate):
        end = time.monotonic() + 8
        while time.monotonic() < end:
            if predicate():
                return
            time.sleep(0.05)
        self.fail('MQTT state did not change')

    def test_disconnect_and_reconnect(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        listener.settimeout(8)
        publisher = MqttPublisher(host='127.0.0.1', port=listener.getsockname()[1],
                                  device_id='dashboard-test', enabled=True, async_connect=True)
        try:
            for attempt in range(2):
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    self.assertTrue(conn.recv(4096).startswith(b'\x10'))
                    conn.sendall(b'\x20\x02\x00\x00')
                    self.wait_for(publisher.client.is_connected)
                    publisher.publish({'detections': []}, qos=0)
                    self.assertTrue(conn.recv(4096).startswith(b'\x30'))
                self.wait_for(lambda: not publisher.client.is_connected())
        finally:
            publisher.close()
            listener.close()


if __name__ == '__main__':
    unittest.main()
