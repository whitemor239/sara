from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def normalize_money_input(value):
    if not isinstance(value, str):
        return value
    value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    return "".join(character for character in value if character not in ",٬" and not character.isspace())


def grouped_integer(value):
    if value is None or value == "":
        return ""
    normalized = normalize_money_input(str(value))
    if not normalized.isascii() or not normalized.isdigit():
        return str(value)
    return f"{int(normalized):,}".replace(",", "٬")


def decimal_toman(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if not amount.is_finite():
            return ""
    except (InvalidOperation, ValueError, TypeError):
        return ""
    text = f"{amount:,.2f}".rstrip("0").rstrip(".").replace(",", "٬").replace(".", "٫")
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
