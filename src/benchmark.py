"""
benchmark.py - Do FPS / do tre / kich thuoc mo hinh, so sanh .pt va .onnx tren CPU.
Ket qua xuat ra CSV de dan thang vao bang danh gia hieu nang (tuan 6).

    python benchmark.py --models weights/best.pt weights/best.onnx --source video/demo.mp4
"""
import argparse
import csv
import statistics
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def bench(weights, frames, imgsz, conf, iou, device, warmup=5):
    model = YOLO(weights)
    for _ in range(warmup):  # bo qua vai lan chay dau (khoi tao/JIT)
        model.predict(frames[0], imgsz=imgsz, conf=conf, iou=iou,
                      device=device, verbose=False)

    lat = []
    for f in frames:
        t0 = time.perf_counter()
        model.predict(f, imgsz=imgsz, conf=conf, iou=iou, device=device, verbose=False)
        lat.append((time.perf_counter() - t0) * 1000)

    lat_sorted = sorted(lat)
    return {
        "model": Path(weights).name,
        "size_mb": round(Path(weights).stat().st_size / 1e6, 2),
        "n_frames": len(lat),
        "latency_mean_ms": round(statistics.mean(lat), 2),
        "latency_median_ms": round(statistics.median(lat), 2),
        "latency_p95_ms": round(lat_sorted[int(0.95 * len(lat)) - 1], 2),
        "fps_mean": round(1000 / statistics.mean(lat), 2),
    }


def load_frames(source, n):
    if Path(source).is_dir():
        files = sorted([p for p in Path(source).iterdir()
                        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])[:n]
        return [cv2.imread(str(p)) for p in files]
    cap = cv2.VideoCapture(source)
    frames = []
    while len(frames) < n:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if not frames:
        raise RuntimeError(f"Khong doc duoc khung hinh tu {source}")
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["weights/best.pt"])
    ap.add_argument("--source", required=True, help="Video hoac thu muc anh test")
    ap.add_argument("--n", type=int, default=200, help="So khung hinh do")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default="logs/benchmark.csv")
    args = ap.parse_args()

    frames = load_frames(args.source, args.n)
    print(f"Da nap {len(frames)} khung hinh. Bat dau do tren '{args.device}'...\n")

    rows = [bench(m, frames, args.imgsz, args.conf, args.iou, args.device)
            for m in args.models]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    hdr = list(rows[0].keys())
    print(" | ".join(h.ljust(18) for h in hdr))
    print("-" * (21 * len(hdr)))
    for r in rows:
        print(" | ".join(str(r[h]).ljust(18) for h in hdr))
    print(f"\nDa luu: {args.out}")


if __name__ == "__main__":
    main()
