from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView

from termsandconditions.decorators import terms_required

from customsignup.views import CustomLoginView
from customsignup.views import CustomRegistrationView
from customsignup.views import custom_profile_data


urlpatterns = [
    url(r'^login/$', CustomLoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', auth_views.LogoutView.as_view(), {'next_page': settings.LOGIN_URL}),
    url(r'^register/$', CustomRegistrationView.as_view(), name='registration_register'),
    url(r'^custom-profile-data/$', custom_profile_data, name='custom_profile_data'),
    url(r'^activate/complete/$', terms_required(TemplateView.as_view(template_name='registration/activation_complete.html')), name='registration_activation_complete'),
    url(r'^', include('registration.backends.default.urls')),

    url(r'^password_reset/$', auth_views.PasswordResetView.as_view(), name='password_reset'),
    url(r'^password_reset/done/$', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    url(r'^reset/done/$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
