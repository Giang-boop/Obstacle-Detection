# ======================================================================
#  FILE: training/tao_oversample.py
#  CHUC NANG: Tạo bản oversample cho các lớp vật hiếm.
# ======================================================================

import argparse
import sys
from collections import Counter
from pathlib import Path

import yaml

THU_MUC_TRAINING = Path(__file__).resolve().parent
THU_MUC_DATASET = THU_MUC_TRAINING / "datasets" / "obstacle17"

DUOI_ANH = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

HE_SO_MAC_DINH = {
    "Motorcycle": 4,
    "Bike": 4,
    "Dog": 4,
    "Electrical Pole": 4,
    "Guard rail": 2,
    "Electrical Box": 2,
    "Road": 2,
    "Truck": 2,
}


def doc_tham_so():
    parser = argparse.ArgumentParser(
        description="Tạo danh sách ảnh train có lặp lại ảnh chứa lớp hiếm và data yaml tương ứng."
    )
    parser.add_argument("--data", default=str(THU_MUC_DATASET / "data.yaml"))
    parser.add_argument("--ra-yaml", default=str(THU_MUC_DATASET / "data_oversample.yaml"))
    parser.add_argument("--ra-danh-sach", default=str(THU_MUC_DATASET / "train_oversample.txt"))
    parser.add_argument("--thong-ke", default=str(THU_MUC_TRAINING / "thong_ke_oversample.txt"))
    parser.add_argument(
        "--he-so",
        nargs="*",
        default=None,
        help='Ghi đè hệ số dạng "Tên lớp=số", ví dụ "Motorcycle=4" "Truck=2"',
    )
    return parser.parse_args()


def doc_he_so(danh_sach):
    he_so = dict(HE_SO_MAC_DINH)
    for muc in danh_sach or []:
        ten, _, gia_tri = muc.rpartition("=")
        if not ten or not gia_tri.isdigit():
            sys.exit(f"[LỖI] Hệ số không hợp lệ: {muc}")
        he_so[ten.strip()] = int(gia_tri)
    return he_so


def doc_cau_hinh(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        cau_hinh = yaml.safe_load(f)
    ten_lop = cau_hinh["names"]
    if isinstance(ten_lop, dict):
        ten_lop = [ten_lop[k] for k in sorted(ten_lop)]
    return cau_hinh, [str(t) for t in ten_lop]


def duong_dan_tap(cau_hinh, khoa, thu_muc_yaml):
    goc = Path(cau_hinh.get("path") or thu_muc_yaml)
    if not goc.is_absolute():
        goc = thu_muc_yaml / goc
    gia_tri = Path(cau_hinh[khoa])
    return gia_tri if gia_tri.is_absolute() else goc / gia_tri


def file_nhan_cua_anh(anh):
    phan = list(anh.parts)
    vi_tri = len(phan) - 1 - phan[::-1].index("images")
    phan[vi_tri] = "labels"
    return Path(*phan).with_suffix(".txt")


def doc_lop_trong_nhan(file_nhan, so_lop):
    lop = []
    if not file_nhan.exists():
        return lop
    for dong in file_nhan.read_text(encoding="utf-8").splitlines():
        cac_phan = dong.split()
        if not cac_phan:
            continue
        chi_so = int(float(cac_phan[0]))
        if 0 <= chi_so < so_lop:
            lop.append(chi_so)
    return lop


def tao_bang_thong_ke(ten_lop, truoc, sau, so_anh_truoc, so_anh_sau, he_so_theo_lop):
    dong = [
        "THỐNG KÊ OVERSAMPLE TẬP TRAIN",
        f"Số ảnh trước: {so_anh_truoc}",
        f"Số ảnh sau  : {so_anh_sau} (x{so_anh_sau / max(so_anh_truoc, 1):.2f})",
        "",
        f"{'Chỉ số':>6}  {'Lớp':<16}{'Hệ số':>6}{'Nhãn trước':>12}{'Nhãn sau':>10}{'Tỉ lệ':>8}",
    ]
    for i, ten in enumerate(ten_lop):
        ti_le = sau[i] / truoc[i] if truoc[i] else 0
        dong.append(
            f"{i:>6}  {ten:<16}{he_so_theo_lop.get(ten, 1):>6}{truoc[i]:>12}{sau[i]:>10}{ti_le:>8.2f}"
        )
    dong.append(f"{'':>6}  {'Tổng':<16}{'':>6}{sum(truoc.values()):>12}{sum(sau.values()):>10}")
    return "\n".join(dong)


def main():
    tham_so = doc_tham_so()
    duong_dan_yaml = Path(tham_so.data).resolve()
    cau_hinh, ten_lop = doc_cau_hinh(duong_dan_yaml)
    he_so_theo_lop = doc_he_so(tham_so.he_so)
    lop_khong_co = [ten for ten in he_so_theo_lop if ten not in ten_lop]
    if lop_khong_co:
        sys.exit(f"[LỖI] Lớp không có trong data.yaml: {lop_khong_co}")
    he_so_chi_so = {ten_lop.index(ten): so for ten, so in he_so_theo_lop.items()}

    thu_muc_anh = duong_dan_tap(cau_hinh, "train", duong_dan_yaml.parent)
    if not thu_muc_anh.is_dir():
        sys.exit(f"[LỖI] Không thấy thư mục ảnh train {thu_muc_anh}")
    danh_sach_anh = sorted(p for p in thu_muc_anh.rglob("*") if p.suffix.lower() in DUOI_ANH)

    truoc = Counter({i: 0 for i in range(len(ten_lop))})
    sau = Counter({i: 0 for i in range(len(ten_lop))})
    dong_danh_sach = []
    for anh in danh_sach_anh:
        lop = doc_lop_trong_nhan(file_nhan_cua_anh(anh), len(ten_lop))
        lan_lap = max([he_so_chi_so.get(c, 1) for c in lop], default=1)
        dem = Counter(lop)
        for c, so in dem.items():
            truoc[c] += so
            sau[c] += so * lan_lap
        dong_danh_sach.extend([str(anh.resolve())] * lan_lap)

    file_danh_sach = Path(tham_so.ra_danh_sach)
    file_danh_sach.write_text("\n".join(dong_danh_sach) + "\n", encoding="utf-8")

    cau_hinh_moi = {
        "path": str(Path(cau_hinh.get("path") or duong_dan_yaml.parent)),
        "train": str(file_danh_sach.resolve()),
        "val": str(duong_dan_tap(cau_hinh, "val", duong_dan_yaml.parent)),
        "nc": len(ten_lop),
        "names": ten_lop,
    }
    if cau_hinh.get("test"):
        cau_hinh_moi["test"] = str(duong_dan_tap(cau_hinh, "test", duong_dan_yaml.parent))
    with open(tham_so.ra_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(cau_hinh_moi, f, allow_unicode=True, sort_keys=False)

    bang = tao_bang_thong_ke(ten_lop, truoc, sau, len(danh_sach_anh), len(dong_danh_sach), he_so_theo_lop)
    bang += f"\n\nDanh sách ảnh: {file_danh_sach.resolve()}\nData yaml    : {Path(tham_so.ra_yaml).resolve()}\n"
    Path(tham_so.thong_ke).write_text(bang, encoding="utf-8")
    print(bang)


if __name__ == "__main__":
    main()
