"""
convert_dataset.py
Chuyen bo du lieu tu dinh dang TensorFlow (nhan trong _annotations.csv, toa do pixel)
sang dinh dang YOLO (moi anh mot file .txt, toa do chuan hoa) va sinh data.yaml.

Thu tu lop duoc lay TRUC TIEP tu mo hinh best.pt de bao dam khong lech chi so lop.

Chay:
    python src\\convert_dataset.py --src "D:\\VNTS merge.v2i.tensorflow"
    python src\\convert_dataset.py --src <thu_muc_tf> --dst dataset --weights weights\\best.pt
"""

import argparse
import csv
import shutil
from collections import Counter
from pathlib import Path

import yaml
from ultralytics import YOLO

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True,
                    help="Thu muc goc dinh dang TensorFlow (chua train/valid/test)")
    ap.add_argument("--dst", default="dataset",
                    help="Thu muc dich dinh dang YOLO")
    ap.add_argument("--weights", default="weights/best.pt",
                    help="Trong so dung de lay thu tu lop")
    ap.add_argument("--keep-background", action="store_true",
                    help="Giu ca anh khong co doi tuong (nhan rong)")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    if not src.exists():
        print(f"[LOI] Khong tim thay thu muc: {src}")
        return

    print(f"Doc thu tu lop tu {args.weights} ...")
    names = YOLO(args.weights).names
    cls2id = {v: k for k, v in names.items()}
    print(f"  -> {len(names)} lop\n")

    missing = Counter()
    summary = []

    for split in ["train", "valid", "test"]:
        src_dir = src / split
        if not src_dir.exists():
            print(f"[BO QUA] khong co thu muc {split}")
            continue

        csv_path = src_dir / "_annotations.csv"
        if not csv_path.exists():
            print(f"[BO QUA] {split}: khong tim thay _annotations.csv")
            continue

        img_out = dst / split / "images"
        lbl_out = dst / split / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        rows_by_img = {}
        with open(csv_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows_by_img.setdefault(r["filename"], []).append(r)

        n_obj = 0
        for fname, rows in rows_by_img.items():
            img_src = src_dir / fname
            if not img_src.exists():
                continue
            shutil.copy(img_src, img_out / fname)

            lines = []
            for r in rows:
                cname = r["class"]
                if cname not in cls2id:
                    missing[cname] += 1
                    continue
                w, h = float(r["width"]), float(r["height"])
                x1, y1 = float(r["xmin"]), float(r["ymin"])
                x2, y2 = float(r["xmax"]), float(r["ymax"])
                # kep toa do trong khung anh de tranh gia tri am hoac > 1
                x1, x2 = max(0.0, min(x1, w)), max(0.0, min(x2, w))
                y1, y2 = max(0.0, min(y1, h)), max(0.0, min(y2, h))
                if x2 <= x1 or y2 <= y1:
                    continue
                lines.append(
                    f"{cls2id[cname]} {((x1 + x2) / 2) / w:.6f} "
                    f"{((y1 + y2) / 2) / h:.6f} "
                    f"{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}"
                )
                n_obj += 1

            (lbl_out / f"{Path(fname).stem}.txt").write_text(
                "\n".join(lines), encoding="utf-8")

        # anh nen: co trong thu muc nhung khong xuat hien trong CSV
        n_bg = 0
        if args.keep_background:
            for img in src_dir.iterdir():
                if img.suffix.lower() in IMG_EXT and not (img_out / img.name).exists():
                    shutil.copy(img, img_out / img.name)
                    (lbl_out / f"{img.stem}.txt").write_text("", encoding="utf-8")
                    n_bg += 1

        n_img = len(list(img_out.iterdir()))
        summary.append((split, n_img, n_obj, n_bg))
        print(f"{split:6s}: {n_img:5d} anh  |  {n_obj:5d} doi tuong"
              + (f"  |  +{n_bg} anh nen" if n_bg else ""))

    # ------------------------------------------------------------------
    cfg = {
        "path": str(dst.resolve()),
        "train": "train/images",
        "val": "valid/images",
        "test": "test/images",
        "nc": len(names),
        "names": [names[i] for i in range(len(names))],
    }
    with open(dst / "data.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)

    print(f"\nDa tao {dst / 'data.yaml'}")

    if missing:
        print("\n[CANH BAO] Lop co trong CSV nhung khong co trong mo hinh:")
        for k, v in missing.most_common():
            print(f"   {k}: {v} doi tuong bi bo qua")
    else:
        print("Tat ca lop trong CSV deu khop voi mo hinh.")

    print("\nBuoc tiep theo:")
    print(f'   yolo val model={args.weights} data={dst / "data.yaml"} '
          f'split=test imgsz=640 conf=0.35 iou=0.5 plots=True name=test_eval')


if __name__ == "__main__":
    main()
