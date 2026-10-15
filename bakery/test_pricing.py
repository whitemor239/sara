from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Ingredient, Order, OrderItem, Product, ProductWeightOption, RecipeIngredient
from .pricing import calculate_product_pricing, parse_weight_grams, recalculate_product_prices


class RecipePricingTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="کیک دستور پایه", price=80000, recipe_yield_grams=500, profit_percent=25)
        self.flour = Ingredient.objects.create(name="آرد", price_per_kg=50000)
        self.butter = Ingredient.objects.create(name="کره", price_per_kg=150000)
        self.flour_line = RecipeIngredient.objects.create(product=self.product, ingredient=self.flour, quantity_grams=400)
        self.butter_line = RecipeIngredient.objects.create(product=self.product, ingredient=self.butter, quantity_grams=200)
        self.small = ProductWeightOption.objects.create(product=self.product, weight="۲۵۰ گرم", price=100, sort_order=0)
        self.base = ProductWeightOption.objects.create(product=self.product, weight="۵۰۰ گرم", price=200, sort_order=1)
        self.large = ProductWeightOption.objects.create(product=self.product, weight="۱ کیلوگرم", price=300, sort_order=2)
        self.product.auto_pricing = True
        self.product.save()

    def test_recipe_cost_markup_and_scaled_ingredient_quantities(self):
        pricing = calculate_product_pricing(self.product)
        self.assertEqual(pricing["cost"], Decimal("50000"))
        self.assertEqual(pricing["price"], 62500)
        self.assertEqual([row["price"] for row in pricing["weights"]], [31250, 62500, 125000])
        self.assertEqual([line["grams"] for line in pricing["weights"][2]["ingredients"]], [Decimal("800"), Decimal("400")])
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 62500)
        self.assertIsNotNone(self.product.price_calculated_at)
        self.large.refresh_from_db()
        self.assertEqual(self.large.price, 125000)

    def test_changing_ingredient_price_updates_every_related_automatic_product(self):
        other = Product.objects.create(name="محصول دیگر", price=1, recipe_yield_grams=250, profit_percent=50)
        RecipeIngredient.objects.create(product=other, ingredient=self.butter, quantity_grams=100)
        other.auto_pricing = True
        other.save()
        self.butter.price_per_kg = 250000
        self.butter.save()
        self.product.refresh_from_db()
        self.large.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.product.price, 87500)
        self.assertEqual(self.large.price, 175000)
        self.assertEqual(other.price, 37500)

    def test_quantity_profit_yield_and_weight_changes_recalculate(self):
        self.flour_line.quantity_grams = 800
        self.flour_line.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 87500)
        self.product.profit_percent = 50
        self.product.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 105000)
        self.product.recipe_yield_grams = 1000
        self.product.save()
        self.large.refresh_from_db()
        self.assertEqual(self.large.price, 105000)
        self.large.weight_grams = Decimal("1500")
        self.large.save()
        self.large.refresh_from_db()
        self.assertEqual(self.large.price, 157500)

    def test_removing_one_recipe_line_recalculates(self):
        self.butter_line.delete()
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 25000)

    def test_explicit_package_weight_and_inactive_weights_are_priced(self):
        package = ProductWeightOption.objects.create(
            product=self.product, weight="۴ عددی", weight_grams=750, price=1, is_available=False,
        )
        package.refresh_from_db()
        self.assertEqual(package.price, 93750)

    def test_price_is_rounded_after_scaling_not_before(self):
        self.product.profit_percent = 0
        self.product.save()
        self.butter_line.delete()
        self.flour.price_per_kg = 1000
        self.flour.save()
        self.flour_line.quantity_grams = Decimal("1.4")
        self.flour_line.save()
        option = ProductWeightOption.objects.create(product=self.product, weight="۱۲۰۰ گرم", price=1)
        self.product.refresh_from_db()
        option.refresh_from_db()
        self.assertEqual(self.product.price, 1)
        self.assertEqual(option.price, 3)
        self.flour_line.quantity_grams = Decimal("1.5")
        self.flour_line.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 2)

    def test_manual_prices_and_original_discount_price_are_preserved(self):
        self.product.auto_pricing = False
        self.product.price = 99999
        self.product.original_price = 110000
        self.product.save()
        self.large.price = 222222
        self.large.save()
        self.butter.price_per_kg = 250000
        self.butter.save()
        self.product.refresh_from_db()
        self.large.refresh_from_db()
        self.assertEqual(self.product.price, 99999)
        self.assertEqual(self.product.original_price, 110000)
        self.assertEqual(self.large.price, 222222)

    def test_automatic_unweighted_product_gets_base_price(self):
        self.product.weight_options.all().delete()
        self.butter.price_per_kg = 250000
        self.butter.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 87500)
        self.assertFalse(self.product.has_weight_options)

    def test_existing_order_prices_are_not_rewritten(self):
        order = Order.objects.create(customer_name="مشتری", phone="09121234567", total=62500)
        line = OrderItem.objects.create(order=order, product=self.product, weight_option=self.base,
                                        product_name=self.product.name, weight_label=self.base.weight, unit_price=62500, quantity=1)
        self.butter.price_per_kg = 250000
        self.butter.save()
        order.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual(order.total, 62500)
        self.assertEqual(line.unit_price, 62500)

    def test_invalid_recipe_and_ambiguous_weight_fail_explicitly(self):
        ProductWeightOption.objects.create(product=self.product, weight="۴ عددی", price=1)
        with self.assertRaisesMessage(ValidationError, "وزن محاسباتی"):
            recalculate_product_prices(self.product.pk, strict=True)
        for field, value in (("recipe_yield_grams", 0), ("profit_percent", -1)):
            product = Product.objects.get(pk=self.product.pk)
            setattr(product, field, value)
            with self.assertRaises(ValidationError):
                product.full_clean()
        self.flour_line.quantity_grams = 0
        with self.assertRaises(ValidationError):
            self.flour_line.full_clean()
        self.flour.price_per_kg = 0
        with self.assertRaises(ValidationError):
            self.flour.full_clean()

    def test_ingredient_in_use_is_protected_and_product_can_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.flour.delete()
        self.product.delete()
        self.assertFalse(RecipeIngredient.objects.exists())

    def test_price_change_rolls_back_if_recalculation_fails(self):
        self.butter.price_per_kg = 250000
        with patch("bakery.pricing_signals.recalculate_product_prices", side_effect=RuntimeError("calculation failed")):
            with self.assertRaises(RuntimeError):
                self.butter.save()
        self.butter.refresh_from_db()
        self.assertEqual(self.butter.price_per_kg, 150000)

    def test_explicit_mass_parser_supports_persian_and_arabic_digits(self):
        for label, grams in (("۵۰۰ گرم", 500), ("۰٫۵ کیلوگرم", 500), ("١ كيلوگرم", 1000), ("1.25 kg", 1250), ("250G", 250)):
            with self.subTest(label=label):
                self.assertEqual(parse_weight_grams(label), Decimal(grams))
        for label in ("۴ عددی", "۲۰۰ تا ۳۰۰ گرم", "500", "0g", "-1kg", "1kg extra"):
            with self.subTest(label=label):
                self.assertIsNone(parse_weight_grams(label))


class RecipePricingAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username="pricing-admin", password="test-password", email="")
        self.client.force_login(self.admin)
        self.flour = Ingredient.objects.create(name="آرد", price_per_kg=50000)
        self.butter = Ingredient.objects.create(name="کره", price_per_kg=150000)

    def product_payload(self):
        return {
            "name": "کیک محاسباتی", "slug": "", "short_description": "", "description": "",
            "price": "", "original_price": "", "auto_pricing": "on", "recipe_yield_grams": "500",
            "profit_percent": "25", "sort_order": "0", "is_available": "on",
            "recipe_items-TOTAL_FORMS": "2", "recipe_items-INITIAL_FORMS": "0",
            "recipe_items-0-ingredient": str(self.flour.pk), "recipe_items-0-quantity_grams": "400",
            "recipe_items-1-ingredient": str(self.butter.pk), "recipe_items-1-quantity_grams": "200",
            "weight_options-TOTAL_FORMS": "2", "weight_options-INITIAL_FORMS": "0",
            "weight_options-0-weight": "۵۰۰ گرم", "weight_options-0-price": "", "weight_options-0-sort_order": "0", "weight_options-0-is_available": "on",
            "weight_options-1-weight": "۱ کیلوگرم", "weight_options-1-price": "", "weight_options-1-sort_order": "1", "weight_options-1-is_available": "on",
            "photos-TOTAL_FORMS": "0", "photos-INITIAL_FORMS": "0", "_save": "ذخیره",
        }

    def test_admin_can_create_recipe_and_weights_without_manual_prices(self):
        response = self.client.post(reverse("admin:bakery_product_add"), self.product_payload())
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name="کیک محاسباتی")
        self.assertEqual(product.price, 62500)
        self.assertEqual(list(product.weight_options.values_list("price", flat=True)), [62500, 125000])
        page = self.client.get(reverse("admin:bakery_product_change", args=[product.pk]))
        self.assertContains(page, "مواد مصرفی دستور پایه")
        self.assertContains(page, "قیمت و مصرف متناسب با هر وزن")
        self.assertContains(page, "۱۲۵٬۰۰۰")
        self.assertNotContains(page, "&lt;table&gt;")

    def test_admin_validates_missing_recipe_and_ambiguous_package(self):
        data = self.product_payload()
        data["recipe_items-TOTAL_FORMS"] = "0"
        response = self.client.post(reverse("admin:bakery_product_add"), data)
        self.assertContains(response, "حداقل یک مادهٔ اولیه")
        self.assertFalse(Product.objects.exists())
        data = self.product_payload()
        data["weight_options-1-weight"] = "۴ عددی"
        response = self.client.post(reverse("admin:bakery_product_add"), data)
        self.assertContains(response, "وزن واقعی بسته را به گرم وارد کنید")
        self.assertFalse(Product.objects.exists())
        data["weight_options-1-weight_grams"] = "750"
        response = self.client.post(reverse("admin:bakery_product_add"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.get().weight_options.get(weight="۴ عددی").price, 93750)

    def test_admin_requires_yield_and_nonnegative_markup(self):
        for field, value, expected in (("recipe_yield_grams", "", "وزن محصول نهایی دستور پخت"), ("profit_percent", "-1", "بزرگتر")):
            with self.subTest(field=field):
                data = self.product_payload()
                data[field] = value
                response = self.client.post(reverse("admin:bakery_product_add"), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["adminform"].form.errors.get(field))
                self.assertFalse(Product.objects.exists())

    def test_admin_manual_prices_remain_required(self):
        data = self.product_payload()
        data.pop("auto_pricing")
        response = self.client.post(reverse("admin:bakery_product_add"), data)
        self.assertContains(response, "در حالت دستی قیمت فروش را وارد کنید")
        data["price"] = "80000"
        response = self.client.post(reverse("admin:bakery_product_add"), data)
        self.assertContains(response, "در حالت دستی قیمت این وزن را وارد کنید")
        self.assertFalse(Product.objects.exists())

    def test_admin_ingredient_edit_reprices_and_dashboard_links_to_materials(self):
        self.client.post(reverse("admin:bakery_product_add"), self.product_payload())
        response = self.client.post(reverse("admin:bakery_ingredient_change", args=[self.butter.pk]),
                                    {"name": self.butter.name, "price_per_kg": "250000", "_save": "ذخیره"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.get().price, 87500)
        material_list = self.client.get(reverse("admin:bakery_ingredient_changelist"))
        self.assertContains(material_list, "مواد اولیه و قیمت روز")
        dashboard = self.client.get(reverse("admin:index"))
        self.assertContains(dashboard, reverse("admin:bakery_ingredient_changelist"))

    def test_admin_cannot_delete_all_ingredients_while_auto_pricing_is_enabled(self):
        self.client.post(reverse("admin:bakery_product_add"), self.product_payload())
        product = Product.objects.get()
        data = self.product_payload()
        data["recipe_items-INITIAL_FORMS"] = "2"
        for index, item in enumerate(product.recipe_items.all()):
            data[f"recipe_items-{index}-id"] = str(item.pk)
            data[f"recipe_items-{index}-DELETE"] = "on"
        data["weight_options-TOTAL_FORMS"] = "0"
        response = self.client.post(reverse("admin:bakery_product_change", args=[product.pk]), data)
        self.assertContains(response, "حداقل یک مادهٔ اولیه")
        self.assertEqual(product.recipe_items.count(), 2)

    def test_material_admin_requires_permissions(self):
        staff = get_user_model().objects.create_user(username="pricing-no-access", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("admin:bakery_ingredient_changelist")).status_code, 403)

    def test_admin_bulk_recalculation_action(self):
        self.client.post(reverse("admin:bakery_product_add"), self.product_payload())
        product = Product.objects.get()
        Ingredient.objects.filter(pk=self.butter.pk).update(price_per_kg=250000)
        response = self.client.post(reverse("admin:bakery_product_changelist"), {
            "action": "recalculate_prices", "_selected_action": [str(product.pk)],
        })
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.price, 87500)

    def test_admin_can_update_recipe_markup_and_weight_together(self):
        self.client.post(reverse("admin:bakery_product_add"), self.product_payload())
        product = Product.objects.get()
        data = self.product_payload()
        data["profit_percent"] = "50"
        data["recipe_items-INITIAL_FORMS"] = "2"
        data["weight_options-INITIAL_FORMS"] = "2"
        for index, item in enumerate(product.recipe_items.all()):
            data[f"recipe_items-{index}-id"] = str(item.pk)
        for index, option in enumerate(product.weight_options.all()):
            data[f"weight_options-{index}-id"] = str(option.pk)
        data["recipe_items-0-quantity_grams"] = "800"
        data["weight_options-1-weight"] = "۲ کیلوگرم"
        response = self.client.post(reverse("admin:bakery_product_change", args=[product.pk]), data)
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.price, 105000)
        self.assertEqual(product.weight_options.get(weight="۲ کیلوگرم").price, 420000)
