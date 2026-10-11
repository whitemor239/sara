# TastyTum Bakery - Roadmap and TODO

Progress tracker. Mark items `[x]` when done. Add date in brackets when finished, like `[x] (2026-10-02)`.

Current state (2026-09-30): working MVP. Product catalog, session cart, Zarinpal payment, OTP phone login, staff dashboard, contact form, CSV export. SQLite DB.

Legend: `[ ]` todo | `[x]` done | `[~]` in progress

---

## Phase 1 - Core Commerce Gaps (high priority, revenue impact)

### 1.1 Discount and Coupon System
- [ ] Coupon model: code, type (percent / fixed), min_order amount, max_discount, usage_limit, per_user_limit, expiry date, active flag
- [ ] Coupon field on checkout form, validation (exists, active, not expired, limit not reached, order meets min)
- [ ] Discount line shown on checkout page, order total calculation updated
- [ ] Coupon usage tracked per order, counter incremented on paid order
- [ ] Coupon management in Django admin

### 1.2 Shipping and Delivery Zones
- [ ] DeliveryZone model: name, areas description, fee, free above min order
- [ ] Shipping fee calculated at checkout based on delivery choice
- [ ] Pickup always free
- [ ] Fee shown to customer before payment
- [ ] Zones editable in admin

### 1.3 Inventory and Stock Tracking
- [ ] stock_count field on Product (blank = unlimited)
- [ ] Stock decremented when order paid
- [ ] Stock restored when order cancelled
- [ ] Product auto marked unavailable at zero stock
- [ ] Low stock warning list in dashboard

### 1.4 Order Status SMS Notifications
- [ ] SMS sent to customer on status change (preparing, ready, completed)
- [ ] Kavenegar templates per status
- [ ] Notification log so staff can see what was sent
- [ ] Failure does not block status update

### 1.5 Product Variants
- [ ] ProductVariant model: product FK, label (500g / 1kg etc), price
- [ ] Variant picker on product detail page
- [ ] Variants carried through cart and order items
- [ ] Migration path for existing single price products

---

## Phase 2 - Customer Experience

### 2.1 Wishlist / Favorites
- [ ] Favorite model linking customer to products
- [ ] Heart button on product cards and detail page
- [ ] Favorites list in customer profile

### 2.2 Product Reviews and Ratings
- [ ] Review model: user, product, rating 1-5, text, approved flag, created_at
- [ ] Only verified buyers can review
- [ ] Staff moderation queue in admin
- [ ] Average rating shown on product cards

### 2.3 Product Search
- [ ] Search over name, description, ingredients
- [ ] Search box in header
- [ ] Results page with count and empty state

### 2.4 Order History Improvements
- [ ] Reorder button on past orders (refills cart)
- [ ] Order detail page for customer with status timeline
- [ ] Link to payment retry when applicable

### 2.5 Address Book
- [ ] SavedAddress model on CustomerProfile
- [ ] Pick saved address at checkout
- [ ] Manage addresses in profile

### 2.6 Product Image Gallery
- [ ] ProductImage model: product FK, image, alt text, sort_order
- [ ] Multiple images per product
- [ ] Gallery on detail page, thumbnail on cards
- [ ] First image used as card image

---

## Phase 3 - Operations and Admin

### 3.1 Dashboard Improvements
- [ ] Monthly sales chart alongside weekly
- [ ] Top selling products list
- [ ] Revenue breakdown by category
- [ ] Quick reply to contact messages from dashboard
- [ ] Sales compared to previous period (percent change)

### 3.2 Print Invoice
- [ ] Printable order view (print CSS, no PDF dependency)
- [ ] Bakery branding, items, totals, payment ref
- [ ] Print button on order admin and dashboard

### 3.3 Staff Email Notifications
- [ ] Email to bakery owner on new paid order
- [ ] Daily digest: sales, pending orders, unread messages
- [ ] SMTP settings via environment variables

### 3.4 Bulk Product Import and Export
- [ ] CSV export of full catalog
- [ ] CSV import: create or update products by name/slug
- [ ] Image handling documented for import

### 3.5 Order Workflow Extensions
- [ ] out_for_delivery status
- [ ] Estimated delivery time field
- [ ] Courier / tracking note field

---

## Phase 4 - Technical Debt and Hardening

### 4.1 Production Database
- [ ] PostgreSQL settings via env vars, SQLite stays for dev
- [ ] Migration runbook documented

### 4.2 Media Storage
- [ ] S3-compatible storage (Arvan Cloud or MinIO) via django-storages
- [ ] Env based credentials

### 4.3 Caching
- [ ] Cache homepage and menu queries, invalidate on product save
- [ ] Redis for sessions and cache in production

### 4.4 Background Tasks
- [ ] Task queue (django-q2 or Celery) for SMS, email, reports
- [ ] Scheduled job for expiring stale pending orders

### 4.5 API Layer
- [ ] Django REST Framework
- [ ] Read endpoints: products, categories, dietary tags
- [ ] Authenticated endpoints: profile, order history
- [ ] Token auth for future mobile app

### 4.6 Logging and Monitoring
- [ ] Structured logging config
- [ ] Sentry error tracking
- [ ] Uptime check on homepage and payment return

### 4.7 CI
- [ ] GitHub Actions: run `manage.py check` and `manage.py test` on push
- [ ] Migration consistency check
- [ ] Test coverage report

---

## Phase 5 - Growth Features

### 5.1 Content Pages
- [ ] Simple page model for bakery stories and announcements
- [ ] SEO meta title and description per page

### 5.2 Multi-language
- [ ] English locale alongside Persian
- [ ] Translated templates and product content strategy

### 5.3 Loyalty Program
- [ ] Points earned per paid order
- [ ] Points redeemable as discount at checkout
- [ ] Points balance shown in profile

### 5.4 Telegram Bot
- [ ] New order notification to staff group
- [ ] Customer order status lookup by order number

### 5.5 PWA
- [ ] manifest.json and service worker
- [ ] Offline menu caching
- [ ] Add to home screen prompt

---

## Progress Log

| Date | Phase | Item | Note |
|------|-------|------|------|
| 2026-09-30 | - | Roadmap created | Baseline: MVP with catalog, cart, Zarinpal, OTP login, dashboard |
| 2026-09-30 | UI | Typography & Design System | Added Estedad display font, refined terracotta/stone palette, rounded cards/buttons, tightened spacing |
