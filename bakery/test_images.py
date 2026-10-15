from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import HeroSlide, Product, ProductImage


class WebPUploadTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        settings = override_settings(MEDIA_ROOT=directory.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def upload(self):
        data = BytesIO()
        Image.new("RGBA", (1000, 800), (200, 100, 50, 128)).save(data, "PNG")
        return SimpleUploadedFile("photo.png", data.getvalue(), content_type="image/png")

    def assert_webp(self, instance):
        self.assertTrue(instance.image.name.endswith(".webp"))
        name = instance.image.name
        instance.refresh_from_db()
        self.assertEqual(instance.image.name, name)
        with instance.image.open("rb") as source:
            with Image.open(source) as image:
                self.assertEqual(image.format, "WEBP")
                self.assertEqual(image.size, (1000, 800))
                self.assertIn("A", image.getbands())

    def test_product_and_gallery_upload_use_actual_webp(self):
        product = Product.objects.create(name="شیرینی", price=1000, image=self.upload())
        self.assert_webp(product)
        photo = ProductImage.objects.create(product=product, image=self.upload())
        self.assert_webp(photo)
        self.assertTrue(all(image["url"].endswith(".webp") for image in product.gallery_images))

    def test_original_is_deleted_only_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            product = Product.objects.create(name="شیرینی", price=1000, image=self.upload())
            storage = product.image.storage
            self.assertTrue(storage.exists("products/photo.png"))
            self.assert_webp(product)
        self.assertFalse(storage.exists("products/photo.png"))
        self.assertTrue(storage.exists(product.image.name))

    def test_hero_html_uses_webp_and_replacing_image_updates_url(self):
        slide = HeroSlide.objects.create(title="تصویر هدر", image=self.upload())
        self.assert_webp(slide)
        previous_name = slide.image.name
        slide.image = self.upload()
        slide.save()
        self.assert_webp(slide)
        self.assertNotEqual(slide.image.name, previous_name)
        response = self.client.get("/")
        self.assertContains(response, f'src="{slide.image.url}"')
        self.assertNotContains(response, 'src="/media/hero/photo.png"')
