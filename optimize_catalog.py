"""Generate catalog WebP variants; preserve uploaded originals."""
from pathlib import Path
from PIL import Image, ImageOps
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tastytum.settings")
import django
django.setup()
from bakery.models import Product
for product in Product.objects.exclude(image=""):
    path = Path(product.image.path)
    if not path.is_file():
        continue
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        for width in (320, 640, 960):
            image = source.copy()
            image = image.resize((width, round(source.height * width / source.width)), Image.Resampling.LANCZOS)
            target = path.with_name(path.stem + f"-catalog-{width}.webp")
            image.save(target, "WEBP", quality=82, method=6)
            print(target.name, target.stat().st_size)
