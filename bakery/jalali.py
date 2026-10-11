"""
Lightweight standalone Jalali (Shamsi / Solar Hijri) date conversion algorithm.
Requires no external dependencies.
"""
from datetime import date, datetime
from django.utils import timezone


JALALI_MONTH_NAMES = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

JALALI_WEEKDAY_NAMES = (
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
)


def gregorian_to_jalali(gy, gm, gd):
    """Convert Gregorian (gy, gm, gd) to Jalali (jy, jm, jd)."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621

    gy2 = gy if gm > 2 else gy - 1
    days = (
        365 * gy
        + (gy2 + 4) // 4
        - (gy2 + 100) // 100
        + (gy2 + 400) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461

    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        days -= 186
        jm = 7 + days // 30
        jd = 1 + days % 30

    return jy, jm, jd


def to_jalali_tuple(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        return gregorian_to_jalali(dt.year, dt.month, dt.day), (dt.hour, dt.minute)
    if isinstance(dt, date):
        return gregorian_to_jalali(dt.year, dt.month, dt.day), None
    return None
