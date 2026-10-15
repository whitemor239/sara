import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse


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


class Product(models.Model):
    name = models.CharField("نام محصول", max_length=120)
    slug = models.SlugField("نشانی انگلیسی (اختیاری)", max_length=140, unique=True, blank=True)
    short_description = models.CharField("توضیح کوتاه", max_length=220, blank=True)
    description = models.TextField("توضیحات", blank=True)
    price = models.PositiveIntegerField("قیمت با تخفیف / فروش (تومان)", validators=[MinValueValidator(1)])
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
    flavor = models.CharField("طعم / مزه", max_length=160, blank=True, help_text="مثلاً: شکلاتی، دارچینی، وانیلی، سیب، کاراملی، میوه‌ای، پنیری، بادامی")
    category = models.ForeignKey(ProductCategory, verbose_name="دسته‌بندی", related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    dietary_tags = models.ManyToManyField(
        DietaryTag,
        verbose_name="ویژگی‌های غذایی",
        related_name="products",
        blank=True,
        help_text="فقط ویژگی‌هایی را ثبت کنید که با دستور پخت و ترکیبات محصول تأیید شده‌اند.",
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

    @property
    def has_weight_options(self):
        return self.weight_options.filter(is_available=True).exists()

    @property
    def available_weight_options(self):
        return self.weight_options.filter(is_available=True)

    @property
    def starting_price(self):
        first_opt = self.weight_options.filter(is_available=True).order_by("price").first()
        if first_opt:
            return first_opt.price
        return self.price

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > self.price:
            return int(round((1 - (self.price / self.original_price)) * 100))
        return 0


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


class ProductWeightOption(models.Model):
    product = models.ForeignKey(Product, related_name="weight_options", on_delete=models.CASCADE, verbose_name="محصول")
    weight = models.CharField("وزن / بسته‌بندی", max_length=60, help_text="مثلاً: ۲۵۰ گرم، ۵۰۰ گرم، ۱ کیلوگرم، ۴ عددی")
    weight_grams = models.DecimalField(
        "وزن محاسباتی (گرم)", max_digits=12, decimal_places=3, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="برای عنوان‌هایی مثل «۵۰۰ گرم» یا «۱ کیلوگرم» خودکار تشخیص داده می‌شود؛ برای بسته‌های عددی، وزن واقعی کل بسته را وارد کنید.",
    )
    price = models.PositiveIntegerField("قیمت فروش (تومان)", validators=[MinValueValidator(1)])
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
    name = models.CharField("نام مادهٔ اولیه", max_length=120, unique=True)
    price_per_kg = models.PositiveIntegerField("قیمت هر کیلو (تومان)", validators=[MinValueValidator(1)])
    updated_at = models.DateTimeField("آخرین به‌روزرسانی قیمت", auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "مادهٔ اولیه"
        verbose_name_plural = "مواد اولیه و قیمت روز"
        constraints = [models.CheckConstraint(condition=models.Q(price_per_kg__gt=0), name="ingredient_positive_price")]

    def __str__(self):
        return self.name

    @transaction.atomic
    def save(self, *args, **kwargs):
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
