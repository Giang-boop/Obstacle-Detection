from datetime import date, datetime


def parse_client_datetime(value, fallback=None):
    if value is None or value == "":
        return fallback
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return fallback
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def parse_form_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def to_iso(value):
    if value is None:
        return None
    return value.isoformat(timespec="seconds")


def format_datetime(value, pattern="%d/%m/%Y %H:%M:%S"):
    if value is None:
        return "—"
    return value.strftime(pattern)


def format_duration(seconds):
    if seconds is None:
        return "—"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours} giờ {minutes:02d} phút"
    if minutes:
        return f"{minutes} phút {secs:02d} giây"
    return f"{secs} giây"
