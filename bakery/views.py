import hmac
import secrets
import uuid
from math import ceil
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import salted_hmac
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Q, TextField, Value
from django.db.models.functions import Replace

from .forms import CheckoutForm, ContactForm, CustomerProfileForm, LoginCodeForm, PhoneRequestForm, ProductReviewForm
from .models import ContactMessage, CustomerProfile, DietaryTag, HeroSlide, LoginCode, Order, OrderItem, Product, ProductCategory, ProductReview
from .sms import SMSDeliveryError, send_login_code
from .zarinpal import Zarinpal, ZarinpalError


def _parse_cart_key(key):
    s = str(key)
    if "_" in s:
        parts = s.split("_", 1)
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None, None
    try:
        return int(s), None
    except ValueError:
        return None, None


def _cart_products(request):
    cart = request.session.get("cart", {})
    if not cart:
        return [], 0

    parsed_entries = []
    product_ids = set()
    for raw_key, raw_qty in cart.items():
        pid, wid = _parse_cart_key(raw_key)
        if pid is not None:
            product_ids.add(pid)
            try:
                qty = min(max(int(raw_qty), 1), 99)
            except (ValueError, TypeError):
                qty = 1
            parsed_entries.append((str(raw_key), pid, wid, qty))

    if not product_ids:
        return [], 0

    products_by_id = {
        p.id: p
        for p in Product.objects.filter(id__in=product_ids, is_available=True)
        .select_related("category")
        .prefetch_related("weight_options", "photos")
    }

    rows = []
    total = 0
    for item_key, pid, wid, quantity in parsed_entries:
        product = products_by_id.get(pid)
        if not product:
            continue

        weight_option = None
        if wid is not None:
            weight_option = next((w for w in product.weight_options.all() if w.id == wid and w.is_available), None)
            if not weight_option:
                continue
            unit_price = weight_option.selling_price
            weight_label = weight_option.weight
            original_price = weight_option.price_before_discount
        else:
            if product.has_weight_options:
                first_opt = product.weight_options.filter(is_available=True).first()
                if first_opt:
                    weight_option = first_opt
                    unit_price = first_opt.selling_price
                    weight_label = first_opt.weight
                    original_price = first_opt.price_before_discount
                else:
                    unit_price = product.selling_price
                    weight_label = ""
                    original_price = product.price_before_discount
            else:
                unit_price = product.selling_price
                weight_label = ""
                original_price = product.price_before_discount

        line_total = unit_price * quantity
        total += line_total
        rows.append({
            "key": item_key,
            "product": product,
            "weight_option": weight_option,
            "weight_label": weight_label,
            "unit_price": unit_price,
            "original_price": original_price,
            "quantity": quantity,
            "line_total": line_total,
        })
    return rows, total


def home(request):
    products = Product.objects.filter(is_available=True, is_featured=True).select_related("category").prefetch_related("dietary_tags")[:4]
    if not products:
        products = Product.objects.filter(is_available=True).select_related("category").prefetch_related("dietary_tags")[:4]
    featured_reviews = ProductReview.objects.filter(is_approved=True).select_related("product")[:6]
    hero_slides = HeroSlide.objects.filter(is_active=True).order_by("sort_order", "id")
    return render(request, "bakery/home.html", {
        "products": products,
        "featured_reviews": featured_reviews,
        "hero_slides": hero_slides,
    })


def _extract_unique_flavors():
    """Parse comma-separated flavors from all available products, return sorted unique list."""
    raw = Product.objects.filter(is_available=True).exclude(flavor="").values_list("flavor", flat=True)
    seen = {}  # normalized -> display
    for text in raw:
        for part in text.replace("،", ",").split(","):
            token = part.strip()
            if token and token not in seen:
                seen[token] = token
    return sorted(seen.values())


def _extract_unique_ingredients():
    return _extract_unique_flavors()


def _normalize_search_expr(field_name):
    return Replace(
        Replace(field_name, Value("\u200c"), Value("")),
        Value(" "),
        Value(""),
        output_field=TextField(),
    )


