from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import BlogCategory, BlogPost, Ingredient, Product, RecipeIngredient


class BlogTests(TestCase):
    def setUp(self):
        self.category = BlogCategory.objects.create(name="نکته‌های پخت", slug="baking")

    def post(self, **kwargs):
        values = dict(title="راز یک کوکی خوش‌عطر", excerpt="از دمای کره تا زمان استراحت خمیر.", body="مواد را اندازه بگیرید.\n\nخمیر را استراحت دهید.", is_published=True, category=self.category)
        values.update(kwargs)
        return BlogPost.objects.create(**values)

    def test_drafts_and_future_posts_are_not_public(self):
        public = self.post()
        draft = self.post(title="پیش‌نویس محرمانه", is_published=False)
        future = self.post(title="مطلب آینده", published_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse("blog"))
        self.assertContains(response, public.title)
        for post in (draft, future):
            self.assertNotContains(response, post.title)
            self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)

    def test_category_search_and_pagination(self):
        chosen = self.post(title="آرد مناسب کوکی")
        other_category = BlogCategory.objects.create(name="نگهداری", slug="storage")
        other = self.post(title="نگهداری نان", category=other_category)
        response = self.client.get(reverse("blog"), {"category": "baking", "q": "آرد"})
        self.assertContains(response, chosen.title)
        self.assertNotContains(response, other.title)
        for index in range(10):
            self.post(title=f"مقاله {index}")
        page = self.client.get(reverse("blog"), {"page": 2, "category": "baking"})
        self.assertEqual(page.context["page"].number, 2)
        self.assertContains(page, "category=baking")

    def test_recipe_renders_quantities_but_not_internal_costs(self):
        product = Product.objects.create(name="کوکی", price=10000, recipe_instructions="مواد را مخلوط کنید.", baking_time_minutes=20, recipe_yield_grams=500, profit_percent=32)
        flour = Ingredient.objects.create(name="آرد سفید", price_per_kg=123456)
        RecipeIngredient.objects.create(product=product, ingredient=flour, quantity_grams=250)
        post = self.post(product=product, body='<script>alert("unsafe")</script>')
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, "مواد را مخلوط کنید.")
        self.assertContains(response, "۲۵۰ گرم")
        self.assertContains(response, "۲۰ دقیقه")
        self.assertNotContains(response, "123456")
        self.assertNotContains(response, '<script>alert("unsafe")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_empty_blog_and_article_without_recipe(self):
        self.assertContains(self.client.get(reverse("blog")), "اولین یادداشت، به‌زودی.")
        post = self.post()
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="journal-recipe"')

    def test_blog_admin_can_publish_article(self):
        user = get_user_model().objects.create_superuser(username="blog-editor", password="test-password")
        self.client.force_login(user)
        response = self.client.post(reverse("admin:bakery_blogpost_add"), {
            "title": "راهنمای پخت", "slug": "baking-guide", "category": self.category.pk,
            "excerpt": "نکته‌های پخت خانگی", "body": "فر را پیش‌گرم کنید.", "author_name": "نارون",
            "is_published": "on", "published_at_0": "2026-01-01", "published_at_1": "12:00:00", "_save": "ذخیره",
        })
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(reverse("blog")), "راهنمای پخت")

    def test_blog_image_uses_webp(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            output = BytesIO()
            Image.new("RGB", (320, 200), "brown").save(output, "PNG")
            with self.captureOnCommitCallbacks(execute=True):
                post = self.post(image=SimpleUploadedFile("blog.png", output.getvalue(), content_type="image/png"))
            post.refresh_from_db()
            self.assertTrue(post.image.name.endswith(".webp"))
            self.assertFalse(post.image.storage.exists("blog/blog.png"))
            self.assertContains(self.client.get(post.get_absolute_url()), f'src="{post.image.url}"')
