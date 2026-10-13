from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse

from .models import ContactMessage, CustomerProfile, DietaryTag, LoginCode, Order, Product, ProductCategory
from .sms import SMSDeliveryError, send_login_code
from .zarinpal import Zarinpal


class BakeryFlowTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="نان کره‌ای", short_description="پخت تازه",
            price=85000, is_available=True,
        )
        self.assertTrue(self.product.slug.startswith("pastry-"))

    def test_menu_accessibility_and_catalog_fallback(self):
        response = self.client.get(reverse("menu"), {"q": "نان"})
        self.assertContains(response, 'role="dialog" aria-modal="true"')
        self.assertContains(response, 'aria-label="جست‌وجو در منو"')
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, 'viewport-fit=cover')
        self.assertContains(response, 'aria-controls="mobile-nav-drawer"')

    def test_product_gallery_supports_multiple_images(self):
        from .models import ProductImage
        self.product.image = "products/main.webp"
        self.product.save()
        for index in range(5):
            ProductImage.objects.create(product=self.product, image=f"products/detail-{index}.webp", alt_text="نمای شیرینی", sort_order=index)
        self.assertEqual(len(self.product.gallery_images), 6)
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, "data-product-gallery")
        self.assertContains(response, "نمای شیرینی")

    def test_dashboard_chart_has_individual_hit_targets(self):
        from .templatetags.bakery_tags import render_dashboard_chart
        chart = render_dashboard_chart([{"label": str(i), "amount": i} for i in range(30)])
        self.assertEqual(len(chart["bars"]), 30)
        self.assertAlmostEqual(chart["bars"][0]["slot"], chart["plotW"] / 30, places=1)
        self.assertEqual(chart["bars"][1]["full_label"], "1")
        self.assertTrue(chart["line_path"].startswith("M "))

    def test_dashboard_sales_periods(self):
        from django.test import RequestFactory
        from .dashboard import dashboard_context
        factory = RequestFactory()
        for period, count in (("daily", 24), ("weekly", 7), ("monthly", 30)):
            context = dashboard_context(factory.get("/dashboard/", {"period": period}))
            self.assertEqual(context["period"], period)
            self.assertEqual(len(context["bars"]), count)
            self.assertEqual(context["period_sales"], sum(bar["amount"] for bar in context["bars"] if bar["amount"] is not None))
        self.assertEqual(dashboard_context(factory.get("/dashboard/", {"period": "bad"}))["period"], "weekly")

    def test_login_phone_label_matches_input(self):
        response = self.client.get(reverse("phone_login"))
        self.assertContains(response, 'for="auth-phone"')

    def test_home_has_ordering_and_fulfillment_guidance(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="home-page"')
        self.assertContains(response, "روش تحویل و زمان آماده‌سازی")

    def test_pagination_neighbors_and_ellipsis(self):
        from .templatetags.bakery_tags import pagination_items
        self.assertEqual(pagination_items(6, 12), [1, None, 5, 6, 7, None, 12])
        self.assertEqual(pagination_items(1, 3), [1, 2, 3])

    def test_profile_history_is_paginated(self):
        user = get_user_model().objects.create_user(username="profile-pagination")
        CustomerProfile.objects.create(user=user, phone="09121234567", display_name="مریم")
        self.client.force_login(user)
        for i in range(21):
            Order.objects.create(customer=user, customer_name="مریم", phone="09121234567", total=1000)
        response = self.client.get(reverse("customer_profile"))
        self.assertEqual(response.context["order_count"], 21)
        self.assertEqual(len(response.context["orders"]), 10)
        self.assertContains(response, 'rel="next"')

    def test_ajax_basket_update_and_remove(self):
        self.client.post(reverse("add_to_basket", args=[self.product.id]))
        response = self.client.post(reverse("update_basket", args=[self.product.id]),
                                    {"quantity": "۳"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cart_count"], 3)
        self.assertEqual(response.json()["total"], 255000)
        response = self.client.post(reverse("remove_from_basket", args=[self.product.id]),
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json()["cart_count"], 0)

    def test_ajax_basket_rejects_invalid_quantity(self):
        response = self.client.post(reverse("update_basket", args=[self.product.id]),
                                    {"quantity": "oops"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)

    def test_ajax_add_returns_count_without_redirect(self):
        response = self.client.post(reverse("add_to_basket", args=[self.product.id]),
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cart_count"], 1)
        self.assertEqual(self.client.session["cart"][str(self.product.id)], 1)
        response = self.client.post(reverse("add_to_basket", args=[self.product.id]),
                                    HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.json()["cart_count"], 2)

    def test_catalog_srcset_missing_variants_falls_back(self):
        from .templatetags.bakery_tags import catalog_srcset
        self.assertEqual(catalog_srcset(None), "")

    def test_contact_form_saves_message_and_shows_success_state(self):
        response = self.client.post(reverse("contact"), {
            "name": "مریم رضایی",
            "phone": "۰۹۱۲۱۲۳۴۵۶۷",
            "subject": "سفارش فردا",
            "message": "برای فردا کروسان دارید؟",
        })
        message = ContactMessage.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(message.phone, "09121234567")
        self.assertContains(self.client.get(response.url), "پیامتان رسید")

    def test_contact_form_requires_a_valid_phone(self):
        response = self.client.post(reverse("contact"), {
            "name": "مریم رضایی", "phone": "۱۲۳", "subject": "پرسش", "message": "سلام",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactMessage.objects.exists())
        self.assertContains(response, "شمارهٔ همراه را بررسی کنید")

    def test_home_and_menu_render_empty_or_available_catalog(self):
        home_response = self.client.get(reverse("home"))
        self.assertContains(home_response, "نان کره‌ای")
        self.assertContains(home_response, "bakery/tart-sample.webp")
        self.assertContains(self.client.get(reverse("menu")), "نان کره‌ای")
        self.assertContains(self.client.get(reverse("menu")), "۸۵٬۰۰۰")

    def test_empty_menu_has_a_composed_state(self):
        self.product.delete()
        self.assertContains(self.client.get(reverse("menu")), "منوی امروز هنوز آماده نشده")

    def test_about_page_and_shared_mobile_navigation_render(self):
        response = self.client.get(reverse("about"))
        self.assertContains(response, "دربارهٔ ما")
        self.assertContains(response, "ما به عطرِ")
        self.assertContains(response, 'aria-controls="mobile-nav-drawer"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, reverse("contact"))

    def test_menu_filters_by_category_and_diet(self):
        bread = ProductCategory.objects.create(name="نان‌ها")
        sweets = ProductCategory.objects.create(name="شیرینی‌ها")
        plant_based = DietaryTag.objects.create(name="گیاهی")
        self.product.category = bread
        self.product.save()
        self.product.dietary_tags.add(plant_based)
        other = Product.objects.create(name="کیک روز", price=120000, category=sweets)

        response = self.client.get(reverse("menu"), {"category": bread.slug, "diet": plant_based.slug})
        self.assertContains(response, "نان کره‌ای")
        self.assertNotContains(response, "کیک روز")
        self.assertContains(response, "گیاهی")
        self.assertContains(response, "نان‌ها")

        all_products = self.client.get(reverse("menu"))
        self.assertContains(all_products, "کیک روز")
        self.assertContains(all_products, "شیرینی‌ها")

    def test_menu_filters_by_flavor(self):
        self.product.flavor = "وانیلی، کره‌ای"
        self.product.save()
        choc = Product.objects.create(name="کوکی شکلات", price=95000, flavor="شکلاتی")
        response = self.client.get(reverse("menu"), {"flavor": "شکلاتی"})
        self.assertContains(response, "کوکی شکلات")
        self.assertNotContains(response, "نان کره‌ای")
        self.assertContains(response, "طعم‌ها")
        all_menu = self.client.get(reverse("menu"))
        self.assertContains(all_menu, "وانیلی")
        self.assertContains(all_menu, "شکلاتی")

    def test_product_card_is_clickable_with_data_href(self):
        response = self.client.get(reverse("menu"))
        self.assertContains(response, f'data-href="{self.product.get_absolute_url()}"')
        self.assertContains(response, 'class="product-title-link"')

    def test_menu_partial_filters_return_only_results(self):
        bread = ProductCategory.objects.create(name="نان‌ها")
        sweets = ProductCategory.objects.create(name="شیرینی‌ها")
        self.product.category = bread
        self.product.save()
        Product.objects.create(name="کیک روز", price=120000, category=sweets)
        response = self.client.get(
            reverse("menu"), {"category": bread.slug},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="menu-results"')
        self.assertContains(response, "نان کره‌ای")
        self.assertNotContains(response, "کیک روز")
        self.assertNotContains(response, 'id="menu-filters-form"')
        empty = self.client.get(
            reverse("menu"), {"category": bread.slug, "q": "ناموجود"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertContains(empty, "با این انتخاب چیزی")
        self.assertContains(empty, 'id="menu-results"')

    def test_menu_search_normalizes_zwnj(self):
        Product.objects.create(name="چیز‌کیک کلاسیک", price=95000, is_available=True)
        # Search without ZWNJ
        res1 = self.client.get(reverse("menu"), {"q": "چیزکیک"})
        self.assertContains(res1, "چیز‌کیک کلاسیک")
        # Search with space
        res2 = self.client.get(reverse("menu"), {"q": "چیز کیک"})
        self.assertContains(res2, "چیز‌کیک کلاسیک")
        # Search with ZWNJ
        res3 = self.client.get(reverse("menu"), {"q": "چیز‌کیک"})
        self.assertContains(res3, "چیز‌کیک کلاسیک")

    def test_unavailable_products_cannot_be_added(self):
        self.product.is_available = False
        self.product.save()
        response = self.client.post(reverse("add_to_basket", args=[self.product.id]))
        self.assertEqual(response.status_code, 404)

    @override_settings(ZARINPAL_MERCHANT_ID="test-merchant", ZARINPAL_SANDBOX=True)
    @patch("bakery.views.Zarinpal.request_payment", return_value="A00000000000000000000000000000000000")
    def test_checkout_creates_snapshot_and_redirects_to_gateway(self, request_payment):
        session = self.client.session
        session["cart"] = {str(self.product.id): 2}
        session.save()
        response = self.client.post(reverse("checkout"), {
            "customer_name": "مریم",
            "phone": "۰۹۱۲۱۲۳۴۵۶۷",
            "fulfillment": "delivery",
            "address": "تهران، خیابان نمونه",
            "note": "",
        })
        order = Order.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith(order.authority))
        self.assertEqual(order.total, 170000)
        self.assertEqual(order.phone, "09121234567")
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(order.items.get().unit_price, 85000)
        self.assertEqual(self.client.session["cart"], {})
        request_payment.assert_called_once()

    @override_settings(ZARINPAL_MERCHANT_ID="test-merchant", ZARINPAL_SANDBOX=True)
    @patch("bakery.views.Zarinpal.verify_payment", return_value="123456789")
    def test_success_callback_marks_order_paid_after_verification(self, verify_payment):
        order = Order.objects.create(
            customer_name="مریم", phone="09121234567", total=85000,
            authority="authority-1", payment_status=Order.PaymentStatus.INITIATED,
        )
        response = self.client.get(reverse("payment_return"), {
            "order": order.number, "Authority": order.authority, "Status": "OK",
        })
        order.refresh_from_db()
        self.assertRedirects(response, reverse("order_status", args=[order.number]), fetch_redirect_response=False)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.ref_id, "123456789")
        verify_payment.assert_called_once_with(order)

    @patch("bakery.views.Zarinpal.verify_payment")
    def test_cancelled_payment_stays_unpaid(self, verify_payment):
        order = Order.objects.create(
            customer_name="مریم", phone="09121234567", total=85000,
            authority="authority-2", payment_status=Order.PaymentStatus.INITIATED,
        )
        response = self.client.get(reverse("payment_return"), {
            "order": order.number, "Authority": order.authority, "Status": "NOK",
        })
        order.refresh_from_db()
        self.assertRedirects(response, reverse("order_status", args=[order.number]), fetch_redirect_response=False)
        self.assertEqual(order.payment_status, Order.PaymentStatus.FAILED)
        verify_payment.assert_not_called()

    def test_callback_rejects_mismatched_authority(self):
        order = Order.objects.create(customer_name="مریم", phone="09121234567", total=85000, authority="expected")
        response = self.client.get(reverse("payment_return"), {
            "order": order.number, "Authority": "attacker", "Status": "OK",
        })
        self.assertEqual(response.status_code, 400)

    def test_callback_rejects_malformed_order_uuid(self):
        response = self.client.get(reverse("payment_return"), {
            "order": "not-a-uuid", "Authority": "authority", "Status": "OK",
        })
        self.assertEqual(response.status_code, 400)

    def test_retry_payment_is_available_after_failure(self):
        order = Order.objects.create(
            customer_name="مریم", phone="09121234567", total=85000,
            payment_status=Order.PaymentStatus.FAILED,
        )
        response = self.client.get(reverse("order_status", args=[order.number]))
        self.assertContains(response, "تلاش دوباره برای پرداخت")

    @override_settings(ZARINPAL_MERCHANT_ID="test-merchant", ZARINPAL_SANDBOX=True)
    @patch("bakery.views.Zarinpal.request_payment", return_value="new-authority")
    def test_failed_order_can_start_a_new_payment(self, request_payment):
        order = Order.objects.create(
            customer_name="مریم", phone="09121234567", total=85000,
            payment_status=Order.PaymentStatus.FAILED,
        )
        response = self.client.post(reverse("retry_payment", args=[order.number]))
        order.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(order.authority, "new-authority")
        self.assertEqual(order.payment_status, Order.PaymentStatus.INITIATED)
        request_payment.assert_called_once()


class ZarinpalClientTests(TestCase):
    @override_settings(ZARINPAL_MERCHANT_ID="merchant-test", ZARINPAL_SANDBOX=True)
    @patch("bakery.zarinpal.requests.post")
    def test_request_uses_rials_and_sandbox_endpoint(self, post):
        response = Mock()
        response.json.return_value = {"data": {"code": 100, "authority": "authority-test"}}
        post.return_value = response
        order = Order(total=85000, phone="09120000000", number="00000000-0000-0000-0000-000000000000")
        authority = Zarinpal.request_payment(order, "https://shop.test/payment/return/")
        self.assertEqual(authority, "authority-test")
        self.assertEqual(post.call_args.kwargs["json"]["amount"], 850000)
        self.assertIn("sandbox.zarinpal.com", post.call_args.args[0])


class PhoneLoginTests(TestCase):
    phone = "09121234567"

    @override_settings(DEBUG=True, OTP_SMS_BACKEND="console")
    @patch("bakery.views.send_login_code")
    def test_local_otp_is_123456_and_six_slot_ui_renders(self, send_code):
        response = self.client.post(reverse("phone_login"), {"action": "send", "phone": self.phone})
        self.assertEqual(response.status_code, 200)
        send_code.assert_called_once_with(self.phone, "123456")
        self.assertContains(response, "۱۲۳۴۵۶")
        self.assertContains(response, "bakery/otp.js")
        self.assertContains(response, 'dir="ltr" role="group"')
        self.assertEqual(response.content.decode().count('data-otp-slot'), 6)
        self.assertContains(response, 'name="code"')  # Single field remains usable without JavaScript.
        verified = self.client.post(reverse("phone_login"), {"action": "verify", "code": "۱۲۳۴۵۶"})
        self.assertRedirects(verified, reverse("customer_profile"), fetch_redirect_response=False)

    @override_settings(DEBUG=False, OTP_SMS_BACKEND="kavenegar")
    @patch("bakery.views.secrets.randbelow", return_value=654320)
    @patch("bakery.views.send_login_code")
    def test_live_sms_backend_uses_random_code_not_development_code(self, send_code, random_number):
        response = self.client.post(reverse("phone_login"), {"action": "send", "phone": self.phone})
        self.assertEqual(response.status_code, 200)
        send_code.assert_called_once_with(self.phone, "654320")
        random_number.assert_called_once_with(1_000_000)
        self.assertNotContains(response, "برای آزمایش محلی")
        wrong = self.client.post(reverse("phone_login"), {"action": "verify", "code": "123456"})
        self.assertContains(wrong, "کد واردشده درست نیست")
        verified = self.client.post(reverse("phone_login"), {"action": "verify", "code": "654320"})
        self.assertRedirects(verified, reverse("customer_profile"), fetch_redirect_response=False)

    @override_settings(DEBUG=False, OTP_SMS_BACKEND="console")
    def test_console_otp_cannot_log_in_when_debug_is_disabled(self):
        response = self.client.post(reverse("phone_login"), {"action": "send", "phone": self.phone})
        self.assertContains(response, "ارسال پیامک در محیط واقعی پیکربندی نشده است")
        self.assertNotContains(response, "برای آزمایش محلی")
        self.assertIsNone(self.client.session.get("phone_login_challenge"))

    def test_anonymous_profile_opens_phone_login(self):
        response = self.client.get(reverse("customer_profile"))
        self.assertRedirects(
            response,
            f"{reverse('phone_login')}?next={reverse('customer_profile')}",
            fetch_redirect_response=False,
        )

    def test_profile_shortcut_points_to_account_profile(self):
        for url in ("/profile", "/profile/"):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse("customer_profile"), fetch_redirect_response=False)

    def test_staff_without_customer_profile_can_open_account(self):
        staff = get_user_model().objects.create_user(username="bakery-admin", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse("customer_profile"))
        self.assertContains(response, "حساب مدیریت")
        self.assertContains(response, reverse("shop_dashboard"))
        self.assertContains(response, reverse("admin:bakery_product_changelist"))
        self.assertNotContains(response, "شمارهٔ همراه تأییدشدهٔ شما")
        self.assertRedirects(self.client.get(reverse("phone_login")), reverse("customer_profile"), fetch_redirect_response=False)

    def test_unverified_legacy_account_gets_help_instead_of_home_redirect(self):
        user = get_user_model().objects.create_user(username="old-account")
        self.client.force_login(user)
        response = self.client.get(reverse("customer_profile"))
        self.assertContains(response, "شمارهٔ همراه را تأیید کنید")
        self.assertContains(response, "خروج از حساب")

    @patch("bakery.views.send_login_code")
    def test_login_creates_customer_only_after_valid_sms_code(self, send_code):
        issued = {}
        send_code.side_effect = lambda phone, code: issued.update(phone=phone, code=code)
        response = self.client.post(reverse("phone_login"), {
            "action": "send", "phone": "+98 912 123 4567", "next": reverse("menu"),
        })
        challenge = LoginCode.objects.get()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کد را")
        self.assertEqual(issued["phone"], self.phone)
        self.assertNotEqual(challenge.code_digest, issued["code"])
        self.assertFalse(get_user_model().objects.exists())

        wrong_code = "999999" if issued["code"] == "000000" else "000000"
        response = self.client.post(reverse("phone_login"), {"action": "verify", "code": wrong_code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کد واردشده درست نیست")
        self.assertFalse(get_user_model().objects.exists())

        response = self.client.post(reverse("phone_login"), {"action": "verify", "code": issued["code"]})
        user = get_user_model().objects.get(username=self.phone)
        challenge.refresh_from_db()
        self.assertRedirects(response, reverse("menu"), fetch_redirect_response=False)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.customer_profile.phone, self.phone)
        self.assertIsNotNone(challenge.used_at)

    @patch("bakery.views.send_login_code")
    def test_phone_login_rejects_invalid_numbers_and_limits_resends(self, send_code):
        invalid = self.client.post(reverse("phone_login"), {"action": "send", "phone": "123"})
        self.assertContains(invalid, "یک شمارهٔ همراه معتبر وارد کنید")
        send_code.assert_not_called()

        send_code.return_value = None
        data = {"action": "send", "phone": "۰۹۱۲۱۲۳۴۵۶۷"}
        self.client.post(reverse("phone_login"), data)
        blocked = self.client.post(reverse("phone_login"), {**data, "action": "resend"})
        self.assertContains(blocked, "یک دقیقه دیگر")
        self.assertEqual(LoginCode.objects.count(), 1)
        send_code.assert_called_once()

    @patch("bakery.views.send_login_code", side_effect=SMSDeliveryError("ارسال پیامک انجام نشد."))
    def test_sms_failure_does_not_start_a_login_session(self, send_code):
        response = self.client.post(reverse("phone_login"), {"action": "send", "phone": self.phone})
        challenge = LoginCode.objects.get()
        self.assertContains(response, "ارسال پیامک انجام نشد")
        self.assertIsNone(self.client.session.get("phone_login_challenge"))
        self.assertIsNotNone(challenge.used_at)
        send_code.assert_called_once()

    @patch("bakery.views.send_login_code")
    def test_otp_expires_and_cannot_be_replayed(self, send_code):
        issued = {}
        send_code.side_effect = lambda phone, code: issued.update(code=code)
        self.client.post(reverse("phone_login"), {"action": "send", "phone": self.phone})
        challenge = LoginCode.objects.get()
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=["expires_at"])
        expired = self.client.post(reverse("phone_login"), {"action": "verify", "code": issued["code"]})
        self.assertRedirects(expired, reverse("phone_login"), fetch_redirect_response=False)
        self.assertFalse(get_user_model().objects.exists())

    def test_profile_shows_orders_edits_name_and_logout_requires_post(self):
        user = get_user_model().objects.create_user(username=self.phone)
        profile = CustomerProfile.objects.create(user=user, phone=self.phone)
        order = Order.objects.create(customer=user, customer_name="مریم", phone=self.phone, total=85000)
        self.client.force_login(user)
        response = self.client.get(reverse("customer_profile"))
        self.assertContains(response, str(order.number)[:8])
        self.assertContains(response, "۸۵٬۰۰۰ تومان")

        response = self.client.post(reverse("customer_profile"), {"display_name": "مریم رضایی"})
        profile.refresh_from_db()
        self.assertRedirects(response, reverse("customer_profile"), fetch_redirect_response=False)
        self.assertEqual(profile.display_name, "مریم رضایی")
        self.assertEqual(self.client.get(reverse("phone_logout")).status_code, 405)
        self.client.post(reverse("phone_logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    @patch("bakery.views.send_login_code")
    def test_unsafe_return_url_is_replaced_by_profile(self, send_code):
        send_code.return_value = None
        response = self.client.post(reverse("phone_login"), {
            "action": "send", "phone": self.phone, "next": "https://elsewhere.invalid/steal",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["phone_login_next"], reverse("customer_profile"))

    @patch("bakery.views.send_login_code")
    def test_phone_otp_cannot_authenticate_staff_accounts(self, send_code):
        staff = get_user_model().objects.create_user(username=self.phone, is_staff=True)
        issued = {}
        send_code.side_effect = lambda phone, code: issued.update(code=code)
        self.client.post(reverse("phone_login"), {"action": "send", "phone": self.phone})
        response = self.client.post(reverse("phone_login"), {"action": "verify", "code": issued["code"]})
        self.assertRedirects(response, reverse("phone_login"), fetch_redirect_response=False)
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertTrue(staff.is_staff)


class SMSDeliveryTests(TestCase):
    @override_settings(
        OTP_SMS_BACKEND="kavenegar",
        KAVENEGAR_API_KEY="test-api-key",
        KAVENEGAR_VERIFY_TEMPLATE="tastytum_login",
    )
    @patch("bakery.sms.requests.post")
    def test_kavenegar_lookup_sends_phone_code_using_approved_template(self, post):
        response = Mock()
        response.json.return_value = {"return": {"status": 200}}
        post.return_value = response
        send_login_code("09121234567", "042861")
        self.assertIn("test-api-key/verify/lookup.json", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["data"], {
            "receptor": "09121234567", "token": "042861", "template": "tastytum_login",
        })


class ShopDashboardTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(username="bakery-owner", email="", password="not-used-here")

    def test_dashboard_requires_staff_login(self):
        url = reverse("shop_dashboard")
        anonymous = self.client.get(url)
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/admin/login/", anonymous["Location"])

        customer = get_user_model().objects.create_user(username="09120000000")
        self.client.force_login(customer)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard_export_orders")).status_code, 302)

    def test_django_admin_home_shares_live_dashboard_and_keeps_model_editing(self):
        self.client.force_login(self.staff)
        order = Order.objects.create(customer_name="سارا", phone="09121234567", total=185000,
                                     status=Order.Status.PAID, payment_status=Order.PaymentStatus.PAID,
                                     paid_at=timezone.now())

        for url in (reverse("admin:index"), reverse("shop_dashboard")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "bakery/dashboard.html")
                self.assertEqual(response.context["sales_today"], 185000)
                self.assertContains(response, "۱۸۵٬۰۰۰")
                self.assertContains(response, reverse("admin:bakery_order_change", args=[order.pk]))
                self.assertContains(response, reverse("admin:bakery_product_changelist"))

        product_form = self.client.get(reverse("admin:bakery_product_add"))
        self.assertEqual(product_form.status_code, 200)
        self.assertContains(product_form, "bakery/admin.css")

    def test_admin_home_requires_staff_authentication(self):
        anonymous = self.client.get(reverse("admin:index"))
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/admin/login/", anonymous["Location"])
        customer = get_user_model().objects.create_user(username="09120000000")
        self.client.force_login(customer)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_dashboard_uses_paid_orders_and_real_customer_counts(self):
        self.client.force_login(self.staff)
        first = Order.objects.create(customer_name="مریم", phone="09121234567", total=100000,
                                     status=Order.Status.PAID, payment_status=Order.PaymentStatus.PAID,
                                     paid_at=timezone.now())
        Order.objects.create(customer_name="علی", phone="09120000001", total=50000,
                             status=Order.Status.PREPARING, payment_status=Order.PaymentStatus.PAID,
                             paid_at=timezone.now())
        Order.objects.create(customer_name="نگار", phone="09120000002", total=900000,
                             status=Order.Status.PENDING, payment_status=Order.PaymentStatus.UNPAID)
        Order.objects.create(customer_name="رضا", phone="09120000003", total=800000,
                             status=Order.Status.CANCELLED, payment_status=Order.PaymentStatus.FAILED)
        user = get_user_model().objects.create_user(username="09121234567")
        CustomerProfile.objects.create(user=user, phone="09121234567")

        response = self.client.get(reverse("shop_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sales_today"], 150000)
        self.assertEqual(response.context["average_basket"], 75000)
        self.assertEqual(response.context["weekly_sales"], 150000)
        self.assertEqual(response.context["open_orders"], 3)
        self.assertEqual(response.context["new_customers"], 1)
        self.assertEqual(len(response.context["bars"]), 7)
        self.assertContains(response, "۱۵۰٬۰۰۰")
        self.assertContains(response, reverse("admin:bakery_order_change", args=[first.pk]))
        self.assertContains(response, reverse("admin:bakery_product_add"))

    def test_dashboard_search_and_filtered_csv_export(self):
        self.client.force_login(self.staff)
        target = Order.objects.create(customer_name="=مریم", phone="09121234567", total=32000)
        Order.objects.create(customer_name="علی", phone="09120000001", total=90000)

        response = self.client.get(reverse("shop_dashboard"), {"q": "09121234567"})
        self.assertContains(response, "=مریم")
        self.assertNotContains(response, "علی")
        self.assertEqual(response.context["orders"].count(), 1)

        prefix = str(target.number)[:8]
        number_search = self.client.get(reverse("shop_dashboard"), {"q": prefix})
        self.assertContains(number_search, "=مریم")
        self.assertNotContains(number_search, "علی")

        csv_response = self.client.get(reverse("dashboard_export_orders"), {"q": "09121234567"})
        body = csv_response.content.decode("utf-8-sig")
        self.assertIn("'=مریم", body)
        self.assertIn("32000", body)
        self.assertNotIn("علی", body)

    def test_empty_dashboard_has_empty_order_state(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("shop_dashboard"))
        self.assertContains(response, "هنوز سفارشی ثبت نشده است.")
        self.assertEqual(response.context["weekly_sales"], 0)


class ProductWeightAndFlavorTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(username="admin-weights", email="", password="test-password")
        self.product = Product.objects.create(
            name="شیرینی دارچینی",
            price=90000,
            flavor="دارچینی، شکری",
            is_available=True,
        )

    def test_flavor_admin_widget_and_weight_option_inline(self):
        self.client.force_login(self.staff)
        url = reverse("admin:bakery_product_change", args=[self.product.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-flavor-tags-root")
        self.assertContains(response, "flavor_tags.js")
        self.assertContains(response, "flavor_tags.css")
        self.assertContains(response, "گزینه‌های وزن و قیمت")

    def test_weighted_detail_has_discount_placeholder_and_package_context(self):
        from .models import ProductWeightOption

        self.product.short_description = "شیرینی دارچینی با بافت ترد"
        self.product.ingredients = "آرد، کره، دارچین"
        self.product.save()
        ProductWeightOption.objects.create(product=self.product, weight="250 گرم", price=95000, sort_order=0)
        ProductWeightOption.objects.create(product=self.product, weight="500 گرم", price=180000, original_price=195000, sort_order=1)
        ProductWeightOption.objects.create(product=self.product, weight="ناموجود", price=50000, is_available=False)

        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, "قیمت یک بسته · ۲۵۰ گرم")
        self.assertContains(response, '<span class="price-discount-row" hidden>')
        self.assertContains(response, '<details class="detail-more">')
        self.assertNotContains(response, "پختِ امروز")
        self.assertNotContains(response, "ناموجود")

    def test_unweighted_detail_uses_base_price_without_weight_prompt(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, "قیمت محصول")
        self.assertContains(response, "۹۰٬۰۰۰")
        self.assertNotContains(response, "data-weight-selector")
        self.assertNotContains(response, "price-discount-row")

    def test_basket_and_checkout_with_weight_options(self):
        from .models import ProductWeightOption
        opt_500 = ProductWeightOption.objects.create(
            product=self.product,
            weight="۵۰۰ گرم",
            price=160000,
            is_available=True,
            sort_order=1,
        )
        opt_1kg = ProductWeightOption.objects.create(
            product=self.product,
            weight="۱ کیلوگرم",
            price=300000,
            is_available=True,
            sort_order=2,
        )

        detail_resp = self.client.get(self.product.get_absolute_url())
        self.assertContains(detail_resp, "data-weight-selector")
        self.assertContains(detail_resp, "۵۰۰ گرم")
        self.assertContains(detail_resp, "۱ کیلوگرم")

        # 1. Add 500g option
        add_500 = self.client.post(reverse("add_to_basket", args=[self.product.id]), {"weight_id": opt_500.id})
        self.assertEqual(add_500.status_code, 302)
        key_500 = f"{self.product.id}_{opt_500.id}"
        self.assertEqual(self.client.session["cart"][key_500], 1)

        # 2. Add 1kg option
        add_1kg = self.client.post(reverse("add_to_basket", args=[self.product.id]), {"weight_id": opt_1kg.id})
        self.assertEqual(add_1kg.status_code, 302)
        key_1kg = f"{self.product.id}_{opt_1kg.id}"
        self.assertEqual(self.client.session["cart"][key_1kg], 1)

        # 3. Check Basket view
        basket_resp = self.client.get(reverse("basket"))
        self.assertContains(basket_resp, "۵۰۰ گرم")
        self.assertContains(basket_resp, "۱ کیلوگرم")
        self.assertContains(basket_resp, "۴۶۰٬۰۰۰")  # 160000 + 300000

        # 4. Update quantity of 500g option
        upd_resp = self.client.post(reverse("update_basket", args=[key_500]), {"quantity": 2})
        self.assertEqual(upd_resp.status_code, 302)
        self.assertEqual(self.client.session["cart"][key_500], 2)

        # Total is now 2 * 160000 + 300000 = 620000
        basket_upd_resp = self.client.get(reverse("basket"))
        self.assertContains(basket_upd_resp, "۶۲۰٬۰۰۰")

        # 5. Checkout
        checkout_resp = self.client.post(reverse("checkout"), {
            "customer_name": "سارا تهرانی",
            "phone": "۰۹۱۲۳۴۵۶۷۸۹",
            "fulfillment": "delivery",
            "address": "خیابان فرشته",
            "note": "",
        })
        self.assertEqual(checkout_resp.status_code, 302)
        order = Order.objects.latest("created_at")
        self.assertEqual(order.total, 620000)
        items = list(order.items.order_by("unit_price"))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].weight_label, "۵۰۰ گرم")
        self.assertEqual(items[0].unit_price, 160000)
        self.assertEqual(items[0].quantity, 2)
        self.assertEqual(items[1].weight_label, "۱ کیلوگرم")
        self.assertEqual(items[1].unit_price, 300000)
        self.assertEqual(items[1].quantity, 1)

        # 6. Remove item from basket
        rem_resp = self.client.post(reverse("remove_from_basket", args=[key_1kg]))
        self.assertEqual(rem_resp.status_code, 302)
        self.assertNotIn(key_1kg, self.client.session.get("cart", {}))


class PriceComponentTests(TestCase):
    def test_render_price_with_discount_and_structure(self):
        from django.template import Context, Template

        template = Template("{% load bakery_tags %}{% render_price amount=80000 original=100000 size='md' %}")
        rendered = template.render(Context({}))

        self.assertIn("price-container price-md", rendered)
        self.assertIn("۸۰٬۰۰۰", rendered)
        self.assertIn("تومان", rendered)
        # Verify original struck-through price precedes discount badge
        orig_idx = rendered.index("۱۰۰٬۰۰۰")
        badge_idx = rendered.index("۲۰٪ تخفیف")
        self.assertLess(orig_idx, badge_idx)
        self.assertIn("price-original", rendered)
        self.assertIn("price-badge", rendered)

    def test_render_price_without_discount(self):
        from django.template import Context, Template

        template = Template("{% load bakery_tags %}{% render_price amount=50000 size='sm' %}")
        rendered = template.render(Context({}))

        self.assertIn("price-container price-sm", rendered)
        self.assertIn("۵۰٬۰۰۰", rendered)
        self.assertNotIn("price-discount-row", rendered)
        self.assertNotIn("تخفیف", rendered)

    def test_dynamic_price_keeps_hidden_discount_row_for_later_selection(self):
        from django.template import Context, Template

        rendered = Template("{% load bakery_tags %}{% render_price amount=95000 dynamic=True %}").render(Context({}))
        self.assertIn('<span class="price-discount-row" hidden>', rendered)
        self.assertIn('<span class="price-original"></span>', rendered)
        self.assertIn('<span class="price-badge"></span>', rendered)

    def test_discount_percentage_rounds_half_up_like_browser(self):
        from .templatetags.bakery_tags import render_price

        self.assertEqual(render_price(755, 1000)["off"], 25)
        self.assertEqual(render_price(1000, 1000)["off"], 0)


class MenuSearchTests(TestCase):
    def setUp(self):
        self.cat1 = ProductCategory.objects.create(name="شیرینی تر", slug="wet-pastry")
        self.cat2 = ProductCategory.objects.create(name="کوکی", slug="cookies")
        self.p1 = Product.objects.create(
            name="کوکی ردولوت",
            slug="red-velvet-cookie",
            category=self.cat2,
            price=120000,
            original_price=140000,
            short_description="۵۰ گرم کوکی ردولوت شکلات سفید",
            flavor="شکلات سفید",
            is_available=True,
        )
        self.p2 = Product.objects.create(
            name="رولت خامه‌ای",
            slug="cream-roll",
            category=self.cat1,
            price=95000,
            short_description="رولت لطیف و تازه",
            flavor="وانیلی",
            is_available=True,
        )

    def test_menu_search_redirects_to_canonical_menu(self):
        response = self.client.get(reverse("menu_search"))
        self.assertRedirects(response, reverse("menu"))

        response_with_q = self.client.get(reverse("menu_search") + "?q=ردولوت")
        self.assertEqual(response_with_q.status_code, 302)
        self.assertTrue(response_with_q.url.startswith(reverse("menu") + "?q="))

    def test_menu_search_filter_query(self):
        response = self.client.get(reverse("menu") + "?q=ردولوت")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["products"]), [self.p1])
        self.assertContains(response, "کوکی ردولوت")
        self.assertNotContains(response, "رولت خامه‌ای")

    def test_menu_search_empty_result(self):
        response = self.client.get(reverse("menu") + "?q=ناموجود123")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "محصولی پیدا نشد")
        self.assertContains(response, "عبارت دیگری را امتحان کنید")
        self.assertContains(response, "مشاهده همهٔ شیرینی‌ها")

    def test_menu_has_no_popular_search_suggestions(self):
        response = self.client.get(reverse("menu"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "query-chip")
        self.assertNotContains(response, "پرطرفدار")

    def test_menu_search_ajax_results(self):
        response = self.client.get(
            reverse("menu") + "?q=ردولوت",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bakery/_menu_results.html")
        self.assertContains(response, "کوکی ردولوت")
        self.assertNotContains(response, "رولت خامه‌ای")
