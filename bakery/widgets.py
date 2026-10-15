from django import forms
from django.utils.safestring import mark_safe

from .money import grouped_integer, normalize_money_input


class MoneyInput(forms.TextInput):
    def __init__(self, attrs=None):
        super().__init__({"inputmode": "numeric", "dir": "ltr", "data-money-input": "", "autocomplete": "off", **(attrs or {})})

    def format_value(self, value):
        return grouped_integer(value)

    class Media:
        js = ("bakery/admin_money.js",)


class MoneyField(forms.IntegerField):
    widget = MoneyInput

    def to_python(self, value):
        return super().to_python(normalize_money_input(value))


class FlavorTagWidget(forms.TextInput):
    class Media:
        css = {
            "all": ("bakery/flavor_tags.css",)
        }
        js = ("bakery/flavor_tags.js",)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs["class"] = (attrs.get("class", "") + " flavor-tags-backing").strip()
        attrs["style"] = "display: none;"
        hidden_html = super().render(name, value, attrs, renderer)
        return mark_safe(f"""
        <div class="flavor-tags-widget" data-flavor-tags-root>
            <div class="flavor-tags-container"></div>
            <input type="text" class="flavor-tags-input" placeholder="طعم را بنویسید و کلید Tab یا Enter بزنید..." autocomplete="off">
            {hidden_html}
            <small class="flavor-tags-help">با زدن کلید Tab، Enter یا کاما (،)، طعم به صورت برچسب اضافه می‌شود.</small>
        </div>
        """)
