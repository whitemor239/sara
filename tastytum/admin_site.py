from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse

from bakery.dashboard import dashboard_context


class TastyTumAdminSite(AdminSite):
    site_header = "نارون | مدیریت"
    site_title = "مدیریت نارون"
    index_title = "نمای کلی فروشگاه"

    def index(self, request, extra_context=None):
        context = {
            **self.each_context(request),
            **dashboard_context(request),
            **(extra_context or {}),
        }
        return TemplateResponse(request, "bakery/dashboard.html", context)
