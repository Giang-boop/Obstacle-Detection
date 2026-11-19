# ======================================================================
#  FILE: training/ve_bieu_do.py
#  CHUC NANG: Vẽ biểu đồ so sánh giữa các lần huấn luyện.
# ======================================================================

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

THU_MUC_TRAINING = Path(__file__).resolve().parent

MAU_1 = "#2a78d6"
MAU_2 = "#eb6834"
MAU_NEN = "#fcfcfb"
MAU_CHU = "#0b0b0b"
MAU_CHU_PHU = "#52514e"
MAU_LUOI = "#e4e3df"

TEN_TAP = {"val": "tập validation", "test": "tập test", "train": "tập train"}


def doc_tham_so():
    parser = argparse.ArgumentParser(description="Vẽ biểu đồ huấn luyện từ results.csv và biểu đồ chỉ số theo lớp.")
    parser.add_argument(
        "--run",
        default=str(THU_MUC_TRAINING / "runs" / "yolov8n_17lop"),
        help="Thư mục run (chứa results.csv) hoặc đường dẫn trực tiếp tới results.csv",
    )
    parser.add_argument(
        "--danh-gia",
        default=None,
        help="File chi_so_theo_lop.json của danh_gia.py (mặc định: <run>/danh_gia/chi_so_theo_lop.json nếu có)",
    )
    parser.add_argument("--out", default=None, help="Thư mục lưu biểu đồ (mặc định: <run>/bieu_do)")
    parser.add_argument("--dpi", type=int, default=200)
    return parser.parse_args()


def cai_dat_giao_dien():
    plt.rcParams.update(
        {
            "font.family": ["Segoe UI", "Arial", "DejaVu Sans"],
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.edgecolor": MAU_CHU_PHU,
            "axes.labelcolor": MAU_CHU,
            "axes.facecolor": MAU_NEN,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": MAU_LUOI,
            "grid.linewidth": 0.8,
            "xtick.color": MAU_CHU_PHU,
            "ytick.color": MAU_CHU_PHU,
            "figure.facecolor": MAU_NEN,
            "legend.frameon": False,
            "lines.linewidth": 2,
        }
    )


def doc_results(duong_dan):
    bang = pd.read_csv(duong_dan)
    bang.columns = [c.strip() for c in bang.columns]
    return bang


def kieu_net(so_epoch):
    return {"marker": "o", "markersize": 6} if so_epoch <= 20 else {}


def ve_hai_duong(ax, epoch, du_lieu_1, nhan_1, du_lieu_2, nhan_2, tieu_de, nhan_y):
    net = kieu_net(len(epoch))
    ax.plot(epoch, du_lieu_1, color=MAU_1, label=nhan_1, **net)
    ax.plot(epoch, du_lieu_2, color=MAU_2, label=nhan_2, **net)
    ax.set_title(tieu_de, loc="left")
    ax.set_xlabel("Epoch")
    ax.set_ylabel(nhan_y)
    ax.legend()
    if len(epoch) <= 20:
        ax.set_xticks(list(epoch))


def luu(fig, thu_muc, ten, dpi, danh_sach):
    duong_dan = thu_muc / ten
    fig.tight_layout()
    fig.savefig(duong_dan, dpi=dpi, facecolor=MAU_NEN)
    plt.close(fig)
    danh_sach.append(duong_dan)


def ve_loss(bang, thu_muc, dpi, danh_sach):
    loai_loss = [
        ("box_loss", "Box loss (sai số vị trí khung)"),
        ("cls_loss", "Cls loss (sai số phân lớp)"),
        ("dfl_loss", "DFL loss (sai số phân bố biên khung)"),
    ]
    epoch = bang["epoch"]
    fig_tong, cac_truc = plt.subplots(1, 3, figsize=(16, 4.8))
    for (ten, tieu_de), ax_tong in zip(loai_loss, cac_truc):
        cot_train, cot_val = f"train/{ten}", f"val/{ten}"
        if cot_train not in bang or cot_val not in bang:
            continue
        fig, ax = plt.subplots(figsize=(8, 5))
        ve_hai_duong(ax, epoch, bang[cot_train], "Huấn luyện (train)", bang[cot_val], "Kiểm định (val)", tieu_de, "Giá trị loss")
        luu(fig, thu_muc, f"loss_{ten.replace('_loss', '')}.png", dpi, danh_sach)
        ve_hai_duong(ax_tong, epoch, bang[cot_train], "Train", bang[cot_val], "Val", tieu_de, "Giá trị loss")
    fig_tong.suptitle("Hàm mất mát theo epoch: huấn luyện và kiểm định", fontsize=14, fontweight="bold", x=0.01, ha="left")
    luu(fig_tong, thu_muc, "loss_tong_hop.png", dpi, danh_sach)


def danh_dau_tot_nhat(ax, epoch, gia_tri, mau, lech_y):
    vi_tri = gia_tri.idxmax()
    ax.scatter([epoch[vi_tri]], [gia_tri[vi_tri]], s=70, color=mau, edgecolor=MAU_NEN, linewidth=2, zorder=5)
    ax.annotate(
        f"cao nhất {gia_tri[vi_tri]:.3f} (epoch {int(epoch[vi_tri])})",
        (epoch[vi_tri], gia_tri[vi_tri]),
        textcoords="offset points",
        xytext=(-8, lech_y),
        ha="right",
        fontsize=10,
        color=MAU_CHU,
    )


