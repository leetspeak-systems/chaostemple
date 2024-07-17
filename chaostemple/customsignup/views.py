from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.shortcuts import reverse

from registration import signals
from registration.models import RegistrationProfile
from registration.users import UserModel
from registration.views import RegistrationView

from customsignup.forms import CustomAuthenticationForm
from customsignup.forms import CustomProfileDataForm
from customsignup.forms import CustomRegistrationForm

User = UserModel()


class CustomLoginView(LoginView):
    form_class = CustomAuthenticationForm


class CustomRegistrationView(RegistrationView):
    form_class = CustomRegistrationForm

    SEND_ACTIVATION_EMAIL = getattr(settings, "SEND_ACTIVATION_EMAIL", True)
    success_url = "registration_complete"

    registration_profile = RegistrationProfile

    def register(self, form):

        site = get_current_site(self.request)

        data = {
            "username": form.cleaned_data["email"],
            "email": form.cleaned_data["email"],
        }

        new_user_instance = User.objects.create_user(**data)
        new_user_instance.set_password(form.cleaned_data["password2"])

        new_user = self.registration_profile.objects.create_inactive_user(
            new_user=new_user_instance,
            site=site,
            send_email=self.SEND_ACTIVATION_EMAIL,
            request=self.request,
        )
        signals.user_registered.send(
            sender=self.__class__, user=new_user, request=self.request
        )

        return new_user

    def registration_allowed(self):
        return getattr(settings, "REGISTRATION_OPEN", True)


@login_required
def custom_profile_data(request):

    profile = request.user.userprofile

    # If this is a user whose information we can determine automatically, we
    # won't let them choose their own.
    if profile.person:
        raise Http404

    if request.method == "POST":
        form = CustomProfileDataForm(request.POST, request=request)

        if form.is_valid():
            profile.name = form.cleaned_data["name"]
            profile.initials = form.cleaned_data["initials"]
            profile.save()

            return redirect(reverse("user_home"))
    else:
        form = CustomProfileDataForm(
            initial={
                "name": profile.name,
                "initials": profile.initials,
            },
            request=request,
        )

    ctx = {
        "form": form,
        "userprofile": profile,
    }
    return render(request, "registration/custom_profile_data.html", ctx)
