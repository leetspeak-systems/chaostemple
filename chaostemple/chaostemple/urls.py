from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views
from django.urls import include
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('customsignup.urls')),
    path('terms/', include('termsandconditions.urls')),
    path('althingi/', include('djalthingi.urls')),
    path('', include('core.urls')),
]


# Add Django Debug Toolbar urls patterns if it is installed and debug is enabled
if settings.DEBUG and 'debug_toolbar.apps.DebugToolbarConfig' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
