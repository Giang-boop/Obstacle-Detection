# ======================================================================
#  FILE: training/chuan_bi_dataset.py
#  CHUC NANG: Chuẩn bị dataset từ nguồn ảnh gốc (tách train/val/test).
# ======================================================================

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

import yaml

THU_MUC_TRAINING = Path(__file__).resolve().parent

LOP_MUC_TIEU = [
    "Bike",
    "Building",
    "Car",
    "Person",
    "Stairs",
    "Electrical Pole",
    "Road",
    "Motorcycle",
    "Dustbin",
    "Manhole",
    "Tree",
    "Guard rail",
    "Truck",
    "Traffic Cone",
    "Electrical Box",
    "Chair",
    "Dog",
]

DUOI_ANH = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

TAP_DU_LIEU = [("train", "train"), ("val", "valid"), ("test", "test")]


def doc_tham_so():
    parser = argparse.ArgumentParser(
        description="Chuẩn bị dataset YOLO 17 lớp (ánh xạ lớp theo tên hoặc kiểm tra dataset đã có 17 lớp)."
    )
    parser.add_argument("--nguon", required=True, help="Thư mục dataset nguồn (chứa data.yaml)")
    parser.add_argument(
        "--dich",
        default=str(THU_MUC_TRAINING / "datasets" / "obstacle17"),
        help="Thư mục xuất dataset 17 lớp (mặc định: training/datasets/obstacle17)",
    )
    parser.add_argument(
        "--che-do",
        choices=["tu-dong", "anh-xa", "kiem-tra"],
        default="tu-dong",
        help="tu-dong: nguồn đã đúng 17 lớp thì chỉ kiểm tra, ngược lại thì ánh xạ; anh-xa: luôn tạo bản mới; kiem-tra: chỉ kiểm tra",
    )
    parser.add_argument("--ghi-de", action="store_true", help="Xóa thư mục đích cũ trước khi tạo")
    return parser.parse_args()


def chuan_hoa_ten(ten):
    return " ".join(str(ten).strip().lower().split())


def doc_data_yaml(thu_muc_nguon):
    duong_dan = thu_muc_nguon / "data.yaml"
    if not duong_dan.exists():
        sys.exit(f"[LỖI] Không tìm thấy {duong_dan}")
    with open(duong_dan, encoding="utf-8") as f:
        cau_hinh = yaml.safe_load(f)
    ten_lop = cau_hinh.get("names")
    if isinstance(ten_lop, dict):
        ten_lop = [ten_lop[k] for k in sorted(ten_lop)]
    if not ten_lop:
        sys.exit("[LỖI] data.yaml không có danh sách names")
    return cau_hinh, [str(t) for t in ten_lop]


def tim_thu_muc_anh(thu_muc_nguon, cau_hinh, khoa, ten_tap):
    ung_vien = []
    goc = Path(cau_hinh["path"]) if cau_hinh.get("path") else thu_muc_nguon
    if not goc.is_absolute():
        goc = thu_muc_nguon / goc
    gia_tri = cau_hinh.get(khoa)
    if isinstance(gia_tri, str):
        ung_vien.append(Path(gia_tri))
        ung_vien.append(goc / gia_tri)
        ung_vien.append(thu_muc_nguon / gia_tri.lstrip("./").lstrip("/"))
        ung_vien.append(thu_muc_nguon / gia_tri.replace("../", "", 1))
    ung_vien.append(thu_muc_nguon / ten_tap / "images")
    for duong_dan in ung_vien:
        if duong_dan.is_dir():
            return duong_dan.resolve()
    return None


def duong_dan_nhan(anh):
    phan = list(anh.parts)
    for i in range(len(phan) - 1, -1, -1):
        if phan[i] == "images":
            phan[i] = "labels"
            break
    return Path(*phan).with_suffix(".txt")


def lien_ket_hoac_sao_chep(nguon, dich):
    if dich.exists():
        if os.path.samefile(nguon, dich):
            return "lien_ket"
        dich.unlink()
    try:
        os.link(nguon, dich)
        return "lien_ket"
    except OSError:
        shutil.copy2(nguon, dich)
        return "sao_chep"


