# ======================================================================
#  FILE: training/danh_gia.py
#  CHUC NANG: Đánh giá model trên tập test (precision/recall/mAP theo lớp).
# ======================================================================

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from ultralytics import YOLO

THU_MUC_TRAINING = Path(__file__).resolve().parent

HINH_HUAN_LUYEN = [
    "results.png",
    "labels.jpg",
    "labels_correlogram.jpg",
    "confusion_matrix.png",
    "confusion_matrix_normalized.png",
    "PR_curve.png",
    "P_curve.png",
    "R_curve.png",
    "F1_curve.png",
]


def doc_tham_so():
    parser = argparse.ArgumentParser(description="Đánh giá best.pt trên tập val và test, xuất chỉ số theo từng lớp.")
    parser.add_argument("--weights", default=str(THU_MUC_TRAINING / "runs" / "yolov8n_17lop" / "weights" / "best.pt"))
    parser.add_argument("--data", default=str(THU_MUC_TRAINING / "datasets" / "obstacle17" / "data.yaml"))
    parser.add_argument("--splits", nargs="+", default=["val", "test"])
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--conf", type=float, default=0.001)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--out", default=None, help="Thư mục xuất (mặc định: <thư mục run>/danh_gia)")
    return parser.parse_args()


def so_thuc(gia_tri):
    return round(float(gia_tri), 5)


def danh_gia_mot_tap(model, tham_so, split, thu_muc_xuat):
    bo_dem = {}

    def lay_so_luong(validator):
        bo_dem["so_anh"] = int(validator.seen)
        bo_dem["doi_tuong_theo_lop"] = [int(x) for x in validator.nt_per_class]
        bo_dem["anh_theo_lop"] = [int(x) for x in validator.nt_per_image]

    model.add_callback("on_val_end", lay_so_luong)
    try:
        metrics = model.val(
            data=tham_so.data,
            split=split,
            imgsz=tham_so.imgsz,
            batch=tham_so.batch,
            conf=tham_so.conf,
            iou=tham_so.iou,
            device=tham_so.device,
            workers=tham_so.workers,
            project=str(thu_muc_xuat),
            name=split,
            exist_ok=True,
            plots=True,
            verbose=False,
        )
    finally:
        model.callbacks["on_val_end"].remove(lay_so_luong)
    ten_lop = metrics.names
    hop = metrics.box
    vi_tri = {int(c): i for i, c in enumerate(hop.ap_class_index)}
    theo_lop = []
    for id_lop in range(len(ten_lop)):
        dong = {
            "class_id": id_lop,
            "class_name": ten_lop[id_lop],
            "images": bo_dem["anh_theo_lop"][id_lop],
            "instances": bo_dem["doi_tuong_theo_lop"][id_lop],
            "precision": None,
            "recall": None,
            "mAP50": None,
            "mAP50-95": None,
        }
        if id_lop in vi_tri and dong["instances"] > 0:
            p, r, ap50, ap = hop.class_result(vi_tri[id_lop])
            dong.update(precision=so_thuc(p), recall=so_thuc(r), mAP50=so_thuc(ap50), **{"mAP50-95": so_thuc(ap)})
        theo_lop.append(dong)
    tong_hop = {
        "class_id": "",
        "class_name": "all",
        "images": bo_dem["so_anh"],
        "instances": sum(bo_dem["doi_tuong_theo_lop"]),
        "precision": so_thuc(hop.mp),
        "recall": so_thuc(hop.mr),
        "mAP50": so_thuc(hop.map50),
        "mAP50-95": so_thuc(hop.map),
    }
    toc_do = {k: round(float(v), 3) for k, v in metrics.speed.items()}
    return {"tong_hop": tong_hop, "theo_lop": theo_lop, "toc_do_ms_moi_anh": toc_do, "thu_muc": str(metrics.save_dir)}


