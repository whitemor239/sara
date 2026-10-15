from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import Product, ProductWeightOption
from .widgets import MoneyField


class ProductPricingForm(forms.ModelForm):
    price = MoneyField(
        label="قیمت عادی / پایه (تومان)", required=False, min_value=1,
        help_text="در حالت خودکار نیاز به ورود قیمت نیست؛ پس از ذخیره از دستور پخت محاسبه می‌شود. در حالت دستی الزامی است.",
    )
    discounted_price = MoneyField(label="قیمت با تخفیف (تومان)", required=False, min_value=0, initial=0,
                                  help_text="اختیاری؛ خالی یا صفر یعنی بدون تخفیف.")

    class Meta:
        model = Product
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("price") is None:
            automatic = cleaned.get("auto_pricing") if "auto_pricing" in self.fields else self.instance.auto_pricing
            if automatic:
                cleaned["price"] = self.instance.price or 1
            else:
                self.add_error("price", "در حالت دستی قیمت فروش را وارد کنید.")
        return cleaned

    def clean_discounted_price(self):
        return self.cleaned_data.get("discounted_price") or 0


class RecipeIngredientFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active = [form for form in self.forms if form.cleaned_data and not form.cleaned_data.get("DELETE")]
        if self.instance.auto_pricing and not active:
            raise ValidationError("برای قیمت‌گذاری خودکار، حداقل یک مادهٔ اولیه و مقدار مصرف آن را ثبت کنید.")


class WeightOptionPricingForm(forms.ModelForm):
    price = MoneyField(
        label="قیمت عادی (تومان)", required=False, min_value=1,
        help_text="در حالت محاسبهٔ خودکار می‌تواند خالی باشد؛ قیمت بر اساس وزن این گزینه محاسبه می‌شود.",
    )
    discounted_price = MoneyField(label="قیمت با تخفیف (تومان)", required=False, min_value=0, initial=0,
                                  help_text="اختیاری؛ خالی یا صفر یعنی بدون تخفیف.")

    class Meta:
        model = ProductWeightOption
        fields = "__all__"

    def clean_price(self):
        value = self.cleaned_data.get("price")
        self.price_was_omitted = value is None
        return 1 if value is None else value

    def clean_discounted_price(self):
        return self.cleaned_data.get("discounted_price") or 0


class WeightOptionPricingFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            if self.instance.auto_pricing:
                if form.instance.resolved_weight_grams is None:
                    form.add_error("weight_grams", "برای این عنوان، وزن واقعی بسته را به گرم وارد کنید.")
            elif getattr(form, "price_was_omitted", False):
                form.add_error("price", "در حالت دستی قیمت این وزن را وارد کنید.")
            elif form.instance.discounted_price and form.instance.discounted_price >= form.instance.regular_price:
                form.add_error("discounted_price", "قیمت با تخفیف باید کمتر از قیمت عادی باشد؛ برای حذف تخفیف صفر وارد کنید.")