def xu_ly_tap(ten_tap, thu_muc_anh, anh_xa, so_lop_nguon, ten_lop_nguon, thu_muc_dich, ghi_file):
    thong_ke = {
        "tap": ten_tap,
        "so_anh": 0,
        "anh_co_doi_tuong": 0,
        "anh_nen": 0,
        "anh_thieu_nhan": 0,
        "nhan_rong_goc": 0,
        "anh_thanh_nen_do_bo_lop": 0,
        "hop_giu_lai": 0,
        "hop_bi_bo": 0,
        "dong_loi": 0,
        "lien_ket": 0,
        "sao_chep": 0,
    }
    so_hop_theo_lop = [0] * len(LOP_MUC_TIEU)
    so_hop_bi_bo = {}
    vi_du_loi = []
    danh_sach_anh = sorted(p for p in thu_muc_anh.rglob("*") if p.is_file() and p.suffix.lower() in DUOI_ANH)
    for anh in danh_sach_anh:
        thong_ke["so_anh"] += 1
        file_nhan = duong_dan_nhan(anh)
        dong_moi = []
        co_hop_goc = False
        if file_nhan.exists():
            noi_dung = file_nhan.read_text(encoding="utf-8", errors="ignore").splitlines()
            dong_hop_le = [d for d in noi_dung if d.strip()]
            if not dong_hop_le:
                thong_ke["nhan_rong_goc"] += 1
            for dong in dong_hop_le:
                phan = dong.split()
                try:
                    id_nguon = int(float(phan[0]))
                    toa_do = [float(x) for x in phan[1:]]
                except (ValueError, IndexError):
                    id_nguon, toa_do = -1, []
                if id_nguon < 0 or id_nguon >= so_lop_nguon or len(toa_do) < 4 or len(toa_do) % 2:
                    thong_ke["dong_loi"] += 1
                    if len(vi_du_loi) < 5:
                        vi_du_loi.append(f"{file_nhan.name}: '{dong.strip()}'")
                    continue
                if any(x < -0.01 or x > 1.01 for x in toa_do):
                    thong_ke["dong_loi"] += 1
                    if len(vi_du_loi) < 5:
                        vi_du_loi.append(f"{file_nhan.name}: tọa độ ngoài [0,1] '{dong.strip()}'")
                    continue
                co_hop_goc = True
                id_moi = anh_xa.get(id_nguon)
                if id_moi is None:
                    thong_ke["hop_bi_bo"] += 1
                    ten = ten_lop_nguon[id_nguon]
                    so_hop_bi_bo[ten] = so_hop_bi_bo.get(ten, 0) + 1
                    continue
                thong_ke["hop_giu_lai"] += 1
                so_hop_theo_lop[id_moi] += 1
                dong_moi.append(" ".join([str(id_moi)] + phan[1:]))
        else:
            thong_ke["anh_thieu_nhan"] += 1
        if dong_moi:
            thong_ke["anh_co_doi_tuong"] += 1
        else:
            thong_ke["anh_nen"] += 1
            if co_hop_goc:
                thong_ke["anh_thanh_nen_do_bo_lop"] += 1
        if ghi_file:
            tuong_doi = anh.relative_to(thu_muc_anh)
            anh_dich = thu_muc_dich / ten_tap / "images" / tuong_doi
            nhan_dich = (thu_muc_dich / ten_tap / "labels" / tuong_doi).with_suffix(".txt")
            anh_dich.parent.mkdir(parents=True, exist_ok=True)
            nhan_dich.parent.mkdir(parents=True, exist_ok=True)
            thong_ke[lien_ket_hoac_sao_chep(anh, anh_dich)] += 1
            nhan_dich.write_text("\n".join(dong_moi) + ("\n" if dong_moi else ""), encoding="utf-8")
    return thong_ke, so_hop_theo_lop, so_hop_bi_bo, vi_du_loi


