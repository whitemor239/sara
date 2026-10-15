from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.template.loader import render_to_string

from .admin_forms import ProductPricingForm, RecipeIngredientFormSet, WeightOptionPricingForm, WeightOptionPricingFormSet
from .models import (
    ContactMessage,
    CustomerProfile,
    DietaryTag,
    Ingredient,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    ProductImage,
    ProductReview,
    ProductWeightOption,
    RecipeIngredient,
)
from .pricing import calculate_product_pricing, recalculate_product_prices
from .widgets import FlavorTagWidget, MoneyField, MoneyInput


class MoneyFieldsAdminMixin:
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ("price", "discounted_price", "original_price", "price_per_kg"):
            kwargs.update(form_class=MoneyField, widget=MoneyInput)
        return super().formfield_for_dbfield(db_field, **kwargs)


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("author_name", "product", "rating", "is_approved", "persian_created_at")
    list_filter = ("is_approved", "rating", "created_at")
    list_editable = ("is_approved",)
    search_fields = ("author_name", "comment", "product__name")
    actions = ("approve_reviews", "unapprove_reviews")

    @admin.display(description="زمان ثبت")
    def persian_created_at(self, obj):
        from .templatetags.bakery_tags import jalali_date
        return jalali_date(obj.created_at, "full")

    @admin.action(description="تأیید نظرات انتخاب‌شده برای نمایش")
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="لغو تأیید نظرات انتخاب‌شده")
    def unapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductWeightOptionInline(MoneyFieldsAdminMixin, admin.TabularInline):
    model = ProductWeightOption
    form = WeightOptionPricingForm
    formset = WeightOptionPricingFormSet
    extra = 1
    fields = ("weight", "weight_grams", "price", "discounted_price", "is_available", "sort_order")


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    formset = RecipeIngredientFormSet
    autocomplete_fields = ("ingredient",)
    fields = ("ingredient", "quantity_grams")
    extra = 1


@admin.register(Ingredient)
class IngredientAdmin(MoneyFieldsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "price_per_kg", "product_count", "last_updated")
    list_editable = ("price_per_kg",)
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("last_updated",)
    fields = ("name", "price_per_kg", "last_updated")
    date_hierarchy = "updated_at"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_product_count=Count("recipe_items__product", distinct=True))

    @admin.display(description="محصولات مصرف‌کننده", ordering="_product_count")
    def product_count(self, obj):
        from .templatetags.bakery_tags import fa_digits
        return fa_digits(obj._product_count)

    @admin.display(description="آخرین به‌روزرسانی")
    def last_updated(self, obj):
        from .templatetags.bakery_tags import jalali_date
        return jalali_date(obj.updated_at, "full") if obj.updated_at else "پس از ذخیره ثبت می‌شود."