def menu(request):
    categories = ProductCategory.objects.filter(products__is_available=True).distinct()
    dietary_tags = DietaryTag.objects.filter(products__is_available=True).distinct()
    all_flavors = _extract_unique_flavors()
    selected_category = request.GET.get("category", "")
    selected_diet = request.GET.get("diet", "")
    selected_flavor = request.GET.get("flavor", request.GET.get("ingredient", "")).strip()
    query = request.GET.get("q", "").strip()[:80]
    valid_categories = set(categories.values_list("slug", flat=True))
    valid_diets = set(dietary_tags.values_list("slug", flat=True))
    if selected_category not in valid_categories:
        selected_category = ""
    if selected_diet not in valid_diets:
        selected_diet = ""
    if selected_flavor and selected_flavor not in all_flavors:
        selected_flavor = ""

    products = Product.objects.filter(is_available=True).select_related("category").prefetch_related("dietary_tags")
    if query:
        clean_q = query.replace("\u200c", "").replace(" ", "").strip()
        products = products.annotate(
            _search_name=_normalize_search_expr("name"),
            _search_sdesc=_normalize_search_expr("short_description"),
            _search_desc=_normalize_search_expr("description"),
            _search_flavor=_normalize_search_expr("flavor"),
            _search_ing=_normalize_search_expr("ingredients"),
        ).filter(
            Q(_search_name__icontains=clean_q)
            | Q(_search_sdesc__icontains=clean_q)
            | Q(_search_desc__icontains=clean_q)
            | Q(_search_flavor__icontains=clean_q)
            | Q(_search_ing__icontains=clean_q)
            | Q(name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(flavor__icontains=query)
            | Q(ingredients__icontains=query)
            | Q(ingredient_choices__name__icontains=query)
            | Q(recipe_items__ingredient__name__icontains=query)
        )
    if selected_category:
        products = products.filter(category__slug=selected_category)
    if selected_diet:
        products = products.filter(dietary_tags__slug=selected_diet)
    if selected_flavor:
        products = products.filter(Q(flavor__icontains=selected_flavor) | Q(ingredients__icontains=selected_flavor))
    context = {
        "products": products.distinct(),
        "categories": categories,
        "dietary_tags": dietary_tags,
        "all_flavors": all_flavors,
        "all_ingredients": all_flavors,
        "selected_category": selected_category,
        "selected_diet": selected_diet,
        "selected_flavor": selected_flavor,
        "selected_ingredient": selected_flavor,
        "query": query,
    }
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "bakery/_menu_results.html", context)
    return render(request, "bakery/menu.html", context)


def menu_search(request):
    """Canonical redirect: single search endpoint is /menu/?q=..."""
    query = request.GET.get("q", "").strip()
    target = reverse("menu")
    if query:
        from urllib.parse import quote_plus
        return redirect(f"{target}?q={quote_plus(query)}")
    return redirect(target)



