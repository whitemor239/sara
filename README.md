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

## قیمت‌گذاری بر اساس مواد اولیه

1. در پنل مدیریت، بخش **مواد اولیه و قیمت روز** (`/admin/bakery/ingredient/`) را باز کنید. نام ماده و قیمت **هر کیلو به تومان** را وارد کنید؛ قیمت‌ها در فهرست هم قابل ویرایش‌اند و زمان آخرین تغییر نمایش داده می‌شود.
2. در ویرایش هر محصول، جدول **مواد مصرفی دستور پخت** را با ماده و مقدار مصرف **به گرم** تکمیل کنید. **وزن محصول نهایی دستور پخت** را پس از پخت وارد کنید؛ این وزن لزوماً برابر مجموع وزن مواد خام نیست.
3. **درصد سود روی هزینهٔ مواد** را تعیین و **محاسبهٔ خودکار قیمت از مواد اولیه** را فعال کنید. قیمت دستی در این حالت الزامی نیست و پس از ذخیره محاسبه می‌شود.
4. برای هر گزینهٔ وزن، عنوان‌هایی مانند «۵۰۰ گرم» و «۱ کیلوگرم» خودکار تشخیص داده می‌شوند. برای عنوان‌هایی مثل «۴ عددی»، **وزن محاسباتی (گرم)** کل بسته را مشخص کنید. مقدار مصرف مواد و قیمت هر وزن به نسبت وزن خروجی دستور پایه محاسبه می‌شود.

فرمول: `هزینهٔ مواد = مجموع (مصرف به گرم × قیمت هر کیلو ÷ ۱۰۰۰)`؛ `قیمت فروش = هزینهٔ مواد × (۱ + درصد سود ÷ ۱۰۰)`. برای وزن‌های دیگر ابتدا مقدار مواد و هزینه به نسبت وزن محاسبه و فقط قیمت فروش نهایی به نزدیک‌ترین تومان گرد می‌شود (حداقل یک تومان). هزینهٔ بسته‌بندی، دستمزد و دیگر هزینه‌ها در این فرمول نیستند.

مثال: موادِ یک دستور با خروجی ۵۰۰ گرم، ۸۰٬۰۰۰ تومان هزینه دارد؛ با سود ۲۵٪، قیمت ۵۰۰ گرم ۱۰۰٬۰۰۰ و یک کیلوگرم ۲۰۰٬۰۰۰ تومان است.

در بخش **ترکیبات** محصول، مواد اولیه را از فهرست قابل جست‌وجو انتخاب کنید. مواد مصرفی دستور پخت نیز در ترکیبات نمایشی لحاظ می‌شوند. متن ترکیبات محصولات قدیمی حفظ می‌شود تا عمداً انتخاب جدیدی ثبت کنید.

ورودی قیمت‌ها در ادمین هنگام تایپ با جداکنندهٔ سه‌رقمی نمایش داده می‌شوند (مثل `1٬250٬000`)؛ ارقام فارسی، عربی و انگلیسی و جداکننده‌های `,` و `٬` هنگام ذخیره پذیرفته می‌شوند. **قیمت عادی** و **قیمت با تخفیف** جدا هستند؛ قیمت تخفیف اختیاری است و خالی‌گذاشتن آن مقدار `0` (بدون تخفیف) ذخیره می‌کند. مبلغ صفر تخفیف باعث رایگان‌شدن محصول نمی‌شود. برای هر گزینهٔ وزن هم می‌توان تخفیف مستقل ثبت کرد. محاسبهٔ خودکار قیمت عادی را به‌روز می‌کند؛ تخفیف فقط زمانی اعمال می‌شود که از قیمت عادی کمتر باشد.

با ذخیرهٔ تغییر قیمت یک ماده، مقدار مصرف، درصد سود یا وزن، قیمت تمام محصولات مرتبط که حالت خودکار دارند به‌روز می‌شود. در حالت دستی قیمت‌ها حفظ می‌شوند؛ ریز هزینه و مقدار مواد هر وزن در ویرایش محصول قابل مشاهده است. سفارش‌های ثبت‌شده قیمت تاریخی خود را حفظ می‌کنند. تغییرات عمده از طریق `QuerySet.update()`/`bulk_update()` سیگنال ذخیره را اجرا نمی‌کنند؛ برای چنین تغییراتی از عملیات «محاسبهٔ دوبارهٔ قیمت محصولات خودکار» در فهرست محصولات استفاده کنید.

## Checks

```sh
python manage.py check
python manage.py test
```

On a Linux host, serve the application with `gunicorn tastytum.wsgi:application`. Configure the host to serve `static/`/`staticfiles/` and uploaded `media/` files, and use a persistent database and media storage for production (the local default is SQLite).
