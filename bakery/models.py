import uuid
from math import ceil
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


class BlogCategory(models.Model):
    name = models.CharField("نام دسته‌بندی", max_length=80, unique=True)
    slug = models.SlugField("نشانی انگلیسی", max_length=100, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "دسته‌بندی بلاگ"
        verbose_name_plural = "دسته‌بندی‌های بلاگ"

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    title = models.CharField("عنوان مقاله", max_length=200)
    slug = models.SlugField("نشانی انگلیسی (اختیاری)", max_length=220, unique=True, blank=True)
    category = models.ForeignKey(BlogCategory, verbose_name="دسته‌بندی", related_name="posts", on_delete=models.SET_NULL, null=True, blank=True)
    excerpt = models.TextField("خلاصهٔ مقاله", max_length=450, help_text="چند جمله برای کارت مقاله و معرفی بالای صفحه.")
    body = models.TextField("متن مقاله", help_text="بین پاراگراف‌ها یک خط خالی بگذارید. متن به‌صورت امن و با حفظ پاراگراف‌ها نمایش داده می‌شود.")
    image = models.ImageField("تصویر شاخص", upload_to="blog/", blank=True, help_text="پیشنهاد: عکس افقی ۱۶۰۰ × ۱۰۰۰ پیکسل؛ خودکار به WebP تبدیل می‌شود.")
    image_alt = models.CharField("توضیح تصویر", max_length=180, blank=True)
    author_name = models.CharField("نام نویسنده", max_length=100, default="تحریریهٔ نارون")
    product = models.ForeignKey("Product", verbose_name="محصول مرتبط / رسپی", on_delete=models.SET_NULL, null=True, blank=True, related_name="blog_posts", help_text="اختیاری؛ رسپی عمومی محصول و مقدار مواد آن در مقاله نمایش داده می‌شود.")
    is_published = models.BooleanField("انتشار عمومی", default=False)
    is_featured = models.BooleanField("مطلب شاخص بلاگ", default=False)
    published_at = models.DateTimeField("زمان انتشار", default=timezone.now, help_text="با انتخاب زمان آینده، مطلب تا آن زمان نمایش داده نمی‌شود.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-pk")
        verbose_name = "مقالهٔ بلاگ"
        verbose_name_plural = "مقاله‌های بلاگ"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"journal-{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})

    @property
    def reading_minutes(self):
        return max(1, ceil(len(self.body.split()) / 180))

    @property
    def cover_image(self):
        return self.image or (self.product.image if self.product_id else None)


class ProductCategory(models.Model):
    name = models.CharField("نام دسته", max_length=80)
    slug = models.SlugField("شناسهٔ دسته", max_length=120, unique=True, blank=True)
    sort_order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "دسته‌بندی منو"
        verbose_name_plural = "دسته‌بندی‌های منو"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"category-{uuid.uuid4().hex[:10]}"
        super().save(*args, **kwargs)


class DietaryTag(models.Model):
    name = models.CharField("عنوان ویژگی غذایی", max_length=80)
    slug = models.SlugField("شناسهٔ ویژگی", max_length=120, unique=True, blank=True)
    description = models.CharField("توضیح", max_length=180, blank=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "ویژگی غذایی"
        verbose_name_plural = "ویژگی‌های غذایی"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"diet-{uuid.uuid4().hex[:10]}"
        super().save(*args, **kwargs)


class SalePricingMixin:
    @property
    def regular_price(self):
        # Retain compatibility with older records using original_price + price.
        return self.original_price if self.original_price and self.original_price > self.price else self.price

    @property
    def selling_price(self):
        if self.discounted_price and 0 < self.discounted_price < self.regular_price:
            return self.discounted_price
        return self.price

    @property
    def price_before_discount(self):
        return self.regular_price if self.selling_price < self.regular_price else None

    @property
    def discount_percent(self):
        if self.regular_price and self.selling_price < self.regular_price:
            return int(round((1 - self.selling_price / self.regular_price) * 100))
        return 0


class Product(SalePricingMixin, models.Model):
    name = models.CharField("نام محصول", max_length=120)
    slug = models.SlugField("نشانی انگلیسی (اختیاری)", max_length=140, unique=True, blank=True)
    short_description = models.CharField("توضیح کوتاه", max_length=220, blank=True)
    description = models.TextField("توضیحات", blank=True)
    price = models.PositiveIntegerField("قیمت عادی / پایه (تومان)", validators=[MinValueValidator(1)])
    discounted_price = models.PositiveIntegerField(
        "قیمت با تخفیف (تومان)", default=0, blank=True,
        help_text="اختیاری؛ خالی یا صفر یعنی بدون تخفیف. برای اعمال تخفیف، مبلغی کمتر از قیمت عادی وارد کنید.",
    )
    original_price = models.PositiveIntegerField(
        "قیمت اصلی قبل از تخفیف (تومان)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="در صورت وارد کردن عددی بزرگتر از قیمت فروش، درصد تخفیف و خط‌خوردگی قیمت به صورت خودکار نمایش داده می‌شود.",
    )
    auto_pricing = models.BooleanField(
        "محاسبهٔ خودکار قیمت از مواد اولیه", default=False,
        help_text="با تغییر قیمت مواد، دستور مصرف، وزن یا درصد سود، قیمت فروش دوباره محاسبه می‌شود.",
    )
    recipe_yield_grams = models.DecimalField(
        "وزن محصول نهاییِ دستور پخت (گرم)", max_digits=12, decimal_places=3,
        null=True, blank=True, validators=[MinValueValidator(Decimal("0.001"))],
        help_text="وزن محصول آماده پس از پخت؛ مثلاً اگر مواد برای یک کیک ۵۰۰ گرمی است، ۵۰۰ وارد کنید. برای محصول بدون گزینهٔ وزن، قیمت همین مقدار به‌عنوان قیمت یک محصول ثبت می‌شود.",
    )
    profit_percent = models.DecimalField(
        "درصد سود روی هزینهٔ مواد", max_digits=7, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="مثلاً هزینهٔ ۱۰۰٬۰۰۰ تومان با سود ۳۰٪، قیمت فروش ۱۳۰٬۰۰۰ تومان می‌شود. دستمزد، بسته‌بندی و سایر هزینه‌ها در این محاسبه لحاظ نمی‌شوند.",
    )
    price_calculated_at = models.DateTimeField("آخرین محاسبهٔ قیمت", null=True, blank=True, editable=False)
    image = models.ImageField("تصویر", upload_to="products/", blank=True)
    image_alt = models.CharField("توضیح تصویر", max_length=180, blank=True)
    ingredients = models.CharField("ترکیبات", max_length=240, blank=True)
    ingredient_choices = models.ManyToManyField(
        "Ingredient", verbose_name="ترکیبات", related_name="listed_products", blank=True,
        help_text="از مواد اولیه انتخاب کنید. مواد ثبت‌شده در دستور پخت هم در ترکیبات محصول نمایش داده می‌شوند.",
    )
    flavor = models.CharField("طعم / مزه", max_length=160, blank=True, help_text="مثلاً: شکلاتی، دارچینی، وانیلی، سیب، کاراملی، میوه‌ای، پنیری، بادامی")
    category = models.ForeignKey(ProductCategory, verbose_name="دسته‌بندی", related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    dietary_tags = models.ManyToManyField(
        DietaryTag,
        verbose_name="ویژگی‌های غذایی",
        related_name="products",
        blank=True,
        help_text="فقط ویژگی‌هایی را ثبت کنید که با دستور پخت و ترکیبات محصول تأیید شده‌اند.",
    )
    recipe_instructions = models.TextField(
        "دستور و شیوهٔ پخت (رسپی)",
        blank=True,
        help_text="مراحل آماده‌سازی و نکات پخت شیرینی. در صورت وارد کردن، در صفحهٔ محصول برای مشتریان نیز نمایش داده می‌شود.",
    )
    baking_time_minutes = models.PositiveSmallIntegerField(
        "زمان آماده‌سازی / پخت (دقیقه)",
        null=True,
        blank=True,
        help_text="اختیاری؛ مثلاً ۴۵ دقیقه.",
    )
    baking_temperature = models.CharField(
        "دمای فر / پخت",
        max_length=60,
        blank=True,
        help_text="اختیاری؛ مثلاً: ۱۸۰ درجه سانتی‌گراد",
    )
    is_available = models.BooleanField("موجود", default=True)
    is_featured = models.BooleanField("نمایش در صفحهٔ نخست", default=False)
    sort_order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name = "شیرینی"
        verbose_name_plural = "شیرینی‌ها"

    def __str__(self):
        return self.name

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"pastry-{uuid.uuid4().hex[:12]}"
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.auto_pricing and not self.recipe_yield_grams:
            raise ValidationError({"recipe_yield_grams": "برای محاسبهٔ خودکار، وزن محصول نهایی دستور پخت را وارد کنید."})
        if not self.auto_pricing and self.discounted_price and self.regular_price and self.discounted_price >= self.regular_price:
            raise ValidationError({"discounted_price": "قیمت با تخفیف باید کمتر از قیمت عادی باشد؛ برای حذف تخفیف صفر وارد کنید."})

    @property
    def has_weight_options(self):
        return self.weight_options.filter(is_available=True).exists()

    @property
    def available_weight_options(self):
        return self.weight_options.filter(is_available=True)

    @property
    def starting_price(self):
        first_opt = self.cheapest_weight_option
        if first_opt:
            return first_opt.selling_price
        return self.selling_price

    @property
    def cheapest_weight_option(self):
        return min(self.available_weight_options, key=lambda option: option.selling_price, default=None)

    @property
    def starting_original_price(self):
        option = self.cheapest_weight_option
        return option.price_before_discount if option else self.price_before_discount

    @property
    def display_ingredients(self):
        if not self.pk:
            return self.ingredients
        names = [ingredient.name for ingredient in self.ingredient_choices.all()]
        names.extend(item.ingredient.name for item in self.recipe_items.all())
        if not names:
            return self.ingredients
        names.extend(part.strip() for part in self.ingredients.replace("،", ",").split(",") if part.strip())
        return "، ".join(dict.fromkeys(names))


    @property
    def gallery_images(self):
        images = []
        if self.image:
            images.append({"url": self.image.url, "alt": self.image_alt or self.name})
        images.extend({"url": photo.image.url, "alt": photo.alt_text or self.name} for photo in self.photos.all() if photo.image)
        return images

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField("تصویر محصول", upload_to="products/gallery/")
    alt_text = models.CharField("توضیح تصویر", max_length=180, blank=True)
    sort_order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        ordering = ("sort_order", "pk")
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"


class ProductWeightOption(SalePricingMixin, models.Model):
    product = models.ForeignKey(Product, related_name="weight_options", on_delete=models.CASCADE, verbose_name="محصول")
    weight = models.CharField("وزن / بسته‌بندی", max_length=60, help_text="مثلاً: ۲۵۰ گرم، ۵۰۰ گرم، ۱ کیلوگرم، ۴ عددی")
    weight_grams = models.DecimalField(
        "وزن محاسباتی (گرم)", max_digits=12, decimal_places=3, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="برای عنوان‌هایی مثل «۵۰۰ گرم» یا «۱ کیلوگرم» خودکار تشخیص داده می‌شود؛ برای بسته‌های عددی، وزن واقعی کل بسته را وارد کنید.",
    )
    price = models.PositiveIntegerField("قیمت عادی (تومان)", validators=[MinValueValidator(1)])
    discounted_price = models.PositiveIntegerField(
        "قیمت با تخفیف (تومان)", default=0, blank=True,
        help_text="اختیاری؛ خالی یا صفر یعنی بدون تخفیف برای این وزن.",
    )
    original_price = models.PositiveIntegerField(
        "قیمت قبل از تخفیف (تومان)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="اختیاری؛ در صورت تخفیف‌دار بودن این وزن خاص",
    )
    is_available = models.BooleanField("موجود", default=True)
    sort_order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)

    class Meta:
        ordering = ("sort_order", "price", "pk")
        verbose_name = "گزینهٔ وزن و قیمت"
        verbose_name_plural = "گزینه‌های وزن و قیمت"

    def __str__(self):
        return f"{self.product.name} — {self.weight} ({self.price:,} تومان)"

    @property
    def resolved_weight_grams(self):
        from .pricing import parse_weight_grams
        return self.weight_grams if self.weight_grams is not None else parse_weight_grams(self.weight)

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Ingredient(models.Model):
    class Unit(models.TextChoices):
        KILOGRAM = "kg", "کیلوگرم (kg)"
        GRAM = "g", "گرم (g)"
        PACKAGE = "pkg", "بسته / عدد"

    name = models.CharField("نام مادهٔ اولیه", max_length=120, unique=True)
    purchase_unit = models.CharField(
        "واحد خرید",
        max_length=10,
        choices=Unit.choices,
        default=Unit.KILOGRAM,
        blank=True,
        help_text="واحدی که این ماده را تهیه می‌کنید (کیلوگرم، گرم یا بسته/قوطی).",
    )
    purchase_quantity = models.DecimalField(
        "مقدار هر واحد خرید",
        max_digits=10,
        decimal_places=3,
        default=Decimal("1"),
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="مثلاً برای بسته ۲۵۰ گرمی، عدد ۲۵۰ یا برای ۱ کیلوگرم، عدد ۱ را وارد کنید.",
    )
    purchase_price = models.PositiveIntegerField(
        "قیمت خرید این واحد (تومان)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="مبلغی که برای این مقدار پرداخته‌اید. در صورت خالی بودن، از قیمت هر کیلو محاسبه می‌شود.",
    )
    price_per_kg = models.PositiveIntegerField("قیمت هر کیلو (تومان)", validators=[MinValueValidator(1)])
    package_weight_grams = models.DecimalField(
        "وزن هر بسته (گرم)",
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="فقط در صورتی که واحد خرید «بسته / عدد» است، وزن هر بسته را به گرم وارد کنید تا نرخ کیلو به درستی محاسبه شود.",
    )
    updated_at = models.DateTimeField("آخرین به‌روزرسانی قیمت", auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "مادهٔ اولیه"
        verbose_name_plural = "مواد اولیه و قیمت روز"
        constraints = [models.CheckConstraint(condition=models.Q(price_per_kg__gt=0), name="ingredient_positive_price")]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.purchase_unit == self.Unit.PACKAGE and not self.package_weight_grams:
            raise ValidationError({"package_weight_grams": "برای واحد بسته/عدد، وزن هر بسته به گرم الزامی است."})

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.purchase_unit:
            self.purchase_unit = self.Unit.KILOGRAM
        if not self.purchase_quantity:
            self.purchase_quantity = Decimal("1")

        if self.pk:
            old = Ingredient.objects.filter(pk=self.pk).values("price_per_kg", "purchase_price").first()
            if old:
                if self.purchase_price and self.purchase_price != old["purchase_price"]:
                    if self.purchase_unit == self.Unit.KILOGRAM:
                        self.price_per_kg = max(1, int(round(Decimal(self.purchase_price) / Decimal(self.purchase_quantity))))
                    elif self.purchase_unit == self.Unit.GRAM:
                        self.price_per_kg = max(1, int(round((Decimal(self.purchase_price) / Decimal(self.purchase_quantity)) * Decimal(1000))))
                    elif self.purchase_unit == self.Unit.PACKAGE and self.package_weight_grams:
                        total_grams = Decimal(self.purchase_quantity) * Decimal(self.package_weight_grams)
                        self.price_per_kg = max(1, int(round((Decimal(self.purchase_price) / total_grams) * Decimal(1000))))
                elif self.price_per_kg != old["price_per_kg"] or not self.purchase_price:
                    if self.purchase_unit == self.Unit.KILOGRAM:
                        self.purchase_price = max(1, int(round(Decimal(self.price_per_kg) * Decimal(self.purchase_quantity))))
                    elif self.purchase_unit == self.Unit.GRAM:
                        self.purchase_price = max(1, int(round((Decimal(self.price_per_kg) / Decimal(1000)) * Decimal(self.purchase_quantity))))
                    elif self.purchase_unit == self.Unit.PACKAGE and self.package_weight_grams:
                        total_grams = Decimal(self.purchase_quantity) * Decimal(self.package_weight_grams)
                        self.purchase_price = max(1, int(round((Decimal(self.price_per_kg) / Decimal(1000)) * total_grams)))
        else:
            if self.purchase_price:
                if self.purchase_unit == self.Unit.KILOGRAM:
                    self.price_per_kg = max(1, int(round(Decimal(self.purchase_price) / Decimal(self.purchase_quantity))))
                elif self.purchase_unit == self.Unit.GRAM:
                    self.price_per_kg = max(1, int(round((Decimal(self.purchase_price) / Decimal(self.purchase_quantity)) * Decimal(1000))))
                elif self.purchase_unit == self.Unit.PACKAGE and self.package_weight_grams:
                    total_grams = Decimal(self.purchase_quantity) * Decimal(self.package_weight_grams)
                    self.price_per_kg = max(1, int(round((Decimal(self.purchase_price) / total_grams) * Decimal(1000))))
            elif self.price_per_kg:
                if self.purchase_unit == self.Unit.KILOGRAM:
                    self.purchase_price = max(1, int(round(Decimal(self.price_per_kg) * Decimal(self.purchase_quantity))))
                elif self.purchase_unit == self.Unit.GRAM:
                    self.purchase_price = max(1, int(round((Decimal(self.price_per_kg) / Decimal(1000)) * Decimal(self.purchase_quantity))))
                elif self.purchase_unit == self.Unit.PACKAGE and self.package_weight_grams:
                    total_grams = Decimal(self.purchase_quantity) * Decimal(self.package_weight_grams)
                    self.purchase_price = max(1, int(round((Decimal(self.price_per_kg) / Decimal(1000)) * total_grams)))

        super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    product = models.ForeignKey(Product, related_name="recipe_items", on_delete=models.CASCADE, verbose_name="محصول")
    ingredient = models.ForeignKey(Ingredient, related_name="recipe_items", on_delete=models.PROTECT, verbose_name="مادهٔ اولیه")
    quantity_grams = models.DecimalField(
        "مقدار مصرف در دستور پایه (گرم)", max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
    )

    class Meta:
        ordering = ("pk",)
        verbose_name = "مادهٔ مصرفی دستور پخت"
        verbose_name_plural = "مواد مصرفی دستور پخت"
        constraints = [
            models.UniqueConstraint(fields=("product", "ingredient"), name="unique_product_recipe_ingredient"),
            models.CheckConstraint(condition=models.Q(quantity_grams__gt=0), name="recipe_positive_quantity"),
        ]

    def __str__(self):
        return f"{self.product.name}: {self.ingredient.name}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت‌شده"
        PREPARING = "preparing", "در حال آماده‌سازی"
        READY = "ready", "آمادهٔ تحویل"
        COMPLETED = "completed", "تکمیل‌شده"
        CANCELLED = "cancelled", "لغوشده"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "پرداخت‌نشده"
        INITIATED = "initiated", "در انتظار پرداخت"
        PAID = "paid", "پرداخت‌شده"
        FAILED = "failed", "ناموفق"

    number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="حساب مشتری", related_name="bakery_orders", on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField("نام مشتری", max_length=120)
    phone = models.CharField("شماره تماس", max_length=20)
    address = models.TextField("نشانی", blank=True)
    fulfillment = models.CharField("روش دریافت", max_length=20, choices=(("delivery", "ارسال"), ("pickup", "تحویل حضوری")), default="delivery")
    note = models.TextField("یادداشت مشتری", blank=True)
    status = models.CharField("وضعیت سفارش", max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField("وضعیت پرداخت", max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    total = models.PositiveIntegerField("جمع کل (تومان)", default=0)
    authority = models.CharField("شناسه پرداخت زرین‌پال", max_length=64, blank=True, db_index=True)
    ref_id = models.CharField("کد پیگیری زرین‌پال", max_length=64, blank=True)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)
    paid_at = models.DateTimeField("زمان پرداخت", null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"

    def __str__(self):
        return f"سفارش {str(self.number)[:8]}: {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE, verbose_name="سفارش")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="محصول")
    weight_option = models.ForeignKey(ProductWeightOption, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="گزینهٔ وزن")
    weight_label = models.CharField("وزن / بسته‌بندی", max_length=60, blank=True)
    product_name = models.CharField("نام محصول", max_length=160)
    unit_price = models.PositiveIntegerField("قیمت واحد (تومان)")
    quantity = models.PositiveSmallIntegerField("تعداد", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "ردیف سفارش"
        verbose_name_plural = "ردیف‌های سفارش"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"


class ContactMessage(models.Model):
    name = models.CharField("نام", max_length=120)
    phone = models.CharField("شمارهٔ همراه", max_length=20)
    subject = models.CharField("موضوع", max_length=140)
    message = models.TextField("پیام", max_length=3000)
    is_read = models.BooleanField("خوانده شده", default=False)
    created_at = models.DateTimeField("زمان دریافت", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام‌های تماس"

    def __str__(self):
        return f"{self.subject}: {self.name}"


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="حساب کاربری", related_name="customer_profile", on_delete=models.CASCADE)
    phone = models.CharField("شمارهٔ همراه", max_length=11, unique=True)
    display_name = models.CharField("نام نمایشی", max_length=120, blank=True)
    created_at = models.DateTimeField("زمان عضویت", auto_now_add=True)

    class Meta:
        verbose_name = "پروفایل مشتری"
        verbose_name_plural = "پروفایل‌های مشتریان"

    def __str__(self):
        return self.display_name or self.phone


class LoginCode(models.Model):
    session_nonce = models.UUIDField("شناسهٔ نشست", unique=True, default=uuid.uuid4, editable=False)
    phone = models.CharField("شمارهٔ همراه", max_length=11, db_index=True)
    code_digest = models.CharField("هش کد", max_length=64)
    ip_address = models.GenericIPAddressField("نشانی IP", null=True, blank=True, db_index=True)
    attempts = models.PositiveSmallIntegerField("تلاش‌های ورود", default=0)
    created_at = models.DateTimeField("زمان درخواست", auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField("زمان انقضا")
    used_at = models.DateTimeField("زمان مصرف", null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "کد یک‌بارمصرف ورود"
        verbose_name_plural = "کدهای یک‌بارمصرف ورود"

    def __str__(self):
        return f"کد ورود برای {self.phone}"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, verbose_name="محصول", related_name="reviews", on_delete=models.CASCADE)
    customer = models.ForeignKey(CustomerProfile, verbose_name="مشتری", related_name="reviews", on_delete=models.SET_NULL, null=True, blank=True)
    author_name = models.CharField("نام نویسنده", max_length=120)
    rating = models.PositiveSmallIntegerField("امتیاز (از ۵)", default=5, validators=[MinValueValidator(1)])
    comment = models.TextField("نظر و تجربه")
    is_approved = models.BooleanField("تأیید برای نمایش", default=False)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "نظر مشتری"
        verbose_name_plural = "نظرات مشتریان"

    def __str__(self):
        return f"نظر {self.author_name} برای {self.product.name}"


class HeroSlide(models.Model):
    title = models.CharField("عنوان اسلاید", max_length=140, blank=True, help_text="اختیاری؛ در صورت خالی بودن، متن پیش‌فرض نمایش داده می‌شود.")
    subtitle = models.CharField("توضیح کوتاه / زیرعنوان", max_length=240, blank=True)
    button_text = models.CharField("متن دکمه", max_length=60, default="دیدن منو و سفارش")
    button_url = models.CharField("پیوند دکمه", max_length=200, default="/menu/")
    image = models.ImageField("تصویر اسلاید", upload_to="hero/", help_text="سایز پیشنهادی: 1920x1080 یا 1600x900 پیکسل (افقی ۱۶:۹ یا ۳:۲)")
    image_alt = models.CharField("متن جایگزین تصویر", max_length=180, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveSmallIntegerField("ترتیب نمایش", default=0)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "اسلاید هدر صفحه اصلی"
        verbose_name_plural = "اسلایدهای هدر صفحه اصلی"

    def __str__(self):
        return self.title or f"اسلاید {self.id}"