def about(request):
    return render(request, "bakery/about.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ContactMessage.objects.create(**form.cleaned_data)
        return redirect(f"{reverse('contact')}?sent=1")
    return render(request, "bakery/contact.html", {
        "form": form,
        "sent": request.GET.get("sent") == "1" and request.method == "GET",
    })


def _safe_next_url(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse("customer_profile")


def _otp_digest(nonce, code):
    return salted_hmac("bakery.phone-login", f"{nonce}:{code}", secret=settings.SECRET_KEY, algorithm="sha256").hexdigest()


def _masked_phone(phone):
    return f"{phone[:4]}{'•' * 5}{phone[-2:]}"


def _login_context(request, phone_form=None, code_form=None, challenge=None):
    next_candidate = (
        request.session.get("phone_login_next")
        or request.GET.get("next")
        or request.POST.get("next")
    )
    return {
        "phone_form": phone_form or PhoneRequestForm(),
        "code_form": code_form or LoginCodeForm(),
        "challenge": challenge,
        "masked_phone": _masked_phone(challenge.phone) if challenge else "",
        "next_url": _safe_next_url(request, next_candidate),
        "show_development_code": settings.DEBUG and settings.OTP_SMS_BACKEND == "console",
        "resend_seconds": max(0, ceil((challenge.created_at + timedelta(seconds=settings.OTP_RESEND_SECONDS) - timezone.now()).total_seconds())) if challenge else 0,
        "resend_duration": settings.OTP_RESEND_SECONDS,
    }


def phone_login(request):
    if request.user.is_authenticated:
        return redirect("customer_profile")
    if request.method == "GET":
        if request.GET.get("change") == "1":
            request.session.pop("phone_login_challenge", None)
            request.session.pop("phone_login_next", None)
        challenge_nonce = request.session.get("phone_login_challenge")
        challenge = LoginCode.objects.filter(session_nonce=challenge_nonce, used_at__isnull=True).first() if challenge_nonce else None
        if challenge and challenge.expires_at > timezone.now() and challenge.attempts < settings.OTP_MAX_ATTEMPTS:
            return render(request, "bakery/phone_login.html", _login_context(request, challenge=challenge))
        request.session.pop("phone_login_challenge", None)
        return render(request, "bakery/phone_login.html", _login_context(request))

    action = request.POST.get("action", "send")
    if action == "verify":
        return _verify_phone_code(request)

    phone_form = PhoneRequestForm(request.POST)
    if not phone_form.is_valid():
        return render(request, "bakery/phone_login.html", _login_context(request, phone_form=phone_form))

    phone = phone_form.cleaned_data["phone"]
    now = timezone.now()
    window = now - timedelta(hours=1)
    remote_ip = request.META.get("REMOTE_ADDR")
    if LoginCode.objects.filter(phone=phone, created_at__gte=now - timedelta(seconds=settings.OTP_RESEND_SECONDS)).exists():
        phone_form.add_error("phone", "کد تازه فرستاده شده؛ یک دقیقه دیگر دوباره تلاش کنید.")
        return render(request, "bakery/phone_login.html", _login_context(request, phone_form=phone_form))
    if LoginCode.objects.filter(phone=phone, created_at__gte=window).count() >= 5:
        phone_form.add_error("phone", "برای این شماره فعلاً درخواست کد بیشتری ممکن نیست.")
        return render(request, "bakery/phone_login.html", _login_context(request, phone_form=phone_form))
    if remote_ip and LoginCode.objects.filter(ip_address=remote_ip, created_at__gte=window).count() >= 15:
        phone_form.add_error("phone", "درخواست‌های زیادی ثبت شده است. کمی بعد تلاش کنید.")
        return render(request, "bakery/phone_login.html", _login_context(request, phone_form=phone_form))

    LoginCode.objects.filter(created_at__lt=now - timedelta(days=2)).delete()
    nonce = uuid.uuid4()
    code = (
        "123456"
        if settings.DEBUG and settings.OTP_SMS_BACKEND == "console"
        else f"{secrets.randbelow(10 ** settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}"
    )
    challenge = LoginCode.objects.create(
        session_nonce=nonce,
        phone=phone,
        code_digest=_otp_digest(nonce, code),
        ip_address=remote_ip,
        expires_at=now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS),
    )
    try:
        send_login_code(phone, code)
    except SMSDeliveryError as exc:
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
        phone_form.add_error(None, str(exc))
        return render(request, "bakery/phone_login.html", _login_context(request, phone_form=phone_form))

    request.session["phone_login_challenge"] = str(nonce)
    request.session["phone_login_next"] = _safe_next_url(request, request.POST.get("next"))
    return render(request, "bakery/phone_login.html", _login_context(request, challenge=challenge))


def _verify_phone_code(request):
    nonce = request.session.get("phone_login_challenge")
    form = LoginCodeForm(request.POST)
    if not nonce:
        messages.error(request, "ابتدا شمارهٔ همراهتان را وارد کنید.")
        return redirect("phone_login")
    if not form.is_valid():
        challenge = LoginCode.objects.filter(session_nonce=nonce, used_at__isnull=True).first()
        return render(request, "bakery/phone_login.html", _login_context(request, code_form=form, challenge=challenge))

    with transaction.atomic():
        challenge = LoginCode.objects.select_for_update().filter(session_nonce=nonce).first()
        now = timezone.now()
        if not challenge or challenge.used_at or challenge.expires_at <= now or challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
            request.session.pop("phone_login_challenge", None)
            messages.error(request, "کد منقضی شده است. دوباره درخواست کد کنید.")
            return redirect("phone_login")

        challenge.attempts += 1
        valid_code = hmac.compare_digest(challenge.code_digest, _otp_digest(challenge.session_nonce, form.cleaned_data["code"]))
        if (
            not valid_code
            and settings.DEBUG
            and settings.OTP_SMS_BACKEND == "console"
            and form.cleaned_data["code"] == "123456"
        ):
            valid_code = True
        if valid_code:
            challenge.used_at = now
        challenge.save(update_fields=["attempts", "used_at"])
        phone = challenge.phone

    if not valid_code:
        if challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
            request.session.pop("phone_login_challenge", None)
            messages.error(request, "تعداد تلاش‌ها به پایان رسید. دوباره کد درخواست کنید.")
            return redirect("phone_login")
        form.add_error("code", "کد واردشده درست نیست.")
        return render(request, "bakery/phone_login.html", _login_context(request, code_form=form, challenge=challenge))

    User = get_user_model()
    with transaction.atomic():
        user = User.objects.select_for_update().filter(username=phone).first()
        if user and (user.is_staff or user.is_superuser or not user.is_active):
            request.session.pop("phone_login_challenge", None)
            messages.error(request, "ورود با این حساب امکان‌پذیر نیست.")
            return redirect("phone_login")
        if user is None:
            user = User.objects.create_user(username=phone)
        profile, _ = CustomerProfile.objects.get_or_create(user=user, defaults={"phone": phone})
        if profile.phone != phone:
            request.session.pop("phone_login_challenge", None)
            messages.error(request, "شمارهٔ همراه حساب با این شماره یکسان نیست.")
            return redirect("phone_login")

    next_url = request.session.pop("phone_login_next", reverse("customer_profile"))
    request.session.pop("phone_login_challenge", None)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    messages.success(request, "با موفقیت وارد شدید.")
    return redirect(_safe_next_url(request, next_url))


@login_required
def customer_profile(request):
    profile = CustomerProfile.objects.filter(user=request.user).first()
    if profile is None:
        return render(request, "bakery/profile.html", {
            "profile": None,
            "staff_account": request.user.is_staff or request.user.is_superuser,
        })
    form = CustomerProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پروفایلتان به‌روز شد.")
        return redirect("customer_profile")
    history = Order.objects.filter(Q(customer=request.user) | Q(phone=profile.phone)).distinct().order_by("-created_at", "-pk")
    paginator = Paginator(history, 10)
    orders = paginator.get_page(request.GET.get("page"))
    return render(request, "bakery/profile.html", {"profile": profile, "form": form, "orders": orders,
                                                  "order_count": paginator.count})


@require_POST
def phone_logout(request):
    logout(request)
    messages.info(request, "از حساب کاربری خارج شدید.")
    return redirect("home")


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category").prefetch_related("dietary_tags", "ingredient_choices", "recipe_items__ingredient"), slug=slug, is_available=True)
    reviews = product.reviews.filter(is_approved=True)

    initial = {}
    if request.user.is_authenticated:
        profile = CustomerProfile.objects.filter(user=request.user).first()
        if profile and profile.display_name:
            initial["author_name"] = profile.display_name

    form = ProductReviewForm(initial=initial)

    if request.method == "POST" and "submit_review" in request.POST:
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            if request.user.is_authenticated:
                profile = CustomerProfile.objects.filter(user=request.user).first()
                if profile:
                    review.customer = profile
            review.is_approved = False
            review.save()
            messages.success(request, "نظر شما با موفقیت ثبت شد و پس از بررسی و تأیید مدیریت نمایش داده می‌شود.")
            return redirect(product.get_absolute_url())

    return render(
        request,
        "bakery/product_detail.html",
        {
            "product": product,
            "reviews": reviews,
            "review_form": form,
        },
    )


def basket(request):
    items, total = _cart_products(request)
    return render(request, "bakery/basket.html", {"items": items, "total": total})


@require_POST
def add_to_basket(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_available=True)
    weight_id = request.POST.get("weight_id")
    cart = request.session.get("cart", {})
    weight_opt = None
    if weight_id:
        try:
            weight_opt = product.weight_options.filter(id=int(weight_id), is_available=True).first()
        except (ValueError, TypeError):
            weight_opt = None
    elif product.has_weight_options:
        weight_opt = product.weight_options.filter(is_available=True).first()

    if weight_opt:
        key = f"{product.id}_{weight_opt.id}"
        message = f"«{product.name} ({weight_opt.weight})» به سبد خرید اضافه شد."
    else:
        key = str(product.id)
        message = f"«{product.name}» به سبد خرید اضافه شد."

    cart[key] = min(int(cart.get(key, 0)) + 1, 99)
    request.session["cart"] = cart
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"cart_count": sum(int(q) for q in cart.values()), "message": message})
    messages.success(request, message)
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("basket")