def ve_chi_so(bang, thu_muc, dpi, danh_sach):
    epoch = bang["epoch"]
    if {"metrics/precision(B)", "metrics/recall(B)"} <= set(bang.columns):
        fig, ax = plt.subplots(figsize=(8, 5))
        ve_hai_duong(
            ax, epoch, bang["metrics/precision(B)"], "Precision", bang["metrics/recall(B)"], "Recall",
            "Precision và Recall trên tập kiểm định theo epoch", "Giá trị",
        )
        ax.set_ylim(0, 1.05)
        luu(fig, thu_muc, "precision_recall.png", dpi, danh_sach)
    if {"metrics/mAP50(B)", "metrics/mAP50-95(B)"} <= set(bang.columns):
        fig, ax = plt.subplots(figsize=(8, 5))
        ve_hai_duong(
            ax, epoch, bang["metrics/mAP50(B)"], "mAP@0.5", bang["metrics/mAP50-95(B)"], "mAP@0.5:0.95",
            "mAP trên tập kiểm định theo epoch", "Giá trị mAP",
        )
        danh_dau_tot_nhat(ax, epoch, bang["metrics/mAP50(B)"], MAU_1, 10)
        danh_dau_tot_nhat(ax, epoch, bang["metrics/mAP50-95(B)"], MAU_2, -18)
        ax.set_ylim(0, 1.05)
        luu(fig, thu_muc, "map.png", dpi, danh_sach)


def ve_theo_lop(file_json, thu_muc, dpi, danh_sach):
    with open(file_json, encoding="utf-8") as f:
        du_lieu = json.load(f)
    for split, kq in du_lieu["ket_qua"].items():
        cac_lop = [d for d in kq["theo_lop"] if d["mAP50"] is not None]
        if not cac_lop:
            continue
        cac_lop.sort(key=lambda d: d["mAP50"])
        ten = [f"{d['class_name']} ({d['instances']})" for d in cac_lop]
        vi_tri = range(len(cac_lop))
        do_day = 0.38
        fig, ax = plt.subplots(figsize=(9, 0.42 * len(cac_lop) + 1.8))
        cot_1 = ax.barh([y + do_day / 2 for y in vi_tri], [d["mAP50"] for d in cac_lop], height=do_day - 0.04,
                        color=MAU_1, label="mAP@0.5")
        cot_2 = ax.barh([y - do_day / 2 for y in vi_tri], [d["mAP50-95"] for d in cac_lop], height=do_day - 0.04,
                        color=MAU_2, label="mAP@0.5:0.95")
        ax.bar_label(cot_1, fmt="%.2f", padding=3, fontsize=8, color=MAU_CHU_PHU)
        ax.bar_label(cot_2, fmt="%.2f", padding=3, fontsize=8, color=MAU_CHU_PHU)
        ax.set_yticks(list(vi_tri))
        ax.set_yticklabels(ten)
        ax.set_xlim(0, 1.08)
        ax.grid(axis="y", visible=False)
        tong = kq["tong_hop"]
        ax.set_title(
            f"mAP theo từng lớp trên {TEN_TAP.get(split, split)} "
            f"(tất cả: mAP@0.5={tong['mAP50']:.3f}, mAP@0.5:0.95={tong['mAP50-95']:.3f})",
            loc="left", fontsize=12,
        )
        ax.set_xlabel("Giá trị mAP (trong ngoặc: số đối tượng)")
        ax.legend(loc="lower right")
        luu(fig, thu_muc, f"map_theo_lop_{split}.png", dpi, danh_sach)


def main():
    tham_so = doc_tham_so()
    duong_dan = Path(tham_so.run).resolve()
    file_results = duong_dan if duong_dan.is_file() else duong_dan / "results.csv"
    if not file_results.exists():
        raise SystemExit(f"[LỖI] Không tìm thấy {file_results}")
    thu_muc_run = file_results.parent
    thu_muc_out = Path(tham_so.out).resolve() if tham_so.out else thu_muc_run / "bieu_do"
    thu_muc_out.mkdir(parents=True, exist_ok=True)
    file_json = Path(tham_so.danh_gia) if tham_so.danh_gia else thu_muc_run / "danh_gia" / "chi_so_theo_lop.json"

    cai_dat_giao_dien()
    bang = doc_results(file_results)
    print(f"Đọc {file_results}: {len(bang)} epoch")
    danh_sach = []
    ve_loss(bang, thu_muc_out, tham_so.dpi, danh_sach)
    ve_chi_so(bang, thu_muc_out, tham_so.dpi, danh_sach)
    if file_json.exists():
        ve_theo_lop(file_json, thu_muc_out, tham_so.dpi, danh_sach)
    else:
        print(f"[CẢNH BÁO] Chưa có {file_json}, bỏ qua biểu đồ theo lớp (chạy danh_gia.py trước)")
    print(f"Đã lưu {len(danh_sach)} biểu đồ vào {thu_muc_out}:")
    for hinh in danh_sach:
        print(f"  {hinh.name}")


if __name__ == "__main__":
    main()
