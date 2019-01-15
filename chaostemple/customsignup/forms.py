from collections import OrderedDict

from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UsernameField
from django.utils.translation import ugettext_lazy as _

from core.models import UserProfile

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Seat

class CustomProfileDataForm(forms.Form):
    name = forms.CharField(label=_('Name'), max_length=200)
    initials = forms.CharField(label=_('Initials'), max_length=10)

    # Overriding constructor because we need the request for sanity checking.
    def __init__(self, *args, request, **kwargs):
        self.request = request
        super(CustomProfileDataForm, self).__init__(*args, **kwargs)

    def clean_initials(self):
        clean_initials = self.cleaned_data['initials']

        taken_by_person = Seat.objects.filter(
            name_abbreviation=clean_initials,
            parliament__parliament_num=CURRENT_PARLIAMENT_NUM
        ).count() > 0

        taken_by_user = UserProfile.objects.filter(
            initials=clean_initials
        ).exclude(
            user_id=self.request.user.id
        ).count() > 0

        if taken_by_person:
            raise forms.ValidationError(_('Initials already in use by an MP or minister.'))
        elif taken_by_user:
            raise forms.ValidationError(_('Initials already taken by a different user.'))

        return clean_initials


class CustomAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        label=_('Email'),
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': True}),
    )


class CustomRegistrationForm(forms.Form):

    email = forms.EmailField(label=_('Email'))
    password1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_('Password confirmation'),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_('Enter the same password as before, for verification.'),
    )

    def clean_email(self):
        clean_email = self.cleaned_data['email']

        if hasattr(settings, 'CUSTOM_SIGNUP_DOMAINS'):
            allowed_domains = settings.CUSTOM_SIGNUP_DOMAINS
            domain = clean_email.split('@')[1]
            if domain not in allowed_domains:
                raise forms.ValidationError(_('Email address not allowed.'))

        if User.objects.filter(email__iexact=clean_email):
            raise forms.ValidationError(_('Email address already in use.'))

        return clean_email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) == 0:
            raise forms.ValidationError(_('Password must be supplied.'))
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 != password2:
            raise forms.ValidationError(
                _("The two password fields didn't match."),
                code='password_mismatch',
            )
        return password2

    class Meta:
        model = User
        fields = ('email',)
