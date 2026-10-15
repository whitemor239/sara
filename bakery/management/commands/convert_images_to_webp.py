from django.core.management.base import BaseCommand

from bakery.image_utils import use_webp_image
from bakery.models import HeroSlide, Product, ProductImage


class Command(BaseCommand):
    help = "Convert existing product, gallery and hero images and update their stored URLs."

    def handle(self, *args, **options):
        for model in (Product, ProductImage, HeroSlide):
            for instance in model.objects.exclude(image="").iterator():
                previous = instance.image.name
                use_webp_image(instance)
                self.stdout.write(f"{model.__name__} #{instance.pk}: {previous} -> {instance.image.name}")
