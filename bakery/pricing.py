"""Recipe costing in grams and tomans, with a markup on ingredient cost."""

import re
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


def parse_weight_grams(label):
    """Recognize an explicit mass only; never guess a package's unit weight."""
    normalized = str(label).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    normalized = normalized.replace("٫", ".").replace("ك", "ک").replace("ي", "ی").replace("\u200c", "")
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(کیلوگرم|کیلو|گرم|kg|g)\s*", normalized, re.IGNORECASE)
    if not match:
        return None
    amount = Decimal(match[1])
    if match[2].lower() in ("کیلوگرم", "کیلو", "kg"):
        amount *= 1000
    return amount if amount > 0 else None


def selling_price(cost, profit_percent):
    # Round only the final sale price, not each ingredient or the base product.
    value = cost * (Decimal(1) + profit_percent / Decimal(100))
    return max(1, int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP)))


def calculate_product_pricing(product):
    if not product.recipe_yield_grams or product.recipe_yield_grams <= 0:
        raise ValidationError("وزن محصول نهایی دستور پخت باید بیشتر از صفر باشد.")
    if product.profit_percent < 0:
        raise ValidationError("درصد سود نمی‌تواند منفی باشد.")
    recipe = list(product.recipe_items.select_related("ingredient"))
    if not recipe:
        raise ValidationError("حداقل یک مادهٔ اولیه و مقدار مصرف برای دستور پخت ثبت کنید.")
    ingredients = []
    for item in recipe:
        if item.quantity_grams <= 0 or item.ingredient.price_per_kg <= 0:
            raise ValidationError("مقدار مصرف و قیمت مواد اولیه باید بیشتر از صفر باشند.")
        cost = item.quantity_grams * Decimal(item.ingredient.price_per_kg) / Decimal(1000)
        ingredients.append({"name": item.ingredient.name, "grams": item.quantity_grams, "cost": cost})
    cost = sum((line["cost"] for line in ingredients), Decimal(0))
    weights = []
    for option in product.weight_options.all():
        grams = option.resolved_weight_grams
        if grams is None or grams <= 0:
            raise ValidationError(f"وزن محاسباتیِ گزینهٔ «{option.weight}» را به گرم وارد کنید.")
        factor = grams / product.recipe_yield_grams
        option_cost = cost * factor
        option_price = selling_price(option_cost, product.profit_percent)
        weights.append({
            "id": option.pk, "label": option.weight, "grams": grams,
            "cost": option_cost, "price": option_price,
            "selling_price": option.discounted_price if 0 < option.discounted_price < option_price else option_price,
            "ingredients": [dict(line, grams=line["grams"] * factor, cost=line["cost"] * factor) for line in ingredients],
        })
    base_price = selling_price(cost, product.profit_percent)
    return {
        "grams": product.recipe_yield_grams, "cost": cost,
        "profit_percent": product.profit_percent, "price": base_price,
        "selling_price": product.discounted_price if 0 < product.discounted_price < base_price else base_price,
        "ingredients": ingredients, "weights": weights,
    }


@transaction.atomic
def recalculate_product_prices(product_id, *, strict=False):
    from .models import Product, ProductWeightOption

    product = Product.objects.select_for_update().filter(pk=product_id, auto_pricing=True).first()
    if product is None:
        return None
    try:
        pricing = calculate_product_pricing(product)
    except ValidationError:
        if strict:
            raise
        # Parent/inline saves can temporarily precede a complete recipe.
        # Admin formsets validate completeness before the enclosing transaction saves.
        return None
    Product.objects.filter(pk=product.pk).update(price=pricing["price"], price_calculated_at=timezone.now())
    options = [ProductWeightOption(pk=row["id"], price=row["price"]) for row in pricing["weights"]]
    if options:
        ProductWeightOption.objects.bulk_update(options, ["price"])
    return pricing
