import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tastytum.settings")
import django
django.setup()
from django.test import RequestFactory
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import resolve
from django.core.paginator import Paginator
from django.utils import timezone
from bakery.models import CustomerProfile, Order
from bakery.forms import CustomerProfileForm
from pathlib import Path
request=RequestFactory().get("/account/profile/")
request.user=get_user_model()(username="audit",is_staff=False)
request.session={}
request._messages=FallbackStorage(request)
request.resolver_match=resolve("/account/profile/")
profile=CustomerProfile(phone="09121234567",display_name="مریم رضایی")
orders=[Order(number="12345678-1234-1234-1234-123456789abc",customer_name="مریم",phone=profile.phone,total=123456,status="pending",payment_status="unpaid",created_at=timezone.now(),fulfillment="delivery") for _ in range(21)]
paginator=Paginator(orders,10)
for state in ("populated","empty","error"):
    form=CustomerProfileForm(instance=profile) if state!="error" else CustomerProfileForm({"display_name":"x"*300},instance=profile)
    if state=="error":form.is_valid()
    html=render_to_string("bakery/profile.html",{"profile":profile,"form":form,"orders":paginator.page(1) if state!="empty" else [],"order_count":21 if state!="empty" else 0},request=request)
    Path("/home/tyler/.hermes/cache/scratch/profile-"+state+".html").write_text(html)
print("Rendered isolated audit fixtures; no DB writes")
