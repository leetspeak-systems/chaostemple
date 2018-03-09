from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'chaostemple.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('customsignup.urls')),
    url(r'^terms/', include('termsandconditions.urls')),
    url(r'^', include('core.urls')),
]


# Add Django Debug Toolbar urls patterns if it is installed and debug is enabled
if settings.DEBUG and 'debug_toolbar.apps.DebugToolbarConfig' in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
