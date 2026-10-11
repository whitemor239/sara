from django import forms

from .models import CustomerProfile, ProductReview
from .phone import normalize_iranian_mobile


class CheckoutForm(forms.Form):
    FULFILLMENT_CHOICES = (("delivery", "ارسال به نشانی"), ("pickup", "تحویل حضوری"))
    customer_name = forms.CharField(label="نام و نام خانوادگی", max_length=120)
    phone = forms.CharField(label="شمارهٔ همراه", max_length=20)
    fulfillment = forms.ChoiceField(label="روش دریافت", choices=FULFILLMENT_CHOICES, widget=forms.RadioSelect)
    address = forms.CharField(label="نشانی", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    note = forms.CharField(label="یادداشت برای سفارش", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def clean_phone(self):
        try:
            return normalize_iranian_mobile(self.cleaned_data["phone"])
        except ValueError:
            raise forms.ValidationError("شمارهٔ همراه را بررسی کنید.")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fulfillment") == "delivery" and not cleaned.get("address", "").strip():
            self.add_error("address", "برای ارسال، نشانی را وارد کنید.")
        return cleaned


class ProductReviewForm(forms.ModelForm):
    RATING_CHOICES = (
        (5, "۵ ستاره: عالی"),
        (4, "۴ ستاره: خوب"),
        (3, "۳ ستاره: معمولی"),
        (2, "۲ ستاره: ضعیف"),
        (1, "۱ ستاره: ناراضی"),
    )
    rating = forms.ChoiceField(label="امتیاز شما", choices=RATING_CHOICES, initial=5, widget=forms.Select)

    class Meta:
        model = ProductReview
        fields = ("author_name", "rating", "comment")
        labels = {
            "author_name": "نام شما",
            "comment": "نظر یا تجربهٔ شما",
        }
        widgets = {
            "author_name": forms.TextInput(attrs={"placeholder": "مثال: مریم احمدی"}),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "دربارهٔ طعم، بافت، عطر یا بسته‌بندی بنویسید…"}),
        }


class ContactForm(forms.Form):
    name = forms.CharField(label="نام و نام خانوادگی", max_length=120)
    phone = forms.CharField(label="شمارهٔ همراه", max_length=20)
    subject = forms.CharField(label="موضوع پیام", max_length=140)
    message = forms.CharField(label="پیامتان", max_length=3000, widget=forms.Textarea(attrs={"rows": 6}))

    def clean_phone(self):
        try:
            return normalize_iranian_mobile(self.cleaned_data["phone"])
        except ValueError:
            raise forms.ValidationError("شمارهٔ همراه را بررسی کنید.")


class PhoneRequestForm(forms.Form):
    phone = forms.CharField(
        label="شمارهٔ همراه",
        max_length=24,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "dir": "ltr", "placeholder": "۰۹۱۲۱۲۳۴۵۶۷"}),
    )

    def clean_phone(self):
        try:
            return normalize_iranian_mobile(self.cleaned_data["phone"])
        except ValueError:
            raise forms.ValidationError("یک شمارهٔ همراه معتبر وارد کنید.")


class LoginCodeForm(forms.Form):
    code = forms.CharField(
        label="کد ورود",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            "class": "otp-code",
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "pattern": "[0-9]{6}",
            "dir": "ltr",
            "placeholder": "••••••",
        }),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        if len(code) != 6 or not code.isascii() or not code.isdigit():
            raise forms.ValidationError("کد باید شامل شش رقم باشد.")
        return code


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = CustomerProfile
        fields = ("display_name",)
        labels = {"display_name": "نام و نام خانوادگی"}
        widgets = {"display_name": forms.TextInput(attrs={"autocomplete": "name", "aria-describedby": "profile-name-hint profile-name-error"})}
