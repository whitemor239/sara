from pathlib import Path
from PIL import Image, ImageOps

CATALOG_WIDTHS = (320, 640, 960)


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
