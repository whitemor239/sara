import csv
import re
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Avg, Q, Sum
from django.urls import reverse
from urllib.parse import urlencode
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import ContactMessage, CustomerProfile, Order, Product


WEEKDAYS = ("شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه")
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _matching_orders(request):
    query = request.GET.get("q", "").strip()[:80]
    orders = Order.objects.all()
    if query:
        normalized = query.translate(DIGITS)
        orders = orders.filter(
            Q(customer_name__icontains=query)
            | Q(phone__icontains=normalized)
            | Q(number__icontains=normalized)
        )
    return query, orders


def _spreadsheet_text(value):
    return f"'{value}" if re.match(r"^[\s\x00-\x1f]*[=+@-]", value) else value


def dashboard_context(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=(today.weekday() + 2) % 7)
    paid_orders = Order.objects.filter(payment_status=Order.PaymentStatus.PAID)
    daily = paid_orders.filter(paid_at__date=today).aggregate(sales_sum=Sum("total"), basket_average=Avg("total"))
    weekly_totals = {
        item["day"]: item["total"]
        for item in paid_orders.filter(paid_at__date__range=(week_start, week_start + timedelta(days=6)))
        .annotate(day=TruncDate("paid_at", tzinfo=timezone.get_current_timezone()))
        .values("day")
        .annotate(total=Sum("total"))
    }
    amounts = [weekly_totals.get(week_start + timedelta(days=offset), 0) for offset in range(7)]
    highest = max(amounts, default=0)
    bars = [
        {
            "label": label,
            "amount": amounts[index],
            "height": max(5, round(amounts[index] / highest * 100)) if highest and amounts[index] else 0,
            "is_peak": bool(highest and amounts[index] == highest),
            "is_today": week_start + timedelta(days=index) == today,
        }
        for index, label in enumerate(WEEKDAYS)
    ]
    period = request.GET.get("period", "weekly")
    if period not in ("daily", "weekly", "monthly"):
        period = "weekly"
    if period != "weekly":
        count = 24 if period == "daily" else 30
        start = today if period == "daily" else today - timedelta(days=29)
        values = [0] * count
        for order in paid_orders.filter(paid_at__date__range=(start, today)).only("paid_at", "total"):
            local = timezone.localtime(order.paid_at)
            index = local.hour if period == "daily" else (local.date() - start).days
            values[index] += order.total
        from .templatetags.bakery_tags import jalali_date
        bars = [{"label": (str(index).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")) if period == "daily" else jalali_date(start + timedelta(days=index), "short")),
                 "amount": amount, "is_today": (index == timezone.localtime().hour if period == "daily" else index == 29),
                 "is_peak": bool(amount and amount == max(values))} for index, amount in enumerate(values)]
    period_titles = {"daily": "فروش روزانه", "weekly": "فروش هفتگی", "monthly": "فروش ماهانه"}
    period_notes = {"daily": "امروز، به تفکیک ساعت", "weekly": "از شنبه تا جمعه", "monthly": "۳۰ روز اخیر، به تفکیک روز"}
    now = timezone.localtime()
    for index, bar in enumerate(bars):
        future = (week_start + timedelta(days=index) > today) if period == "weekly" else (index > now.hour if period == "daily" else False)
        bar["is_future"] = future
        if future:
            bar["amount"] = None
            bar["is_peak"] = False
    query, orders = _matching_orders(request)
    page = Paginator(orders, 12).get_page(request.GET.get("page"))
    clear_params = urlencode({"period": period})
    all_params = urlencode({"q": query}) if query else ""
    return {
        "period": period,
        "period_title": period_titles[period],
        "period_note": period_notes[period],
        "period_sales": sum(bar["amount"] or 0 for bar in bars),
        "today": today,
        "sales_today": daily["sales_sum"] or 0,
        "average_basket": round(daily["basket_average"] or 0),
        "open_orders": Order.objects.exclude(status__in=(Order.Status.COMPLETED, Order.Status.CANCELLED)).count(),
        "new_customers": CustomerProfile.objects.filter(created_at__date=today, user__is_staff=False, user__is_superuser=False).count(),
        "pending_orders": Order.objects.filter(status=Order.Status.PENDING).count(),
        "preparing_orders": Order.objects.filter(status=Order.Status.PREPARING).count(),
        "unread_messages": ContactMessage.objects.filter(is_read=False).count(),
        "product_count": Product.objects.count(),
        "bars": bars,
        "weekly_sales": sum(amounts),
        "query": query,
        "orders": page.object_list,
        "page_obj": page,
        "total_results": orders.count(),
        "has_orders": page.paginator.count > 0,
        "clear_search_url": f"{request.path}?{clear_params}",
        "view_all_admin_url": f"{reverse('admin:bakery_order_changelist')}?{all_params}" if all_params else reverse('admin:bakery_order_changelist'),
    }


@staff_member_required(login_url="/admin/login/")
@never_cache
def dashboard(request):
    return render(request, "bakery/dashboard.html", dashboard_context(request))


@staff_member_required(login_url="/admin/login/")
@never_cache
def export_orders(request):
    _, orders = _matching_orders(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="tastytum-orders.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(("شماره سفارش", "مشتری", "موبایل", "مبلغ (تومان)", "وضعیت", "زمان ثبت"))
    for order in orders.iterator():
        # Prevent spreadsheet programs from interpreting customer input as formulas.
        writer.writerow((
            str(order.number), _spreadsheet_text(order.customer_name), _spreadsheet_text(order.phone), order.total,
            order.get_status_display(), timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M"),
        ))
    return response
