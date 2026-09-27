#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ve_bieu_do_chuong4.py
Sinh 5 bieu do cho Chuong 4 cua bao cao do an.

Chay:
    python ve_bieu_do_chuong4.py

Ket qua: 5 tep PNG 300 dpi trong thu muc docs/hinh/
Chen truc tiep vao Word bang Insert > Pictures.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# ---------------------------------------------------------------------------
# Thiet lap chung: font chu Times New Roman de dong bo voi than bai bao cao.
# Neu may khong co Times New Roman, tu dong chuyen sang phong chu thay the
# co day du dau tieng Viet.
# ---------------------------------------------------------------------------
import matplotlib.font_manager as fm

_available = {f.name for f in fm.fontManager.ttflist}
for _candidate in ("Times New Roman", "Liberation Serif", "DejaVu Serif"):
    if _candidate in _available:
        FONT = _candidate
        break
else:
    FONT = "serif"

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#8A8A8A",
    "axes.linewidth": 0.8,
    "grid.color": "#DDDDDD",
    "grid.linewidth": 0.6,
})

# Bang mau da kiem chung do phan biet voi nguoi mu mau (Delta-E protan 23,1)
BLUE = "#2E75B6"      # chuoi so lieu thu nhat
ORANGE = "#ED7D31"    # chuoi so lieu thu hai
# Thang don sac cho bien do phan giai (du lieu co thu tu: 640 > 416 > 320)
SEQ = ["#1F4E79", "#4F8CC9", "#A6C8E8"]
INK = "#333333"
MUTED = "#666666"

OUT = Path("docs/hinh")
OUT.mkdir(parents=True, exist_ok=True)


def _grid(ax, axis="y"):
    ax.grid(axis=axis, zorder=0)
    ax.set_axisbelow(True)


def _dau_phay(ax, so_le=1):
    """Đổi dấu chấm thập phân trên trục y thành dấu phẩy theo chuẩn tiếng Việt."""
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v:.{so_le}f}".replace(".", ",")))


# ===========================================================================
# HINH 4.9 — Suy giam do chinh xac theo do phan giai anh dau vao
# ===========================================================================
def hinh_4_9():
    res = ["320×320", "416×416", "640×640"]
    map50 = [0.839, 0.898, 0.942]
    map5095 = [0.656, 0.713, 0.774]

    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    _grid(ax)

    ax.plot(res, map50, marker="o", markersize=8, linewidth=2,
            color=BLUE, label="mAP@0.5", zorder=3)
    ax.plot(res, map5095, marker="s", markersize=8, linewidth=2,
            color=ORANGE, label="mAP@0.5:0.95", zorder=3)

    for x, y in zip(res, map50):
        ax.annotate(f"{y:.3f}".replace(".", ","), (x, y),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=10, color=INK)
    for x, y in zip(res, map5095):
        ax.annotate(f"{y:.3f}".replace(".", ","), (x, y),
                    textcoords="offset points", xytext=(0, -16),
                    ha="center", fontsize=10, color=INK)

    ax.set_xlabel("Độ phân giải ảnh đầu vào")
    ax.set_ylabel("Giá trị chỉ số")
    ax.set_ylim(0.58, 1.01)
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    _dau_phay(ax)
    ax.legend(frameon=False, loc="lower right")

    fig.savefig(OUT / "hinh_4_9_map_theo_do_phan_giai.png")
    plt.close(fig)
    print("  Đã tạo hinh_4_9_map_theo_do_phan_giai.png")


# ===========================================================================
# HINH 4.10 — Muc suy giam AP theo tung lop khi giam do phan giai
# ===========================================================================
def hinh_4_10():
    lop = ["R.301e", "R.434", "R.302a", "P.102", "W.202a", "W.203b"]
    v640 = [0.962, 0.780, 0.858, 0.813, 0.995, 0.995]
    v416 = [0.481, 0.621, 0.700, 0.760, 0.995, 0.945]
    v320 = [0.395, 0.518, 0.614, 0.686, 0.933, 0.995]

    x = range(len(lop))
    w = 0.26

    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    _grid(ax)

    ax.bar([i - w for i in x], v640, w * 0.92, label="640 px",
           color=SEQ[0], zorder=3)
    ax.bar(list(x), v416, w * 0.92, label="416 px",
           color=SEQ[1], zorder=3)
    ax.bar([i + w for i in x], v320, w * 0.92, label="320 px",
           color=SEQ[2], zorder=3)

    ax.set_xticks(list(x))
    ax.set_xticklabels(lop)
    ax.set_xlabel("Mã lớp biển báo")
    ax.set_ylabel("AP tại ngưỡng IoU 0,5")
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_locator(MultipleLocator(0.2))
    _dau_phay(ax)
    ax.legend(frameon=False, ncol=3, loc="upper left")

    fig.savefig(OUT / "hinh_4_10_suy_giam_theo_lop.png")
    plt.close(fig)
    print("  Đã tạo hinh_4_10_suy_giam_theo_lop.png")