@admin.register(Product)
class ProductAdmin(MoneyFieldsAdminMixin, admin.ModelAdmin):
    form = ProductPricingForm
    inlines = (RecipeIngredientInline, ProductWeightOptionInline, ProductImageInline)
    list_display = ("name", "category", "flavor", "price", "auto_pricing", "discounted_price", "discount_percent", "is_available", "is_featured", "sort_order")
    list_filter = ("auto_pricing", "category", "dietary_tags", "is_available", "is_featured")
    list_editable = ("price", "discounted_price", "is_available", "is_featured", "sort_order")
    search_fields = ("name", "short_description", "flavor", "ingredients", "ingredient_choices__name", "recipe_items__ingredient__name")
    autocomplete_fields = ("ingredient_choices",)
    filter_horizontal = ("dietary_tags",)
    readonly_fields = ("pricing_summary", "last_price_calculation", "legacy_ingredients")
    actions = ("recalculate_prices",)
    fieldsets = (
        ("مشخصات محصول", {"fields": ("name", "slug", "category", "short_description", "description", "ingredient_choices", "flavor", "dietary_tags")}),
        ("قیمت‌گذاری و دستور مصرف", {
            "fields": ("auto_pricing", "recipe_yield_grams", "profit_percent", "price", "discounted_price", "pricing_summary", "last_price_calculation"),
            "description": "قیمت مواد را از بخش «مواد اولیه و قیمت روز» وارد کنید؛ مقدار مصرف هر ماده را در جدول پایین صفحه بنویسید. محاسبات پس از ذخیره به‌روز می‌شوند. سود روی هزینهٔ مواد افزوده و فقط قیمت نهایی به نزدیک‌ترین تومان گرد می‌شود.",
        }),
        ("تصویر و نمایش", {"fields": ("image", "image_alt", "is_available", "is_featured", "sort_order")}),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if obj and obj.ingredients:
            title, options = fieldsets[0]
            fieldsets[0] = (title, {**options, "fields": (*options["fields"], "legacy_ingredients")})
        return fieldsets

    @admin.display(description="ترکیبات قبلی")
    def legacy_ingredients(self, obj):
        return obj.ingredients

    @admin.display(description="جزئیات محاسبه با قیمت روز مواد")
    def pricing_summary(self, obj):
        if not obj.pk:
            return "پس از ثبت محصول و مواد مصرفی، ریز محاسبات اینجا نمایش داده می‌شود."
        if not obj.auto_pricing and not obj.recipe_yield_grams:
            return "برای دیدن ریز هزینه، وزن دستور پایه و مواد مصرفی را وارد و ذخیره کنید."
        try:
            pricing = calculate_product_pricing(obj)
        except ValidationError as error:
            return " ".join(error.messages)
        return render_to_string("admin/bakery/product/pricing_summary.html", {"pricing": pricing, "auto_pricing": obj.auto_pricing})

    @admin.display(description="آخرین محاسبهٔ قیمت")
    def last_price_calculation(self, obj):
        from .templatetags.bakery_tags import jalali_date
        return jalali_date(obj.price_calculated_at, "full") if obj.price_calculated_at else "هنوز محاسبه نشده است."

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if "ingredient_choices" in form.changed_data:
            # An intentional selection replaces the legacy free-text list.
            Product.objects.filter(pk=form.instance.pk).update(ingredients="")
            form.instance.ingredients = ""
        if form.instance.auto_pricing:
            recalculate_product_prices(form.instance.pk, strict=True)
            form.instance.refresh_from_db(fields=("price", "price_calculated_at"))

    @admin.action(description="محاسبهٔ دوبارهٔ قیمت محصولات خودکار", permissions=("change",))
    def recalculate_prices(self, request, queryset):
        count = 0
        for product in queryset.filter(auto_pricing=True).order_by("pk"):
            try:
                recalculate_product_prices(product.pk, strict=True)
                count += 1
            except ValidationError as error:
                self.message_user(request, f"{product.name}: {' '.join(error.messages)}", level="error")
        from .templatetags.bakery_tags import fa_digits
        self.message_user(request, f"قیمت {fa_digits(count)} محصول خودکار به‌روز شد.")

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "flavor":
            kwargs["widget"] = FlavorTagWidget
        return super().formfield_for_dbfield(db_field, **kwargs)

    @admin.display(description="تخفیف")
    def discount_percent(self, obj):
        if obj.discount_percent:
            from .templatetags.bakery_tags import fa_digits
            return f"{fa_digits(obj.discount_percent)}٪"
        return "-"


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order")
    list_editable = ("sort_order",)
    search_fields = ("name",)


@admin.register(DietaryTag)
class DietaryTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "description")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "weight_label", "unit_price", "quantity")
    fields = ("product", "product_name", "weight_label", "formatted_unit_price", "quantity")
    readonly_fields = (*readonly_fields, "formatted_unit_price")

    @admin.display(description="قیمت واحد (تومان)")
    def formatted_unit_price(self, obj):
        from .templatetags.bakery_tags import toman
        return toman(obj.unit_price)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("short_number", "customer_name", "phone", "customer", "formatted_total", "payment_status", "status", "persian_created_at")
    list_filter = ("status", "payment_status", "fulfillment", "created_at")
    search_fields = ("customer_name", "phone", "authority", "ref_id")
    readonly_fields = ("number", "customer", "total", "formatted_total", "authority", "ref_id", "created_at", "paid_at")
    inlines = (OrderItemInline,)

    def get_fields(self, request, obj=None):
        return [field for field in super().get_fields(request, obj) if field != "total"]

    @admin.display(description="جمع کل (تومان)", ordering="total")
    def formatted_total(self, obj):
        from .templatetags.bakery_tags import toman
        return toman(obj.total)

    @admin.display(description="شماره")
    def short_number(self, obj):
        return str(obj.number)[:8]

    @admin.display(description="زمان ثبت")
    def persian_created_at(self, obj):
        from .templatetags.bakery_tags import jalali_date
        return jalali_date(obj.created_at, "full")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "phone", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    list_editable = ("is_read",)
    search_fields = ("name", "phone", "subject", "message")
    readonly_fields = ("created_at",)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("phone", "display_name", "created_at")
    search_fields = ("phone", "display_name", "user__username")
    readonly_fields = ("phone", "created_at")