def ghi_csv(duong_dan, ket_qua):
    cot = ["split", "class_id", "class_name", "images", "instances", "precision", "recall", "mAP50", "mAP50-95"]
    with open(duong_dan, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=cot)
        writer.writeheader()
        for split, kq in ket_qua.items():
            for dong in [kq["tong_hop"]] + kq["theo_lop"]:
                writer.writerow({"split": split, **{k: ("" if v is None else v) for k, v in dong.items()}})


def gom_hinh(thu_muc_xuat, ket_qua, thu_muc_run):
    thu_muc_hinh = thu_muc_xuat / "hinh"
    thu_muc_hinh.mkdir(parents=True, exist_ok=True)
    so_hinh = 0
    for split, kq in ket_qua.items():
        for hinh in sorted(Path(kq["thu_muc"]).glob("*")):
            if hinh.suffix.lower() in {".png", ".jpg"}:
                shutil.copy2(hinh, thu_muc_hinh / f"{split}_{hinh.name}")
                so_hinh += 1
    if thu_muc_run is not None:
        for ten in HINH_HUAN_LUYEN:
            hinh = thu_muc_run / ten
            if hinh.exists():
                shutil.copy2(hinh, thu_muc_hinh / f"huan_luyen_{ten}")
                so_hinh += 1
    return thu_muc_hinh, so_hinh


def main():
    tham_so = doc_tham_so()
    weights = Path(tham_so.weights).resolve()
    if not weights.exists():
        raise SystemExit(f"[LỖI] Không tìm thấy {weights}")
    thu_muc_run = weights.parent.parent if weights.parent.name == "weights" else None
    if tham_so.out:
        thu_muc_xuat = Path(tham_so.out).resolve()
    else:
        thu_muc_xuat = (thu_muc_run or weights.parent) / "danh_gia"
    thu_muc_xuat.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(weights))
    print(f"Mô hình: {weights}")
    print(f"Các lớp ({len(model.names)}): {', '.join(model.names.values())}")
    ket_qua = {}
    for split in tham_so.splits:
        print(f"\n=== Đánh giá trên tập {split} ===")
        kq = danh_gia_mot_tap(model, tham_so, split, thu_muc_xuat)
        ket_qua[split] = kq
        th = kq["tong_hop"]
        print(f"{'Lớp':<16}{'Ảnh':>7}{'Đối tượng':>11}{'P':>8}{'R':>8}{'mAP50':>8}{'mAP50-95':>10}")
        for dong in [th] + kq["theo_lop"]:
            gia_tri = [dong[k] for k in ("precision", "recall", "mAP50", "mAP50-95")]
            chu = "".join(f"{v:>8.3f}" if v is not None else f"{'-':>8}" for v in gia_tri[:3])
            chu += f"{gia_tri[3]:>10.3f}" if gia_tri[3] is not None else f"{'-':>10}"
            print(f"{dong['class_name']:<16}{dong['images']:>7}{dong['instances']:>11}{chu}")

    ghi_csv(thu_muc_xuat / "chi_so_theo_lop.csv", ket_qua)
    du_lieu_json = {
        "weights": str(weights),
        "data": str(Path(tham_so.data).resolve()),
        "imgsz": tham_so.imgsz,
        "conf": tham_so.conf,
        "iou": tham_so.iou,
        "thoi_gian": datetime.now().isoformat(timespec="seconds"),
        "ket_qua": ket_qua,
    }
    with open(thu_muc_xuat / "chi_so_theo_lop.json", "w", encoding="utf-8") as f:
        json.dump(du_lieu_json, f, ensure_ascii=False, indent=2)
    thu_muc_hinh, so_hinh = gom_hinh(thu_muc_xuat, ket_qua, thu_muc_run)
    print(f"\nĐã ghi: {thu_muc_xuat / 'chi_so_theo_lop.csv'}")
    print(f"Đã ghi: {thu_muc_xuat / 'chi_so_theo_lop.json'}")
    print(f"Đã gom {so_hinh} hình của Ultralytics vào: {thu_muc_hinh}")


if __name__ == "__main__":
    main()