def _basket_json(request):
    rows, total = _cart_products(request)
    return JsonResponse({
        "cart_count": sum(row["quantity"] for row in rows),
        "total": total,
        "items": [{
            "key": row["key"],
            "id": row["product"].id,
            "weight_label": row["weight_label"],
            "unit_price": row["unit_price"],
            "quantity": row["quantity"],
            "line_total": row["line_total"],
        } for row in rows],
    })


@require_POST
def update_basket(request, item_key):
    cart = request.session.get("cart", {})
    key = str(item_key)
    try:
        raw = request.POST.get("quantity", "1").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        quantity = int(raw)
        if not 0 <= quantity <= 99:
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "تعداد باید بین ۰ و ۹۹ باشد."}, status=400)
    if quantity <= 0:
        cart.pop(key, None)
    elif key in cart or _parse_cart_key(key)[0] is not None:
        cart[key] = min(quantity, 99)
    request.session["cart"] = cart
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return _basket_json(request)
    return redirect("basket")


@require_POST
def remove_from_basket(request, item_key):
    cart = request.session.get("cart", {})
    cart.pop(str(item_key), None)
    request.session["cart"] = cart
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return _basket_json(request)
    return redirect("basket")


def checkout(request):
    items, total = _cart_products(request)
    if not items:
        messages.info(request, "سبد خریدتان خالی است.")
        return redirect("menu")
    initial = {}
    if request.user.is_authenticated:
        profile = CustomerProfile.objects.filter(user=request.user).first()
        if profile:
            initial = {"customer_name": profile.display_name, "phone": profile.phone}
    form = CheckoutForm(request.POST or None, initial=initial if request.method == "GET" else None)
    if request.method == "POST" and form.is_valid():
        callback_base = settings.ZARINPAL_CALLBACK_BASE_URL or request.build_absolute_uri("/").rstrip("/")
        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                customer_name=form.cleaned_data["customer_name"],
                phone=form.cleaned_data["phone"],
                address=form.cleaned_data["address"],
                fulfillment=form.cleaned_data["fulfillment"],
                note=form.cleaned_data["note"],
                total=total,
            )
            OrderItem.objects.bulk_create([
                OrderItem(
                    order=order,
                    product=row["product"],
                    weight_option=row["weight_option"],
                    weight_label=row["weight_label"],
                    product_name=f"{row['product'].name} ({row['weight_label']})" if row["weight_label"] else row["product"].name,
                    unit_price=row["unit_price"],
                    quantity=row["quantity"],
                )
                for row in items
            ])
        callback_url = f"{callback_base}{reverse('payment_return')}?order={order.number}"
        try:
            authority = Zarinpal.request_payment(order, callback_url)
        except ZarinpalError as exc:
            order.payment_status = Order.PaymentStatus.FAILED
            order.save(update_fields=["payment_status"])
            messages.error(request, str(exc))
            return redirect("order_status", number=order.number)
        order.authority = authority
        order.payment_status = Order.PaymentStatus.INITIATED
        order.save(update_fields=["authority", "payment_status"])
        request.session["cart"] = {}
        if getattr(settings, "ZARINPAL_AUTO_APPROVE", False) and not settings.ZARINPAL_MERCHANT_ID:
            return redirect(f"{reverse('payment_return')}?order={order.number}&Authority={authority}&Status=OK")
        return redirect(Zarinpal.payment_url(authority))
    return render(request, "bakery/checkout.html", {"form": form, "items": items, "total": total})


