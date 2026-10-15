from django import template
from ..jalali import JALALI_MONTH_NAMES, to_jalali_tuple

register = template.Library()


def pagination_items(current, total):
    selected = sorted({1, total, *range(max(1, current - 1), min(total, current + 1) + 1)})
    result = []
    for page in selected:
        if result:
            gap = page - result[-1]
            if gap == 2:
                result.append(page - 1)
            elif gap > 2:
                result.append(None)
        result.append(page)
    return result


@register.inclusion_tag("bakery/_pagination.html", takes_context=True)
def render_pagination(context, page, anchor=""):
    request = context["request"]
    def href(number):
        params = request.GET.copy()
        params["page"] = str(number)
        return "?" + params.urlencode() + ("#" + anchor if anchor else "")
    return {"page": page, "links": [{"number": n, "url": href(n) if n else ""} for n in pagination_items(page.number, page.paginator.num_pages)],
            "previous_url": href(page.previous_page_number()) if page.has_previous() else "",
            "next_url": href(page.next_page_number()) if page.has_next() else ""}


@register.simple_tag
def catalog_srcset(image):
    from pathlib import Path
    if not image:
        return ""
    path = Path(image.path)
    variants = []
    for width in (320, 640, 960):
        target = path.with_name(path.stem + f"-catalog-{width}.webp")
        if target.is_file():
            variants.append(image.url.rsplit("/", 1)[0] + "/" + target.name + f" {width}w")
    return ", ".join(variants)

_digit_map = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


@register.filter
def fa_digits(value):
    if value is None:
        return ""
    return str(value).translate(_digit_map)


@register.filter
def jalali_date(value, format_type="numeric"):
    """
    Format date/datetime as Jalali with Persian digits.
    format_type:
      'numeric' -> '۱۴۰۵/۰۷/۰۸'
      'long'    -> '۸ مهر ۱۴۰۵'
      'full'    -> '۸ مهر ۱۴۰۵ ساعت ۱۴:۳۰'
    """
    if not value:
        return ""
    res = to_jalali_tuple(value)
    if not res:
        return value
    (jy, jm, jd), time_part = res

    if format_type == "long":
        m_name = JALALI_MONTH_NAMES[jm - 1]
        text = f"{jd} {m_name} {jy}"
    elif format_type == "full":
        m_name = JALALI_MONTH_NAMES[jm - 1]
        if time_part:
            h, mn = time_part
            text = f"{jd} {m_name} {jy}، ساعت {h:02d}:{mn:02d}"
        else:
            text = f"{jd} {m_name} {jy}"
    else:  # 'numeric'
        if time_part and format_type == "numeric_with_time":
            h, mn = time_part
            text = f"{jy:04d}/{jm:02d}/{jd:02d} {h:02d}:{mn:02d}"
        else:
            text = f"{jy:04d}/{jm:02d}/{jd:02d}"

    return text.translate(_digit_map)


@register.filter
def compact_fa(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return value
    abs_n = abs(n)
    if abs_n >= 1_000_000_000:
        val = f"{n / 1_000_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{val.translate(_digit_map)} میلیارد"
    if abs_n >= 1_000_000:
        val = f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{val.translate(_digit_map)} میلیون"
    if abs_n >= 1_000:
        val = str(round(n / 1_000))
        return f"{val.translate(_digit_map)} هزار"
    return str(n).translate(_digit_map)


@register.filter
def toman(value):
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return value
    return f"{amount:,}".replace(",", "٬").translate(_digit_map)


@register.filter
def cost_toman(value):
    from ..money import decimal_toman
    return decimal_toman(value)


@register.inclusion_tag("bakery/_dashboard_chart.html")
def render_dashboard_chart(bars, height=180):
    W = 600
    H = height
    padR = 120
    padL = 12
    padT = 16
    padB = 28
    plotW = W - padL - padR
    plotH = H - padT - padB

    max_val = max([b.get("amount") or 0 for b in bars], default=1) or 1
    # Nice round ticks
    import math
    step = 10 ** max(0, math.floor(math.log10(max_val or 1)))
    nice = step
    for m in [1, 2, 2.5, 5, 10]:
        candidate = int(m * step)
        if candidate > 0 and (max_val / candidate) <= 4:
            nice = candidate
            break
    top = max(1, math.ceil(max_val / nice) * nice)
    ticks_count = min(6, max(2, round(top / nice) + 1))
    ticks_vals = [i * nice for i in range(ticks_count) if i * nice <= top]
    if top not in ticks_vals:
        ticks_vals.append(top)

    def get_y(v):
        return round(padT + plotH - (v / top) * plotH, 1)

    ticks_data = [{"val": v, "y": get_y(v)} for v in ticks_vals]

    n = max(1, len(bars))
    slot = plotW / n
    bw = round(slot * 0.55, 1)

    chart_bars = []
    line_pts = []
    for i, b in enumerate(bars):
        # RTL: i=0 (first day / Saturday) is at the right edge
        x_slot = round(W - padR - (i + 1) * slot, 1)
        bx = round(x_slot + (slot - bw) / 2, 1)
        amt = b.get("amount")
        has_amt = amt is not None
        by = get_y(amt or 0)
        bar_h = round(padT + plotH - by, 1) if has_amt else 0
        center_x = round(bx + bw / 2, 1)

        chart_bars.append({
            "label": b.get("label", "") if len(bars) <= 7 or i % 5 == 0 or i == len(bars)-1 else "",
            "full_label": b.get("full_label", b.get("label", "")),
            "slot": round(slot, 1),
            "tooltip_y": max(2, by - 28),
            "amount": amt,
            "has_amount": has_amt,
            "is_future": b.get("is_future", False),
            "is_today": b.get("is_today", False),
            "is_peak": b.get("is_peak", False),
            "x_slot": x_slot,
            "bx": bx,
            "by": by,
            "bw": bw,
            "bh": bar_h,
            "cx": center_x,
        })
        if has_amt:
            line_pts.append((center_x, by))

    path = ""
    for i, (px, py) in enumerate(line_pts):
        if i == 0:
            path = f"M {px} {py}"
        else:
            qx, qy = line_pts[i-1]
            cx = round((qx + px) / 2, 1)
            path += f" C {cx} {qy}, {cx} {py}, {px} {py}"
    area = (path + f" L {line_pts[-1][0]} {padT+plotH} L {line_pts[0][0]} {padT+plotH} Z") if line_pts else ""
    return {
        "line_path": path,
        "area_path": area,
        "W": W,
        "H": H,
        "padL": padL,
        "padR": padR,
        "axis_x": W - padR,
        "tick_x": W - 8,
        "padT": padT,
        "padB": padB,
        "plotW": plotW,
        "plotH": plotH,
        "ticks": ticks_data,
        "bars": chart_bars,
    }


@register.inclusion_tag("bakery/_price.html")
def render_price(amount, original=None, unit="تومان", size="md", dynamic=False):
    off = 0
    orig = None
    try:
        amt = int(amount)
        if original:
            orig = int(original)
            if orig > amt:
                # Round half up, matching Math.round in the weight selector.
                off = (200 * (orig - amt) + orig) // (2 * orig)
    except (TypeError, ValueError):
        amt = amount
        orig = original

    return {
        "amount": amt,
        "original": orig if original else None,
        "off": off,
        "unit": unit,
        "size": size,
        "dynamic": dynamic,
    }
