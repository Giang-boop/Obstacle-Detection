# === MO TA FILE ===
# server/app/pagination.py
# CHUC NANG: Phan trang dung chung
# ===================

from flask import current_app, request

from .extensions import db


def requested_page():
    page = request.args.get("page", 1, type=int) or 1
    return max(page, 1)


def paginate_query(query, per_page_key="LIST_PER_PAGE"):
    per_page = current_app.config.get(per_page_key) or current_app.config.get("LIST_PER_PAGE", 15)
    page = requested_page()
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    if pagination.pages and page > pagination.pages:
        pagination = db.paginate(query, page=pagination.pages, per_page=per_page, error_out=False)
    return pagination


def search_condition(keyword, *columns):
    pattern = f"%{keyword}%"
    return db.or_(*(column.ilike(pattern) for column in columns))


def clean_args(values):
    return {key: value for key, value in values.items() if value not in (None, "")}
