from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'chaostemple.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/logout/$', views.logout, {'next_page': settings.LOGIN_URL}),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^', include('core.urls')),
]
