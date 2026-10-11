_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_iranian_mobile(value):
    phone = "".join(value.translate(_DIGITS).split()).replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("0098"):
        phone = "0" + phone[4:]
    if len(phone) != 11 or not phone.startswith("09") or not phone.isascii() or not phone.isdigit():
        raise ValueError("Not a valid Iranian mobile number")
    return phone
