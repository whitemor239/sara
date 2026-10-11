from django.contrib.admin.apps import AdminConfig


class TastyTumAdminConfig(AdminConfig):
    default_site = "tastytum.admin_site.TastyTumAdminSite"
