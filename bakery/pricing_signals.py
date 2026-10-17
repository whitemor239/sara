from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .image_utils import use_webp_image
from .models import BlogPost, HeroSlide, Ingredient, Product, ProductImage, ProductWeightOption, RecipeIngredient
from .pricing import recalculate_product_prices


@receiver(post_save, sender=Product)
def product_price_changed(sender, instance, raw=False, **kwargs):
    if not raw and instance.auto_pricing:
        pricing = recalculate_product_prices(instance.pk)
        if pricing is not None:
            instance.price = pricing["price"]


@receiver(post_save, sender=Product)
def product_image_uploaded(sender, instance, raw=False, **kwargs):
    if not raw and instance.image:
        use_webp_image(instance)


@receiver(post_save, sender=ProductImage)
def gallery_image_uploaded(sender, instance, raw=False, **kwargs):
    if not raw and instance.image:
        use_webp_image(instance)


@receiver(post_save, sender=HeroSlide)
@receiver(post_save, sender=BlogPost)
def hero_slide_image_uploaded(sender, instance, raw=False, **kwargs):
    if not raw and instance.image:
        use_webp_image(instance)


@receiver(post_save, sender=Ingredient)
def ingredient_price_changed(sender, instance, raw=False, **kwargs):
    if not raw:
        products = Product.objects.filter(auto_pricing=True, recipe_items__ingredient=instance).order_by("pk")
        for product_id in products.values_list("pk", flat=True).distinct():
            recalculate_product_prices(product_id)


@receiver(pre_save, sender=RecipeIngredient)
@receiver(pre_save, sender=ProductWeightOption)
def remember_previous_recipe_product(sender, instance, raw=False, **kwargs):
    instance._previous_pricing_product = None
    if not raw and instance.pk:
        instance._previous_pricing_product = sender.objects.filter(pk=instance.pk).values_list("product_id", flat=True).first()


@receiver(post_save, sender=RecipeIngredient)
@receiver(post_save, sender=ProductWeightOption)
def recipe_or_weight_changed(sender, instance, raw=False, **kwargs):
    if not raw:
        product_ids = {instance.product_id, getattr(instance, "_previous_pricing_product", None)} - {None}
        for product_id in sorted(product_ids):
            recalculate_product_prices(product_id)


@receiver(post_delete, sender=RecipeIngredient)
@receiver(post_delete, sender=ProductWeightOption)
def recipe_or_weight_deleted(sender, instance, **kwargs):
    recalculate_product_prices(instance.product_id)
