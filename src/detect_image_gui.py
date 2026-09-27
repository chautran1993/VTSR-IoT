"""
detect_image_gui.py
Ung dung giao dien do hoa: chon anh tu may -> nhan dien bien bao -> hien thi ket qua.
Dung cho phan demo cua do an. Khong can Internet, khong can thu vien ngoai
ngoai nhung gi da cai trong requirements.txt.

Chay:
    python src\\detect_image_gui.py
    python src\\detect_image_gui.py --weights weights\\best.pt
"""

import argparse
import csv
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk
from ultralytics import YOLO

from sign_meanings import SIGN_MEANINGS, group_of, meaning_of


class App:
    def __init__(self, root, weights, conf, iou, imgsz):
        self.root = root
        self.conf, self.iou, self.imgsz = conf, iou, imgsz
        self.current_image = None      # anh da ve box (BGR)
        self.current_path = None
        self.history = []

        root.title("Hệ thống nhận diện biển báo giao thông Việt Nam — Demo ảnh tĩnh")
        root.geometry("1180x760")
        root.configure(bg="#f2f2f2")

        # --- Thanh tieu de ---
        header = tk.Frame(root, bg="#1f3864", height=60)
        header.pack(fill="x")
        tk.Label(header, text="NHẬN DIỆN BIỂN BÁO GIAO THÔNG VIỆT NAM",
                 bg="#1f3864", fg="white",
                 font=("Segoe UI", 15, "bold")).pack(pady=14)

        # --- Thanh cong cu ---
        bar = tk.Frame(root, bg="#f2f2f2")
        bar.pack(fill="x", padx=12, pady=8)

        tk.Button(bar, text="  Chọn ảnh  ", command=self.choose_image,
                  font=("Segoe UI", 10, "bold"), bg="#2e75b6", fg="white",
                  relief="flat", padx=14, pady=7, cursor="hand2").pack(side="left")

        tk.Button(bar, text="  Chọn thư mục  ", command=self.choose_folder,
                  font=("Segoe UI", 10), bg="#548235", fg="white",
                  relief="flat", padx=14, pady=7, cursor="hand2").pack(side="left", padx=6)

        tk.Button(bar, text="  Lưu ảnh kết quả  ", command=self.save_image,
                  font=("Segoe UI", 10), bg="#7f7f7f", fg="white",
                  relief="flat", padx=14, pady=7, cursor="hand2").pack(side="left")

        tk.Button(bar, text="  Xuất CSV  ", command=self.export_csv,
                  font=("Segoe UI", 10), bg="#7f7f7f", fg="white",
                  relief="flat", padx=14, pady=7, cursor="hand2").pack(side="left", padx=6)

        tk.Label(bar, text="Ngưỡng tin cậy:", bg="#f2f2f2",
                 font=("Segoe UI", 10)).pack(side="left", padx=(24, 4))
        self.conf_var = tk.DoubleVar(value=conf)
        tk.Scale(bar, from_=0.10, to=0.90, resolution=0.05, orient="horizontal",
                 variable=self.conf_var, length=170, bg="#f2f2f2",
                 highlightthickness=0, command=self.on_conf_change).pack(side="left")

        # --- Than: anh ben trai, ket qua ben phai ---
        body = tk.Frame(root, bg="#f2f2f2")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        left = tk.LabelFrame(body, text=" Ảnh đầu vào ", bg="white",
                             font=("Segoe UI", 10, "bold"), fg="#1f3864")
        left.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Label(left, bg="white",
                               text="\n\nChọn một ảnh để bắt đầu nhận diện\n\n"
                                    "Hỗ trợ: .jpg  .jpeg  .png  .bmp",
                               font=("Segoe UI", 11), fg="#999999")
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)

        right = tk.LabelFrame(body, text=" Kết quả nhận diện ", bg="white",
                              font=("Segoe UI", 10, "bold"), fg="#1f3864", width=470)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        cols = ("stt", "code", "meaning", "conf")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=11)
        self.tree.heading("stt", text="#")
        self.tree.heading("code", text="Mã biển")
        self.tree.heading("meaning", text="Ý nghĩa")
        self.tree.heading("conf", text="Tin cậy")
        self.tree.column("stt", width=36, anchor="center")
        self.tree.column("code", width=76, anchor="center")
        self.tree.column("meaning", width=190, anchor="w")
        self.tree.column("conf", width=64, anchor="center")
        self.tree.pack(fill="x", padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        tk.Label(right, text="Chi tiết biển báo được chọn:", bg="white",
                 font=("Segoe UI", 9, "bold"), fg="#1f3864",
                 anchor="w").pack(fill="x", padx=8)
        self.detail = tk.Text(right, height=9, wrap="word", bg="#f8f8f8",
                              font=("Segoe UI", 10), relief="flat", padx=8, pady=8)
        self.detail.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.detail.insert("1.0", "Chọn một dòng trong bảng để xem chi tiết.")
        self.detail.config(state="disabled")

        # --- Thanh trang thai ---
        self.status = tk.Label(root, text="Đang tải mô hình...", bd=1,
                               relief="sunken", anchor="w", bg="#e8e8e8",
                               font=("Segoe UI", 9), padx=8)
        self.status.pack(side="bottom", fill="x")

        root.update()
        self.model = YOLO(weights)
        self.names = self.model.names
        self.set_status(f"Sẵn sàng — mô hình {Path(weights).name}, "
                        f"{len(self.names)} lớp biển báo")

    # ------------------------------------------------------------------
    def set_status(self, text):
        self.status.config(text=text)
        self.root.update_idletasks()

    def on_conf_change(self, _=None):
        if self.current_path:
            self.run(self.current_path)

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Chọn ảnh biển báo giao thông",
            filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp *.webp"), ("Tất cả", "*.*")])
        if path:
            self.run(path)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if not folder:
            return
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        files = sorted([p for p in Path(folder).iterdir()
                        if p.suffix.lower() in exts])
        if not files:
            messagebox.showwarning("Không có ảnh",
                                   "Thư mục này không chứa ảnh nào.")
            return
        self.set_status(f"Đang xử lý {len(files)} ảnh...")
        for f in files:
            self.run(str(f))
            self.root.update()
        messagebox.showinfo("Hoàn tất",
                            f"Đã xử lý {len(files)} ảnh.\n"
                            f"Tổng số biển báo phát hiện: {len(self.history)}")

    # ------------------------------------------------------------------
    def run(self, path):
        img = cv2.imread(path)
        if img is None:
            messagebox.showerror("Lỗi", f"Không đọc được ảnh:\n{path}")
            return

        self.current_path = path
        conf = self.conf_var.get()
        self.set_status(f"Đang nhận diện: {Path(path).name} ...")

        res = self.model.predict(img, conf=conf, iou=self.iou,
                                 imgsz=self.imgsz, verbose=False)[0]

        for row in self.tree.get_children():
            self.tree.delete(row)

        dets = []
        for b in res.boxes:
            cid = int(b.cls[0])
            dets.append({
                "code": self.names[cid],
                "conf": float(b.conf[0]),
                "xyxy": [int(v) for v in b.xyxy[0]],
            })
        dets.sort(key=lambda d: -d["conf"])

        for i, d in enumerate(dets, 1):
            x1, y1, x2, y2 = d["xyxy"]
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 200, 0), 3)
            label = f"{i}. {d['code']} {d['conf']:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(img, (x1, max(y1 - th - 10, 0)),
                          (x1 + tw + 8, y1), (0, 200, 0), -1)
            cv2.putText(img, label, (x1 + 4, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            self.tree.insert("", "end", values=(i, d["code"],
                                               meaning_of(d["code"]),
                                               f"{d['conf']:.3f}"))
            self.history.append({
                "file": Path(path).name, "code": d["code"],
                "meaning": meaning_of(d["code"]),
                "confidence": round(d["conf"], 3),
                "bbox": f"{x1},{y1},{x2},{y2}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        self.current_image = img
        self.show(img)

        if dets:
            self.tree.selection_set(self.tree.get_children()[0])
            self.show_detail(dets[0])
            self.set_status(f"{Path(path).name} — phát hiện {len(dets)} biển báo "
                            f"(ngưỡng {conf:.2f})")
        else:
            self.show_detail(None)
            self.set_status(f"{Path(path).name} — không phát hiện biển báo nào. "
                            f"Thử hạ ngưỡng tin cậy.")

    def show(self, img_bgr):
        h, w = img_bgr.shape[:2]
        max_w, max_h = 700, 540
        scale = min(max_w / w, max_h / h, 1.0)
        disp = cv2.resize(img_bgr, (int(w * scale), int(h * scale)))
        rgb = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.canvas.config(image=photo, text="")
        self.canvas.image = photo

    def on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        self.show_detail({"code": str(vals[1]), "conf": float(vals[3])})

    def show_detail(self, d):
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        if d is None:
            self.detail.insert("1.0",
                               "Không phát hiện biển báo nào trong ảnh.\n\n"
                               "Gợi ý: hạ ngưỡng tin cậy xuống 0.20–0.25, "
                               "hoặc thử ảnh khác rõ nét hơn.")
        else:
            code = d["code"]
            self.detail.insert("1.0",
                               f"Mã biển báo:\n    {code}\n\n"
                               f"Ý nghĩa:\n    {meaning_of(code)}\n\n"
                               f"Nhóm biển:\n    {group_of(code)}\n\n"
                               f"Độ tin cậy:\n    {d['conf']:.1%}\n")
        self.detail.config(state="disabled")

    # ------------------------------------------------------------------
    def save_image(self):
        if self.current_image is None:
            messagebox.showwarning("Chưa có ảnh", "Hãy chọn và nhận diện một ảnh trước.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            initialfile=f"ketqua_{Path(self.current_path).stem}.jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if path:
            cv2.imwrite(path, self.current_image)
            self.set_status(f"Đã lưu ảnh kết quả: {path}")

    def export_csv(self):
        if not self.history:
            messagebox.showwarning("Chưa có dữ liệu", "Chưa nhận diện ảnh nào.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="ket_qua_nhan_dien.csv",
            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(self.history[0].keys()))
            w.writeheader()
            w.writerows(self.history)
        self.set_status(f"Đã xuất {len(self.history)} dòng ra {path}")
        messagebox.showinfo("Hoàn tất", f"Đã xuất {len(self.history)} kết quả.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/best.pt")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--imgsz", type=int, default=640)
    args = ap.parse_args()

    if not os.path.exists(args.weights):
        print(f"Khong tim thay trong so: {args.weights}")
        print("Chay lenh nay tu thu muc goc du an VTSR-IoT.")
        return

    root = tk.Tk()
    App(root, args.weights, args.conf, args.iou, args.imgsz)
    root.mainloop()


if __name__ == "__main__":
    main()
