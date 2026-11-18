import sys

from server.app import create_app
from server.app.seed_data import seed_database


def main():
    app = create_app()
    with app.app_context():
        summary = seed_database()
    sys.stdout.reconfigure(encoding="utf-8")
    print("Đã khởi tạo lại cơ sở dữ liệu:", app.config["SQLALCHEMY_DATABASE_URI"])
    for label, value in summary.items():
        print(f"  - {label}: {value}")


if __name__ == "__main__":
    main()
