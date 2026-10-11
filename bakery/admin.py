from django.contrib import admin

from .models import ContactMessage, CustomerProfile, DietaryTag, Order, OrderItem, Product, ProductCategory, ProductReview


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
    from .models import ProductImage
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = (ProductImageInline,)
    list_display = ("name", "category", "price", "original_price", "discount_percent", "is_available", "is_featured", "sort_order")
    list_filter = ("category", "dietary_tags", "is_available", "is_featured")
    list_editable = ("price", "original_price", "is_available", "is_featured", "sort_order")
    search_fields = ("name", "short_description", "ingredients")
    filter_horizontal = ("dietary_tags",)

    @admin.display(description="تخفیف")
    def discount_percent(self, obj):
        if obj.original_price and obj.original_price > obj.price:
            off = round((1 - (obj.price / obj.original_price)) * 100)
            return f"{off}٪"
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
    readonly_fields = ("product", "product_name", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("short_number", "customer_name", "phone", "customer", "total", "payment_status", "status", "persian_created_at")
    list_filter = ("status", "payment_status", "fulfillment", "created_at")
    search_fields = ("customer_name", "phone", "authority", "ref_id")
    readonly_fields = ("number", "customer", "total", "authority", "ref_id", "created_at", "paid_at")
    inlines = (OrderItemInline,)

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
