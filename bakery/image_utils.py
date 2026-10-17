from pathlib import Path
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps

CATALOG_WIDTHS = (320, 640, 960)


def use_webp_image(instance):
    """Store a full-size WebP and persist its name as the actual image URL."""
    field = instance.image
    if not field:
        return
    if Path(field.name).suffix.lower() != ".webp":
        storage = field.storage
        if not storage.exists(field.name):
            return
        with storage.open(field.name, "rb") as uploaded:
            with Image.open(uploaded) as original:
                source = ImageOps.exif_transpose(original)
                source = source.convert("RGBA" if "A" in source.getbands() or "transparency" in source.info else "RGB")
                output = BytesIO()
                source.save(output, "WEBP", quality=82, method=6)
        name = storage.save(str(Path(field.name).with_suffix(".webp")), ContentFile(output.getvalue()))
        # Avoid recursively firing save signals; also update this in-memory instance.
        type(instance).objects.filter(pk=instance.pk).update(image=name)
        instance.image = name
        original_name = field.name
        database = instance._state.db or "default"

        def delete_original():
            from .models import BlogPost, HeroSlide, Product, ProductImage

            # Another record may still share the uploaded original.
            if not any(model.objects.using(database).filter(image=original_name).exists()
                       for model in (Product, ProductImage, HeroSlide, BlogPost)):
                storage.delete(original_name)

        transaction.on_commit(delete_original, using=database)
    generate_image_variants(instance.image)


def generate_image_variants(image_field, widths=CATALOG_WIDTHS, quality=82):
    """
    Given an ImageField instance, generate WebP variants alongside the original file.
    Does nothing if image is empty or file doesn't exist on disk.
    """
    if not image_field:
        return []
    try:
        path = Path(image_field.path)
    except (ValueError, AttributeError):
        return []

    if not path.is_file():
        return []

    created_paths = []
    try:
        with Image.open(path) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            for width in widths:
                target = path.with_name(f"{path.stem}-catalog-{width}.webp")
                new_height = max(1, round(source.height * width / source.width))
                resized = source.resize((width, new_height), Image.Resampling.LANCZOS)
                resized.save(target, "WEBP", quality=quality, method=6)
                created_paths.append(target)
    except Exception:
        return []

    return created_paths
