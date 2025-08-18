from djalthingi.api import api
from django.contrib import admin
from django.urls import include
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("customsignup.urls")),
    path("terms/", include("termsandconditions.urls")),
    path("api/", api.urls),
    path("althingi/", include("djalthingi.urls")),
    path("", include("core.urls")),
]