def payment_return(request):
    order_number = request.GET.get("order")
    authority = request.GET.get("Authority", "")
    payment_status = request.GET.get("Status", "")
    if not order_number or not authority:
        return HttpResponseBadRequest("درخواست بازگشت از درگاه کامل نیست.")
    try:
        order = get_object_or_404(Order, number=order_number)
    except (ValueError, TypeError, ValidationError):
        return HttpResponseBadRequest("شمارهٔ سفارش معتبر نیست.")
    if order.payment_status == Order.PaymentStatus.PAID:
        return redirect("order_status", number=order.number)
    if authority != order.authority:
        return HttpResponseBadRequest("شناسهٔ پرداخت با سفارش تطابق ندارد.")
    if payment_status != "OK":
        order.payment_status = Order.PaymentStatus.FAILED
        order.save(update_fields=["payment_status"])
        messages.error(request, "پرداخت انجام نشد. سفارش پرداخت‌نشده باقی مانده است.")
        return redirect("order_status", number=order.number)
    try:
        ref_id = Zarinpal.verify_payment(order)
    except ZarinpalError as exc:
        messages.error(request, str(exc))
        return redirect("order_status", number=order.number)
    with transaction.atomic():
        locked_order = Order.objects.select_for_update().get(pk=order.pk)
        if locked_order.payment_status != Order.PaymentStatus.PAID:
            locked_order.payment_status = Order.PaymentStatus.PAID
            locked_order.status = Order.Status.PAID
            locked_order.ref_id = ref_id
            locked_order.paid_at = timezone.now()
            locked_order.save(update_fields=["payment_status", "status", "ref_id", "paid_at"])
    messages.success(request, "پرداخت با موفقیت تأیید شد.")
    return redirect("order_status", number=order.number)


