# === MO TA FILE ===
# server/run.py
# CHUC NANG: Diem chay may chu: py -m server.run (--https, --port, --no-warmup), in dia chi LAN
# ===================

import argparse
import os

from server.app import create_app

app = create_app()


def parse_args():
    parser = argparse.ArgumentParser(description="Chạy máy chủ BlindAssist")
    parser.add_argument("--https", action="store_true", help="Chạy HTTPS bằng chứng chỉ tự ký để điện thoại mở được camera")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-warmup", action="store_true", help="Không nạp sẵn mô hình YOLO khi khởi động")
    return parser.parse_args()


def print_addresses(scheme, port, addresses):
    print("[MÁY CHỦ] Truy cập web quản lý và chế độ người khiếm thị:")
    for address in addresses:
        print(f"  {scheme}://{address}:{port}/        {scheme}://{address}:{port}/thiet-bi")


def main():
    args = parse_args()
    host = args.host or os.environ.get("BLINDASSIST_HOST", "0.0.0.0")
    port = args.port or int(os.environ.get("BLINDASSIST_PORT", "5000"))
    ssl_context = None
    if args.https:
        from server.certs import ensure_certificate

        host = "0.0.0.0" if args.host is None else host
        cert_file, key_file, names = ensure_certificate()
        ssl_context = (cert_file, key_file)
        print(f"[MÁY CHỦ] HTTPS bằng chứng chỉ tự ký: {cert_file}")
        print("[MÁY CHỦ] Trình duyệt sẽ cảnh báo chứng chỉ: chọn Nâng cao → Tiếp tục truy cập.")
        print_addresses("https", port, names["ip"])
    else:
        from server.certs import lan_ip_addresses

        print_addresses("http", port, lan_ip_addresses())
        print("[MÁY CHỦ] Điện thoại cần HTTPS để mở camera: chạy py -m server.run --https")
    if not args.no_warmup:
        from server.app.web_detection import start_background_warmup

        start_background_warmup(app)
    app.run(host=host, port=port, debug=False, threaded=True, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
