# TastyTum bakery

Persian RTL bakery storefront built with Django. Products are managed in Django admin; customers can place delivery or pickup orders and pay through Zarinpal.

## Local setup

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `/admin/` to add products, organize them into menu categories, assign verified dietary tags, review orders, and respond to contact messages. Upload real product photography there, add useful alt text, and mark products available. The homepage hero uses a labeled sample tart image; replace it with approved bakery photography when available. The homepage and menu show an empty-menu state until products are added. Dietary tags are intentionally managed by the bakery; only assign claims such as vegan or gluten-free after checking the recipe and handling process. The public contact form stores inquiries in admin; add the bakery's real phone, email, and address to the contact page when those details are ready.

Staff accounts can open `/dashboard/` after logging in through `/admin/login/`. The Django admin home at `/admin/` displays the **same live dashboard**; catalog/order edit pages use matching typography and colors. This server-rendered dashboard uses actual paid orders for sales totals and weekly bars, shows recent orders and customer counts, and links to Django admin for editing. Searching and downloading the filtered orders as CSV also work on both dashboard entry points. The separate `shop-dashboard.tsx` file is a reusable React design example, not the page served by Django.

Customers can create an account and sign in with a mobile number and a six-digit SMS code; there is no customer password. In local development (`DJANGO_DEBUG=1`, `OTP_SMS_BACKEND=console`), the test code is always `123456` and is shown on the verification screen and in the runserver terminal. In production the code is random. Set `OTP_SMS_BACKEND=kavenegar`, `KAVENEGAR_API_KEY`, and `KAVENEGAR_VERIFY_TEMPLATE` to send real messages. Create and approve a Kavenegar verification template containing `%token` before enabling live login. OTPs expire after five minutes, allow five verification attempts, and requests are rate-limited.

Copy `.env.example` and provide its values through your shell or deployment environment (Django does not load `.env` files automatically). For local payment testing, set `ZARINPAL_SANDBOX=1` and configure a Zarinpal test merchant ID. For production, set `DJANGO_DEBUG=0`, a unique `DJANGO_SECRET_KEY`, correct `DJANGO_ALLOWED_HOSTS`, a live merchant ID, and a public HTTPS `ZARINPAL_CALLBACK_BASE_URL`. Production settings enforce HTTPS redirects, secure cookies, and HSTS; only deploy with TLS configured end-to-end.

Prices are entered in tomans; the Zarinpal API amount is sent in rials. Payment credentials are never stored in the database. A payment is only marked paid after server-side verification.

## Checks

```sh
python manage.py check
python manage.py test
```

On a Linux host, serve the application with `gunicorn tastytum.wsgi:application`. Configure the host to serve `static/`/`staticfiles/` and uploaded `media/` files, and use a persistent database and media storage for production (the local default is SQLite).