# ===========================================================================
# HINH 4.12 — So sanh do tre suy luan giua GPU va CPU
# ===========================================================================
def hinh_4_12():
    nen = ["NVIDIA Tesla T4\n(GPU)", "Intel Core i7-1260P\n(CPU)"]
    do_tre = [8.5, 140.1]

    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    _grid(ax)

    bars = ax.bar(nen, do_tre, 0.5, color=[BLUE, ORANGE], zorder=3)
    for b, v in zip(bars, do_tre):
        ax.annotate(f"{v:.1f} ms".replace(".", ","),
                    (b.get_x() + b.get_width() / 2, v),
                    textcoords="offset points", xytext=(0, 5),
                    ha="center", fontsize=11, color=INK)

    ax.set_ylabel("Độ trễ suy luận trung bình (ms)")
    ax.set_ylim(0, 165)

    ax.annotate("Chênh lệch\n16,48 lần",
                xy=(0.76, 70), xytext=(0.42, 62),
                fontsize=10, color=MUTED, ha="center", va="center",
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))

    fig.savefig(OUT / "hinh_4_12_gpu_vs_cpu.png")
    plt.close(fig)
    print("  Đã tạo hinh_4_12_gpu_vs_cpu.png")


# ===========================================================================
# HINH 4.13 — Do tre trung binh va p95 theo tung cau hinh
# ===========================================================================
def hinh_4_13():
    cauhinh = ["PyTorch\n640", "ONNX\n640", "PyTorch\n416",
               "ONNX\n416", "PyTorch\n320", "ONNX\n320"]
    tb = [113.45, 120.19, 53.94, 45.28, 38.68, 28.37]
    p95 = [147.11, 209.69, 74.08, 48.42, 57.48, 31.08]

    x = range(len(cauhinh))
    w = 0.38

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    _grid(ax)

    ax.bar([i - w / 2 for i in x], tb, w * 0.92,
           label="Độ trễ trung bình", color=BLUE, zorder=3)
    ax.bar([i + w / 2 for i in x], p95, w * 0.92,
           label="Độ trễ phân vị 95 (p95)", color=ORANGE, zorder=3)

    for i, (a, b) in enumerate(zip(tb, p95)):
        ax.annotate(f"{a:.0f}", (i - w / 2, a), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=9, color=INK)
        ax.annotate(f"{b:.0f}", (i + w / 2, b), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=9, color=INK)

    ax.set_xticks(list(x))
    ax.set_xticklabels(cauhinh)
    ax.set_xlabel("Cấu hình runtime và độ phân giải")
    ax.set_ylabel("Độ trễ (ms)")
    ax.set_ylim(0, 245)
    ax.legend(frameon=False, ncol=2, loc="upper right")

    # Danh dau cau hinh khuyen nghi
    ax.annotate("Cấu hình khuyến nghị\nhai giá trị gần nhau",
                xy=(3, 50), xytext=(3.15, 120),
                fontsize=9, color=MUTED, ha="left",
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))

    fig.savefig(OUT / "hinh_4_13_do_tre_tb_va_p95.png")
    plt.close(fig)
    print("  Đã tạo hinh_4_13_do_tre_tb_va_p95.png")


# ===========================================================================
# HINH 4.15 — Duong cong danh doi do chinh xac va toc do
# ===========================================================================
def hinh_4_15():
    diem = [
        # (FPS, mAP@0.5, nhan, lech_x, lech_y)
        (8.81, 0.942, "PyTorch · 640", -26, 12),
        (8.32, 0.942, "ONNX · 640",   -10, -18),
        (18.54, 0.898, "PyTorch · 416", 8,  6),
        (22.08, 0.898, "ONNX · 416",    6, -18),
        (25.85, 0.839, "PyTorch · 320", 8,  6),
        (35.25, 0.839, "ONNX · 320",  -18, -20),
    ]

    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    _grid(ax, axis="both")

    # Duong noi cac cau hinh PyTorch va ONNX
    pt = [(d[0], d[1]) for d in diem if "PyTorch" in d[2]]
    on = [(d[0], d[1]) for d in diem if "ONNX" in d[2]]
    ax.plot(*zip(*pt), linewidth=1.6, color=BLUE, alpha=0.55, zorder=2)
    ax.plot(*zip(*on), linewidth=1.6, color=ORANGE, alpha=0.55, zorder=2)

    for fps, m, nhan, dx, dy in diem:
        mau = BLUE if "PyTorch" in nhan else ORANGE
        ax.scatter(fps, m, s=90, color=mau, zorder=4,
                   edgecolors="white", linewidths=1.6)
        ax.annotate(nhan, (fps, m), textcoords="offset points",
                    xytext=(dx, dy), fontsize=9, color=INK)

    # Nguong muot 15 FPS
    ax.axvline(15, color=MUTED, linestyle="--", linewidth=1, zorder=1)
    ax.annotate("Ngưỡng 15 FPS", xy=(15, 0.828), xytext=(16, 0.826),
                fontsize=9, color=MUTED)

    ax.set_xlabel("Tốc độ xử lý (FPS)")
    ax.set_ylabel("mAP@0.5")
    ax.set_xlim(4, 41)
    ax.set_ylim(0.815, 0.972)
    _dau_phay(ax, so_le=2)

    from matplotlib.lines import Line2D
    ax.legend(handles=[
        Line2D([], [], marker="o", color=BLUE, linestyle="-",
               markersize=8, label="PyTorch"),
        Line2D([], [], marker="o", color=ORANGE, linestyle="-",
               markersize=8, label="ONNX Runtime"),
    ], frameon=False, loc="lower left")

    fig.savefig(OUT / "hinh_4_15_danh_doi_chinh_xac_toc_do.png")
    plt.close(fig)
    print("  Đã tạo hinh_4_15_danh_doi_chinh_xac_toc_do.png")


if __name__ == "__main__":
    print(f"Phông chữ sử dụng: {FONT}")
    print(f"Thư mục kết quả  : {OUT.resolve()}\n")
    hinh_4_9()
    hinh_4_10()
    hinh_4_12()
    hinh_4_13()
    hinh_4_15()
    print("\nHoàn tất. Chèn vào Word bằng Insert > Pictures.")
