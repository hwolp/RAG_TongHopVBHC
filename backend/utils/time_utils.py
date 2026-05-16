import datetime


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def utc_timestamp() -> int:
    return int(utc_now().timestamp())

