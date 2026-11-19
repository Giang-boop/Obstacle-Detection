# ======================================================================
#  FILE: training/train.py
#  CHUC NANG: Huấn luyện YOLOv8n 60 epoch, imgsz 640.
# ======================================================================

import argparse
import gc
import time
from pathlib import Path

import torch
from ultralytics import YOLO

THU_MUC_TRAINING = Path(__file__).resolve().parent


def doc_tham_so():
    parser = argparse.ArgumentParser(description="Huấn luyện YOLOv8 nhận diện 17 lớp vật cản.")
    parser.add_argument("--data", default=str(THU_MUC_TRAINING / "datasets" / "obstacle17" / "data.yaml"))
    parser.add_argument("--model", default=str(THU_MUC_TRAINING / "yolov8n.pt"))
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--project", default=str(THU_MUC_TRAINING / "runs"))
    parser.add_argument("--name", default="yolov8n_17lop")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--patience", type=int, default=0)
    parser.add_argument("--optimizer", default="auto")
    parser.add_argument("--lr0", type=float, default=0.01)
    parser.add_argument("--cls", type=float, default=0.5, help="Trọng số loss phân lớp")
    parser.add_argument("--close-mosaic", type=int, default=10)
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--cache", choices=["false", "ram", "disk"], default="false")
    parser.add_argument("--exist-ok", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Train tiếp từ weights/last.pt của run --name")
    parser.add_argument("--batch-nho-nhat", type=int, default=4, help="Khi hết VRAM thì giảm batch một nửa tới mức này")
    return parser.parse_args()


def la_loi_het_vram(loi):
    return isinstance(loi, torch.cuda.OutOfMemoryError) or "out of memory" in str(loi).lower()


def huan_luyen(model, tham_so, batch, ten_run, exist_ok):
    cache = False if tham_so.cache == "false" else tham_so.cache
    return model.train(
        data=tham_so.data,
        epochs=tham_so.epochs,
        imgsz=tham_so.imgsz,
        batch=batch,
        device=tham_so.device,
        workers=tham_so.workers,
        project=tham_so.project,
        name=ten_run,
        exist_ok=exist_ok,
        seed=tham_so.seed,
        deterministic=True,
        patience=tham_so.patience,
        optimizer=tham_so.optimizer,
        lr0=tham_so.lr0,
        cls=tham_so.cls,
        close_mosaic=tham_so.close_mosaic,
        fraction=tham_so.fraction,
        cache=cache,
        pretrained=True,
        amp=True,
        plots=True,
        val=True,
    )


def train_tiep(tham_so):
    last = Path(tham_so.project) / tham_so.name / "weights" / "last.pt"
    if not last.exists():
        raise SystemExit(f"[LỖI] Không tìm thấy {last} để train tiếp")
    print(f"Train tiếp từ {last}")
    model = YOLO(str(last))
    model.train(resume=True, workers=tham_so.workers)
    return model


def main():
    tham_so = doc_tham_so()
    if tham_so.device != "cpu" and not torch.cuda.is_available():
        raise SystemExit("[LỖI] Không thấy GPU CUDA. Dùng --device cpu nếu muốn train bằng CPU.")
    if not Path(tham_so.model).exists():
        ten_model = Path(tham_so.model).name
        print(f"Không thấy {tham_so.model}, Ultralytics sẽ tự tải {ten_model}")
        tham_so.model = ten_model

    print(f"=== HUẤN LUYỆN {Path(tham_so.model).stem} - 17 LỚP VẬT CẢN ===")
    print(f"Dữ liệu     : {tham_so.data}")
    print(f"Mô hình gốc : {tham_so.model}")
    print(f"Epochs={tham_so.epochs}, imgsz={tham_so.imgsz}, batch={tham_so.batch}, device={tham_so.device}, "
          f"workers={tham_so.workers}, seed={tham_so.seed}, patience={tham_so.patience}, fraction={tham_so.fraction}, cls={tham_so.cls}, close_mosaic={tham_so.close_mosaic}")
    if torch.cuda.is_available():
        print(f"GPU         : {torch.cuda.get_device_name(0)}")

    bat_dau = time.time()
    if tham_so.resume:
        model = train_tiep(tham_so)
    else:
        batch = tham_so.batch
        ten_run = tham_so.name
        exist_ok = tham_so.exist_ok
        while True:
            model = YOLO(tham_so.model)
            try:
                huan_luyen(model, tham_so, batch, ten_run, exist_ok)
                break
            except Exception as loi:
                if not la_loi_het_vram(loi) or batch // 2 < tham_so.batch_nho_nhat:
                    raise
                trainer = getattr(model, "trainer", None)
                if trainer is not None and getattr(trainer, "save_dir", None):
                    ten_run = Path(trainer.save_dir).name
                    exist_ok = True
                print(f"[CẢNH BÁO] Hết VRAM với batch={batch}, thử lại với batch={batch // 2}")
                batch //= 2
                del model
                gc.collect()
                torch.cuda.empty_cache()

    thu_muc_run = Path(model.trainer.save_dir)
    phut = (time.time() - bat_dau) / 60
    print("\n=== HOÀN TẤT ===")
    print(f"Thời gian       : {phut:.1f} phút")
    print(f"Thư mục kết quả : {thu_muc_run}")
    print(f"Trọng số tốt nhất: {thu_muc_run / 'weights' / 'best.pt'}")
    print(f"Bảng theo epoch : {thu_muc_run / 'results.csv'}")


if __name__ == "__main__":
    main()
