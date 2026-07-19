"""
اتصال به API زرین‌پال (نسخه v4 - JSON).
با تغییر ZARINPAL_SANDBOX در settings.py، بدون تغییر کد، بین محیط تست و واقعی سوییچ می‌کنیم.

⚠️ نکته‌ی مهم قبل از رفتن به Real:
واحد پول در API زرین‌پال بسته به نسخه فرق دارد (بعضی نسخه‌ها ریال، v4 تومان می‌گیرد).
قبل از اتصال نهایی حتماً یک تراکنش کوچک روی sandbox بزن و مبلغ برگشتی در پنل تست را
با مبلغ ارسالی مقایسه کن تا از صحت واحد پول مطمئن بشیم؛ اینجا فرض بر تومان (Toman) گذاشته شده.
"""

from decimal import Decimal

import requests
from django.conf import settings


class ZarinpalError(Exception):
    def __init__(self, message, code=None, raw=None):
        super().__init__(message)
        self.code = code
        self.raw = raw


def _is_sandbox() -> bool:
    return getattr(settings, "ZARINPAL_SANDBOX", True)


def _base_url() -> str:
    return (
        "https://sandbox.zarinpal.com/pg/v4/payment/"
        if _is_sandbox()
        else "https://payment.zarinpal.com/pg/v4/payment/"
    )


def _startpay_url() -> str:
    return (
        "https://sandbox.zarinpal.com/pg/StartPay/"
        if _is_sandbox()
        else "https://payment.zarinpal.com/pg/StartPay/"
    )


def get_payment_redirect_url(authority: str) -> str:
    return f"{_startpay_url()}{authority}"


def request_payment(*, amount: Decimal, description: str, callback_url: str,
                     mobile: str = "", email: str = "") -> str:
    """
    از زرین‌پال Authority می‌گیرد. خروجی: authority (str)
    خطا در صورت شکست، ZarinpalError می‌اندازد.
    """
    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": int(amount),
        "description": description,
        "callback_url": callback_url,
    }
    if mobile:
        payload["metadata"] = {"mobile": mobile}
    if email:
        payload.setdefault("metadata", {})["email"] = email

    try:
        resp = requests.post(_base_url() + "request.json", json=payload, timeout=15)
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ZarinpalError(f"خطا در ارتباط با درگاه پرداخت: {e}")

    errors = data.get("errors")
    result = data.get("data", {})

    if errors:
        raise ZarinpalError(f"درگاه پرداخت درخواست را رد کرد: {errors}", raw=data)

    if result.get("code") != 100:
        raise ZarinpalError(f"درخواست پرداخت ناموفق بود (کد {result.get('code')})", raw=data)

    return result["authority"]


def verify_payment(*, amount: Decimal, authority: str) -> str:
    """
    پرداخت را نزد زرین‌پال تایید می‌کند. خروجی: ref_id (str)
    کد 100 = تایید موفق تازه، کد 101 = قبلاً تایید شده (idempotent، هردو باید موفق تلقی شوند).
    """
    payload = {
        "merchant_id": settings.ZARINPAL_MERCHANT_ID,
        "amount": int(amount),
        "authority": authority,
    }
    try:
        resp = requests.post(_base_url() + "verify.json", json=payload, timeout=15)
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ZarinpalError(f"خطا در ارتباط با درگاه پرداخت هنگام تایید: {e}")

    errors = data.get("errors")
    result = data.get("data", {})

    if errors:
        raise ZarinpalError(f"تایید پرداخت رد شد: {errors}", raw=data)

    if result.get("code") not in (100, 101):
        raise ZarinpalError(f"پرداخت تایید نشد (کد {result.get('code')})", raw=data)

    return str(result.get("ref_id", ""))