def ghi_data_yaml(thu_muc_dich, thu_muc_tap):
    noi_dung = {"path": str(thu_muc_dich.resolve())}
    for khoa, duong_dan in thu_muc_tap.items():
        noi_dung[khoa] = str(duong_dan.resolve())
    noi_dung["nc"] = len(LOP_MUC_TIEU)
    noi_dung["names"] = list(LOP_MUC_TIEU)
    thu_muc_dich.mkdir(parents=True, exist_ok=True)
    with open(thu_muc_dich / "data.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(noi_dung, f, allow_unicode=True, sort_keys=False)
    return thu_muc_dich / "data.yaml"


def ghi_bang_thong_ke(thu_muc_dich, ket_qua_tap, ket_qua_bo_lop):
    ten_cac_tap = [k["tap"] for k, _, _, _ in ket_qua_tap]
    with open(thu_muc_dich / "thong_ke_lop.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["class_id", "class_name"] + ten_cac_tap + ["total"])
        tong_cot = [0] * len(ten_cac_tap)
        for i, ten in enumerate(LOP_MUC_TIEU):
            dong = [r[1][i] for r in ket_qua_tap]
            tong_cot = [a + b for a, b in zip(tong_cot, dong)]
            writer.writerow([i, ten] + dong + [sum(dong)])
        writer.writerow(["", "TOTAL"] + tong_cot + [sum(tong_cot)])
    with open(thu_muc_dich / "thong_ke_tap.csv", "w", newline="", encoding="utf-8-sig") as f:
        cot = list(ket_qua_tap[0][0].keys())
        writer = csv.DictWriter(f, fieldnames=cot)
        writer.writeheader()
        for thong_ke, _, _, _ in ket_qua_tap:
            writer.writerow(thong_ke)
    if ket_qua_bo_lop:
        with open(thu_muc_dich / "lop_bi_bo.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["class_name"] + ten_cac_tap + ["total"])
            for ten in sorted(ket_qua_bo_lop):
                dong = [r[2].get(ten, 0) for r in ket_qua_tap]
                writer.writerow([ten] + dong + [sum(dong)])


def in_bang(ket_qua_tap):
    ten_cac_tap = [k["tap"] for k, _, _, _ in ket_qua_tap]
    print("\nSố đối tượng (bounding box) theo lớp và theo tập:")
    tieu_de = f"{'ID':>3}  {'Tên lớp':<16}" + "".join(f"{t:>9}" for t in ten_cac_tap) + f"{'Tổng':>9}"
    print(tieu_de)
    print("-" * len(tieu_de))
    tong_cot = [0] * len(ten_cac_tap)
    for i, ten in enumerate(LOP_MUC_TIEU):
        dong = [r[1][i] for r in ket_qua_tap]
        tong_cot = [a + b for a, b in zip(tong_cot, dong)]
        canh_bao = "  <-- không có mẫu" if sum(dong) == 0 else ""
        print(f"{i:>3}  {ten:<16}" + "".join(f"{x:>9}" for x in dong) + f"{sum(dong):>9}{canh_bao}")
    print("-" * len(tieu_de))
    print(f"{'':>3}  {'TỔNG':<16}" + "".join(f"{x:>9}" for x in tong_cot) + f"{sum(tong_cot):>9}")
    print("\nThống kê ảnh theo tập:")
    for thong_ke, _, _, _ in ket_qua_tap:
        print(
            f"  {thong_ke['tap']:<6} ảnh={thong_ke['so_anh']}, có đối tượng={thong_ke['anh_co_doi_tuong']}, "
            f"ảnh nền={thong_ke['anh_nen']} (trong đó {thong_ke['anh_thanh_nen_do_bo_lop']} ảnh thành nền do bỏ lớp, "
            f"{thong_ke['nhan_rong_goc']} nhãn rỗng sẵn, {thong_ke['anh_thieu_nhan']} thiếu file nhãn), "
            f"hộp giữ={thong_ke['hop_giu_lai']}, hộp bỏ={thong_ke['hop_bi_bo']}, dòng lỗi={thong_ke['dong_loi']}"
        )


def main():
    tham_so = doc_tham_so()
    thu_muc_nguon = Path(tham_so.nguon).resolve()
    thu_muc_dich = Path(tham_so.dich).resolve()
    cau_hinh, ten_lop_nguon = doc_data_yaml(thu_muc_nguon)
    print(f"Nguồn: {thu_muc_nguon} ({len(ten_lop_nguon)} lớp)")

    da_dung_17_lop = [chuan_hoa_ten(t) for t in ten_lop_nguon] == [chuan_hoa_ten(t) for t in LOP_MUC_TIEU]
    if tham_so.che_do == "kiem-tra" and not da_dung_17_lop:
        print("[LỖI] Danh sách lớp nguồn không khớp đúng thứ tự 17 lớp mục tiêu:")
        for i in range(max(len(ten_lop_nguon), len(LOP_MUC_TIEU))):
            a = ten_lop_nguon[i] if i < len(ten_lop_nguon) else "-"
            b = LOP_MUC_TIEU[i] if i < len(LOP_MUC_TIEU) else "-"
            print(f"  {i:>2}: nguồn={a!r:<22} mục tiêu={b!r}{'' if chuan_hoa_ten(a) == chuan_hoa_ten(b) else '  <-- KHÁC'}")
        sys.exit(1)
    chi_kiem_tra = tham_so.che_do == "kiem-tra" or (tham_so.che_do == "tu-dong" and da_dung_17_lop)

    chi_so_muc_tieu = {chuan_hoa_ten(t): i for i, t in enumerate(LOP_MUC_TIEU)}
    anh_xa = {}
    for id_nguon, ten in enumerate(ten_lop_nguon):
        id_moi = chi_so_muc_tieu.get(chuan_hoa_ten(ten))
        if id_moi is not None:
            anh_xa[id_nguon] = id_moi
    lop_thieu = [t for i, t in enumerate(LOP_MUC_TIEU) if i not in anh_xa.values()]
    lop_bo = [t for i, t in enumerate(ten_lop_nguon) if i not in anh_xa]

    if chi_kiem_tra:
        print("Chế độ: KIỂM TRA (nguồn đã đúng 17 lớp, không sao chép ảnh)")
    else:
        print("Chế độ: ÁNH XẠ theo tên lớp sang 17 lớp mục tiêu")
        for id_nguon, id_moi in sorted(anh_xa.items()):
            print(f"  {id_nguon:>2} {ten_lop_nguon[id_nguon]:<22} -> {id_moi:>2} {LOP_MUC_TIEU[id_moi]}")
        print(f"  Lớp bị bỏ ({len(lop_bo)}): {', '.join(lop_bo) if lop_bo else 'không có'}")
    if lop_thieu:
        print(f"[CẢNH BÁO] Nguồn không có các lớp: {', '.join(lop_thieu)}")

    if not chi_kiem_tra:
        if thu_muc_dich == thu_muc_nguon:
            sys.exit("[LỖI] Thư mục đích trùng thư mục nguồn")
        if thu_muc_dich.exists() and tham_so.ghi_de:
            print(f"Xóa thư mục đích cũ: {thu_muc_dich}")
            shutil.rmtree(thu_muc_dich)
        thu_muc_dich.mkdir(parents=True, exist_ok=True)

    ket_qua_tap = []
    thu_muc_tap_yaml = {}
    bo_lop_tong = set()
    for khoa, ten_tap in TAP_DU_LIEU:
        thu_muc_anh = tim_thu_muc_anh(thu_muc_nguon, cau_hinh, khoa, ten_tap)
        if thu_muc_anh is None:
            print(f"[CẢNH BÁO] Không tìm thấy ảnh cho tập '{ten_tap}', bỏ qua")
            continue
        print(f"\nĐang xử lý tập {ten_tap}: {thu_muc_anh}")
        if not chi_kiem_tra:
            for cache in (thu_muc_dich / ten_tap).rglob("*.cache") if (thu_muc_dich / ten_tap).exists() else []:
                cache.unlink()
        ket_qua = xu_ly_tap(
            ten_tap, thu_muc_anh, anh_xa, len(ten_lop_nguon), ten_lop_nguon, thu_muc_dich, not chi_kiem_tra
        )
        ket_qua_tap.append(ket_qua)
        bo_lop_tong.update(ket_qua[2])
        for loi in ket_qua[3]:
            print(f"  [DÒNG LỖI] {loi}")
        if not chi_kiem_tra:
            print(f"  Ảnh: {ket_qua[0]['lien_ket']} hard link, {ket_qua[0]['sao_chep']} bản sao")
        thu_muc_tap_yaml[khoa] = thu_muc_anh if chi_kiem_tra else thu_muc_dich / ten_tap / "images"

    if not ket_qua_tap:
        sys.exit("[LỖI] Không xử lý được tập nào")
    if "train" not in thu_muc_tap_yaml or "val" not in thu_muc_tap_yaml:
        print("[CẢNH BÁO] Thiếu tập train hoặc val, Ultralytics sẽ không train được")

    in_bang(ket_qua_tap)
    file_yaml = ghi_data_yaml(thu_muc_dich, thu_muc_tap_yaml)
    ghi_bang_thong_ke(thu_muc_dich, ket_qua_tap, bo_lop_tong)
    tong_loi = sum(r[0]["dong_loi"] for r in ket_qua_tap)
    print(f"\nĐã ghi: {file_yaml}")
    print(f"Đã ghi: {thu_muc_dich / 'thong_ke_lop.csv'}, {thu_muc_dich / 'thong_ke_tap.csv'}")
    if tong_loi:
        print(f"[CẢNH BÁO] Có {tong_loi} dòng nhãn lỗi đã bị bỏ qua")
    print("Hoàn tất.")


if __name__ == "__main__":
    main()
