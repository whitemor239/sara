from django.urls import path
from django.views.generic import RedirectView

from . import dashboard, views

urlpatterns = [
    path("", views.home, name="home"),
    path("menu/", views.menu, name="menu"),
    path("menu/search/", views.menu_search, name="menu_search"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("dashboard/", dashboard.dashboard, name="shop_dashboard"),
    path("dashboard/orders.csv", dashboard.export_orders, name="dashboard_export_orders"),
    path("account/login/", views.phone_login, name="phone_login"),
    path("account/profile/", views.customer_profile, name="customer_profile"),
    path("profile", RedirectView.as_view(pattern_name="customer_profile", permanent=False)),
    path("profile/", RedirectView.as_view(pattern_name="customer_profile", permanent=False)),
    path("account/logout/", views.phone_logout, name="phone_logout"),
    path("pastry/<slug:slug>/", views.product_detail, name="product_detail"),
    path("basket/", views.basket, name="basket"),
    path("basket/add/<int:product_id>/", views.add_to_basket, name="add_to_basket"),
    path("basket/update/<str:item_key>/", views.update_basket, name="update_basket"),
    path("basket/remove/<str:item_key>/", views.remove_from_basket, name="remove_from_basket"),
    path("checkout/", views.checkout, name="checkout"),
    path("payment/return/", views.payment_return, name="payment_return"),
    path("order/<uuid:number>/retry-payment/", views.retry_payment, name="retry_payment"),
    path("order/<uuid:number>/", views.order_status, name="order_status"),
]
