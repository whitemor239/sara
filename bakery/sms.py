import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSDeliveryError(Exception):
    pass


def send_login_code(phone, code):
    backend = settings.OTP_SMS_BACKEND
    if backend == "console":
        if not settings.DEBUG:
            raise SMSDeliveryError("ارسال پیامک در محیط واقعی پیکربندی نشده است.")
        logger.warning("Development login code for %s: %s", phone, code)
        return

    if backend != "kavenegar":
        raise SMSDeliveryError("درگاه پیامک پیکربندی نشده است.")
    if not settings.KAVENEGAR_API_KEY or not settings.KAVENEGAR_VERIFY_TEMPLATE:
        raise SMSDeliveryError("تنظیمات پیامک کامل نیست.")

    url = f"https://api.kavenegar.com/v1/{settings.KAVENEGAR_API_KEY}/verify/lookup.json"
    try:
        response = requests.post(
            url,
            data={"receptor": phone, "token": code, "template": settings.KAVENEGAR_VERIFY_TEMPLATE},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Kavenegar OTP request failed")
        raise SMSDeliveryError("ارسال پیامک انجام نشد. کمی بعد دوباره تلاش کنید.") from exc

    if payload.get("return", {}).get("status") != 200:
        logger.warning("Kavenegar rejected an OTP request")
        raise SMSDeliveryError("ارسال پیامک انجام نشد. کمی بعد دوباره تلاش کنید.")
