from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from customsignup.views import CustomLoginView
from customsignup.views import CustomRegistrationView
from customsignup.views import custom_profile_data


urlpatterns = [
    url(r'^login/$', CustomLoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', auth_views.logout, {'next_page': settings.LOGIN_URL}),
    url(r'^register/$', CustomRegistrationView.as_view(), name='registration_register'),
    url(r'^custom-profile-data/$', custom_profile_data, name='custom_profile_data'),
    url(r'^', include('registration.backends.default.urls')),

    url(r'^password_reset/$', auth_views.password_reset, name='password_reset'),
    url(r'^password_reset/done/$', auth_views.password_reset_done, name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/done/$', auth_views.password_reset_complete, name='password_reset_complete'),
]
