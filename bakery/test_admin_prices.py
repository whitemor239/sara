from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse

from .models import Ingredient, Product, ProductWeightOption, RecipeIngredient
from .money import decimal_toman
from .widgets import MoneyField, MoneyInput


class MoneyFieldTests(SimpleTestCase):
    def test_grouped_english_persian_and_arabic_inputs_are_saved_as_integers(self):
        field = MoneyField(min_value=0, required=False)
        for value in ("1,250,000", "۱٬۲۵۰٬۰۰۰", "١٢٥٠٠٠٠", "1 250 000"):
            self.assertEqual(field.clean(value), 1250000)
        self.assertIsNone(field.clean(""))
        self.assertEqual(field.clean("0"), 0)
        self.assertEqual(field.clean("9٬007٬199٬254٬740٬993"), 9007199254740993)
        for value in ("-1", "100.5", "12x000"):
            with self.assertRaises(ValidationError):
                field.clean(value)

    def test_widget_and_fractional_costs_are_grouped_without_losing_precision(self):
        self.assertEqual(MoneyInput().format_value(1250000), "1٬250٬000")
        self.assertEqual(MoneyInput().format_value("invalid"), "invalid")
        self.assertEqual(decimal_toman(Decimal("1234567.125")), "۱٬۲۳۴٬۵۶۷٫۱۳")
        self.assertEqual(decimal_toman(50000), "۵۰٬۰۰۰")


class AdminPriceAndIngredientsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(username="money-admin", password="test-password", email="")
        self.client.force_login(self.staff)
        self.flour = Ingredient.objects.create(name="آرد سفید", price_per_kg=50000)
        self.butter = Ingredient.objects.create(name="کره", price_per_kg=150000)

    def payload(self):
        return {
            "name": "محصول انتخاب ترکیبات", "price": "۱۰۰٬۰۰۰", "discounted_price": "",
            "profit_percent": "0", "sort_order": "0", "is_available": "on",
            "ingredient_choices": [str(self.flour.pk), str(self.butter.pk)],
            "recipe_items-TOTAL_FORMS": "0", "recipe_items-INITIAL_FORMS": "0",
            "weight_options-TOTAL_FORMS": "0", "weight_options-INITIAL_FORMS": "0",
            "photos-TOTAL_FORMS": "0", "photos-INITIAL_FORMS": "0", "_save": "ذخیره",
        }

    def test_admin_material_selection_and_blank_discount_default(self):
        initial = self.client.get(reverse("admin:bakery_product_add"))
        self.assertEqual(initial.context["adminform"].form["discounted_price"].value(), 0)
        response = self.client.post(reverse("admin:bakery_product_add"), self.payload())
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get()
        self.assertEqual(product.price, 100000)
        self.assertEqual(product.discounted_price, 0)
        self.assertEqual(product.selling_price, 100000)
        self.assertIsNone(product.price_before_discount)
        self.assertCountEqual(product.ingredient_choices.all(), [self.flour, self.butter])
        self.assertIn("آرد سفید", product.display_ingredients)
        detail = self.client.get(product.get_absolute_url())
        self.assertContains(detail, "آرد سفید")
        search = self.client.get(reverse("menu"), {"q": "آرد سفید"})
        self.assertContains(search, product.name)
        form_page = self.client.get(reverse("admin:bakery_product_change", args=[product.pk]))
        self.assertContains(form_page, 'name="ingredient_choices"')
        self.assertNotContains(form_page, 'name="ingredients"')
        self.assertContains(form_page, 'value="100٬000"')
        self.assertContains(form_page, "admin_money.js")
        self.assertFalse(form_page.context["adminform"].form.fields["discounted_price"].required)

    def test_selected_and_recipe_ingredients_are_combined_without_duplicates(self):
        product = Product.objects.create(name="دستور", price=100000, ingredients="دارچین")
        product.ingredient_choices.add(self.flour)
        RecipeIngredient.objects.create(product=product, ingredient=self.flour, quantity_grams=100)
        RecipeIngredient.objects.create(product=product, ingredient=self.butter, quantity_grams=20)
        self.assertEqual(product.display_ingredients.count("آرد سفید"), 1)
        self.assertIn("دارچین", product.display_ingredients)
        self.assertIn("کره", product.display_ingredients)
        self.flour.name = "آرد تازه"
        self.flour.save()
        product.refresh_from_db()
        self.assertIn("آرد تازه", product.display_ingredients)

    def test_explicit_selection_replaces_legacy_text_only_when_changed(self):
        product = Product.objects.create(name="قدیمی", price=100000, ingredients="ترکیبات قدیمی")
        data = self.payload()
        data["ingredient_choices"] = []
        response = self.client.post(reverse("admin:bakery_product_change", args=[product.pk]), data)
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.ingredients, "ترکیبات قدیمی")
        data["ingredient_choices"] = [str(self.flour.pk)]
        self.client.post(reverse("admin:bakery_product_change", args=[product.pk]), data)
        product.refresh_from_db()
        self.assertEqual(product.ingredients, "")
        self.assertEqual(product.display_ingredients, "آرد سفید")

    def test_discounted_price_is_used_in_cart_and_normal_price_for_zero(self):
        data = self.payload()
        data["discounted_price"] = "۸۰٬۰۰۰"
        self.assertEqual(self.client.post(reverse("admin:bakery_product_add"), data).status_code, 302)
        product = Product.objects.get()
        self.assertEqual(product.discount_percent, 20)
        self.assertEqual(product.price_before_discount, 100000)
        self.client.post(reverse("add_to_basket", args=[product.pk]))
        cart = self.client.post(reverse("update_basket", args=[str(product.pk)]), {"quantity": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(cart.json()["total"], 80000)
        product.discounted_price = 0
        product.save()
        cart = self.client.post(reverse("update_basket", args=[str(product.pk)]), {"quantity": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(cart.json()["total"], 100000)

    def test_weight_discount_blank_is_zero_and_checkout_uses_selected_sale_price(self):
        data = self.payload()
        data.update({
            "weight_options-TOTAL_FORMS": "2",
            "weight_options-0-weight": "۵۰۰ گرم", "weight_options-0-price": "80٬000", "weight_options-0-discounted_price": "", "weight_options-0-sort_order": "0", "weight_options-0-is_available": "on",
            "weight_options-1-weight": "۱ کیلوگرم", "weight_options-1-price": "150٬000", "weight_options-1-discounted_price": "60٬000", "weight_options-1-sort_order": "1", "weight_options-1-is_available": "on",
        })
        self.assertEqual(self.client.post(reverse("admin:bakery_product_add"), data).status_code, 302)
        product = Product.objects.get()
        small, large = product.weight_options.order_by("sort_order")
        self.assertEqual(small.discounted_price, 0)
        self.assertEqual(small.selling_price, 80000)
        self.assertEqual(large.selling_price, 60000)
        self.assertEqual(product.starting_price, 60000)
        self.assertEqual(product.starting_original_price, 150000)
        self.client.post(reverse("add_to_basket", args=[product.pk]), {"weight_id": large.pk})
        key = f"{product.pk}_{large.pk}"
        cart = self.client.post(reverse("update_basket", args=[key]), {"quantity": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(cart.json()["total"], 60000)
        detail = self.client.get(product.get_absolute_url())
        self.assertContains(detail, 'data-price="60000"')
        self.assertContains(detail, 'data-original-price="150000"')

    def test_manual_discount_cannot_be_equal_to_or_above_regular_price(self):
        for amount in ("100٬000", "120٬000", "-1"):
            data = self.payload()
            data["discounted_price"] = amount
            response = self.client.post(reverse("admin:bakery_product_add"), data)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["adminform"].form.errors.get("discounted_price"))
        self.assertFalse(Product.objects.exists())

    def test_automatic_pricing_updates_regular_price_and_preserves_valid_discount(self):
        product = Product.objects.create(name="خودکار", price=100000, discounted_price=20000,
                                         recipe_yield_grams=500, profit_percent=25)
        RecipeIngredient.objects.create(product=product, ingredient=self.flour, quantity_grams=400)
        product.auto_pricing = True
        product.save()
        self.assertEqual(product.price, 25000)
        self.assertEqual(product.selling_price, 20000)
        self.flour.price_per_kg = 25000
        self.flour.save()
        product.refresh_from_db()
        self.assertEqual(product.price, 12500)
        self.assertEqual(product.discounted_price, 20000)
        self.assertEqual(product.selling_price, 12500)
        self.assertIsNone(product.price_before_discount)

    def test_ingredient_changelist_accepts_grouped_prices(self):
        response = self.client.post(reverse("admin:bakery_ingredient_change", args=[self.flour.pk]),
                                    {"name": self.flour.name, "price_per_kg": "۱٬۲۵۰٬۰۰۰", "_save": "ذخیره"})
        self.assertEqual(response.status_code, 302)
        self.flour.refresh_from_db()
        self.assertEqual(self.flour.price_per_kg, 1250000)


class ExistingDiscountMigrationTests(TransactionTestCase):
    old = [("bakery", "0012_recipe_cost_pricing")]
    latest = [("bakery", "0013_ingredient_selection_and_discount_prices")]

    def tearDown(self):
        MigrationExecutor(connection).migrate(self.latest)
        super().tearDown()

    def test_legacy_sale_prices_and_order_snapshots_survive_forward_and_reverse(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.old)
        state = executor.loader.project_state(self.old).apps
        old_product = state.get_model("bakery", "Product").objects.create(name="قدیمی", price=80000, original_price=100000)
        old_weight = state.get_model("bakery", "ProductWeightOption").objects.create(product=old_product, weight="۵۰۰ گرم", price=40000, original_price=50000)
        order = state.get_model("bakery", "Order").objects.create(customer_name="مشتری", phone="09121234567", total=80000)
        state.get_model("bakery", "OrderItem").objects.create(order=order, product=old_product, product_name="قدیمی", unit_price=80000, quantity=1)
        MigrationExecutor(connection).migrate(self.latest)
        migrated_state = executor.loader.project_state(self.latest).apps
        product = migrated_state.get_model("bakery", "Product").objects.get(pk=old_product.pk)
        weight = migrated_state.get_model("bakery", "ProductWeightOption").objects.get(pk=old_weight.pk)
        self.assertEqual((product.price, product.discounted_price), (100000, 80000))
        self.assertEqual((weight.price, weight.discounted_price), (50000, 40000))
        self.assertEqual(product.orderitem_set.get().unit_price, 80000)
        MigrationExecutor(connection).migrate(self.old)
        restored = state.get_model("bakery", "Product").objects.get(pk=old_product.pk)
        self.assertEqual((restored.price, restored.original_price), (80000, 100000))
