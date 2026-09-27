"""
mqtt_monitor.py - Subscriber kiem chung luong du lieu IoT.
Dung de chung minh ban tin da di qua broker khi chua kip dung Node-RED,
va de quay video demo phan "dashboard".

    python mqtt_monitor.py --broker localhost --topic vtsr/edge01/detections
"""
import argparse
import collections
import json
import time

import paho.mqtt.client as mqtt

counter = collections.Counter()
start = time.time()
msg_count = 0


def on_connect(client, userdata, flags, reason_code, properties=None):
    topic = userdata["topic"]
    client.subscribe(topic, qos=0)
    print(f"[OK] Da ket noi broker, dang lang nghe topic '{topic}'\n")


def on_message(client, userdata, msg):
    global msg_count
    msg_count += 1
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print("[!] Ban tin khong phai JSON hop le")
        return

    for d in data.get("detections", []):
        counter[d["class_name"]] += 1

    names = ", ".join(f"{d['class_name']}({d['confidence']:.2f})"
                      for d in data.get("detections", []))
    print(f"[{data.get('frame_id')}] {data.get('device_id')} | "
          f"{data.get('fps')} FPS | {data.get('latency_ms')} ms | {names}")

    if msg_count % 50 == 0:
        elapsed = time.time() - start
        print(f"\n--- Thong ke sau {elapsed:.0f}s / {msg_count} ban tin ---")
        for cls, n in counter.most_common(10):
            print(f"    {cls:<28} {n}")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--topic", default="vtsr/edge01/detections")
    args = ap.parse_args()

    userdata = {"topic": args.topic}
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id="monitor", userdata=userdata)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id="monitor", userdata=userdata)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.broker, args.port, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
