from urllib.parse import urljoin

import requests
from django.conf import settings


class ZarinpalError(Exception):
    pass


class Zarinpal:
    API_BASE = "https://sandbox.zarinpal.com/pg/v4/"  # Overridden for live mode below.
    LIVE_API_BASE = "https://payment.zarinpal.com/pg/v4/"
    SANDBOX_API_BASE = "https://sandbox.zarinpal.com/pg/v4/"
    LIVE_GATEWAY = "https://www.zarinpal.com/pg/StartPay/"
    SANDBOX_GATEWAY = "https://sandbox.zarinpal.com/pg/StartPay/"
    TIMEOUT = 15

    @classmethod
    def _api_base(cls):
        return cls.SANDBOX_API_BASE if settings.ZARINPAL_SANDBOX else cls.LIVE_API_BASE

    @classmethod
    def _gateway_base(cls):
        return cls.SANDBOX_GATEWAY if settings.ZARINPAL_SANDBOX else cls.LIVE_GATEWAY

    @classmethod
    def request_payment(cls, order, callback_url):
        if getattr(settings, "ZARINPAL_AUTO_APPROVE", False) and not settings.ZARINPAL_MERCHANT_ID:
            import uuid
            return f"test-authority-{uuid.uuid4().hex[:12]}"
        if not settings.ZARINPAL_MERCHANT_ID:
            raise ZarinpalError("درگاه پرداخت هنوز پیکربندی نشده است.")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": order.total * 10,  # Zarinpal API expects rials; the storefront stores tomans.
            "callback_url": callback_url,
            "description": f"{settings.ZARINPAL_DESCRIPTION} - {str(order.number)[:8]}",
            "metadata": {"mobile": order.phone},
        }
        try:
            response = requests.post(urljoin(cls._api_base(), "payment/request.json"), json=payload, timeout=cls.TIMEOUT)
            response.raise_for_status()
            data = response.json().get("data", {})
        except (requests.RequestException, ValueError) as exc:
            raise ZarinpalError("ارتباط با درگاه پرداخت برقرار نشد.") from exc
        if data.get("code") not in (100, 101) or not data.get("authority"):
            raise ZarinpalError("درگاه پرداخت نتوانست درخواست را ثبت کند.")
        return data["authority"]

    @classmethod
    def verify_payment(cls, order):
        if getattr(settings, "ZARINPAL_AUTO_APPROVE", False) and not settings.ZARINPAL_MERCHANT_ID:
            import uuid
            return f"TEST-REF-{uuid.uuid4().hex[:8].upper()}"
        if not settings.ZARINPAL_MERCHANT_ID or not order.authority:
            raise ZarinpalError("اطلاعات پرداخت برای بررسی کامل نیست.")
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": order.total * 10,
            "authority": order.authority,
        }
        try:
            response = requests.post(urljoin(cls._api_base(), "payment/verify.json"), json=payload, timeout=cls.TIMEOUT)
            response.raise_for_status()
            data = response.json().get("data", {})
        except (requests.RequestException, ValueError) as exc:
            raise ZarinpalError("بررسی پرداخت از درگاه انجام نشد.") from exc
        if data.get("code") not in (100, 101):
            raise ZarinpalError("پرداخت تأیید نشد.")
        return str(data.get("ref_id", ""))

    @classmethod
    def payment_url(cls, authority):
        return urljoin(cls._gateway_base(), authority)
