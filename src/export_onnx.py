"""
export_onnx.py - Xuat mo hinh sang ONNX (va tuy chon INT8) de toi uu cho thiet bi bien.

    python export_onnx.py --weights weights/best.pt
    python export_onnx.py --weights weights/best.pt --half   # FP16 (can GPU)
"""
import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/best.pt")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--opset", type=int, default=12)
    ap.add_argument("--half", action="store_true", help="Xuat FP16 (yeu cau GPU)")
    ap.add_argument("--dynamic", action="store_true", help="Batch dong")
    args = ap.parse_args()

    model = YOLO(args.weights)
    path = model.export(
        format="onnx",
        imgsz=args.imgsz,
        opset=args.opset,
        simplify=True,      # gop/rut gon graph -> chay nhanh hon
        dynamic=args.dynamic,
        half=args.half,
    )

    pt_mb = Path(args.weights).stat().st_size / 1e6
    onnx_mb = Path(path).stat().st_size / 1e6
    print(f"\nDa xuat: {path}")
    print(f"Kich thuoc .pt   : {pt_mb:.2f} MB")
    print(f"Kich thuoc .onnx : {onnx_mb:.2f} MB  ({onnx_mb/pt_mb*100:.0f}% so voi .pt)")
    print("\nDua 2 con so nay vao bang so sanh truoc/sau toi uu trong bao cao tuan 5.")


if __name__ == "__main__":
    main()
