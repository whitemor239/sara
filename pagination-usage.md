Django usage (already integrated into profile order history):

    {% load bakery_tags %}
    {% render_pagination orders "profile-orders" %}

Pass a Django Paginator Page object. Query filters remain in links.

React usage inside an existing React + Tailwind build:

    import { Pagination } from "./pagination";
    <Pagination currentPage={6} totalPages={12}
      hrefForPage={(page) => `/account/profile/?page=${page}#profile-orders`} />

Configure font-sans to project Vazirmatn or IRANSans. Component inherits project font.
Django does not execute TSX: native template works without React or Tailwind build.
SVG paths in Django mirror lucide chevrons; React imports lucide-react.
No form controls exist, so iOS input-size override is unnecessary.
Page numbers are not prices; no تومان unit is appended.