def order_status(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    # Order URLs are unguessable UUIDs; no private delivery data is exposed here.
    return render(request, "bakery/order_status.html", {"order": order})


@require_POST
def retry_payment(request, number):
    order = get_object_or_404(Order, number=number)
    if order.payment_status == Order.PaymentStatus.PAID:
        return redirect("order_status", number=order.number)
    if order.payment_status not in (Order.PaymentStatus.FAILED, Order.PaymentStatus.UNPAID):
        messages.info(request, "وضعیت پرداخت این سفارش در حال بررسی است.")
        return redirect("order_status", number=order.number)
    callback_base = settings.ZARINPAL_CALLBACK_BASE_URL or request.build_absolute_uri("/").rstrip("/")
    callback_url = f"{callback_base}{reverse('payment_return')}?order={order.number}"
    try:
        authority = Zarinpal.request_payment(order, callback_url)
    except ZarinpalError as exc:
        messages.error(request, str(exc))
        return redirect("order_status", number=order.number)
    order.authority = authority
    order.payment_status = Order.PaymentStatus.INITIATED
    order.save(update_fields=["authority", "payment_status"])
    if getattr(settings, "ZARINPAL_AUTO_APPROVE", False) and not settings.ZARINPAL_MERCHANT_ID:
        return redirect(f"{reverse('payment_return')}?order={order.number}&Authority={authority}&Status=OK")
    return redirect(Zarinpal.payment_url(authority))
