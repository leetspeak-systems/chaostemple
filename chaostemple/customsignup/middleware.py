from django.core.urlresolvers import reverse
from django.shortcuts import redirect

class EnsureProfileDataMiddleware():
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_anonymous():
            up = request.user.userprofile
            if (up.name == '' or up.initials is None) and view_func.func_name != 'custom_profile_data':
                return redirect(reverse('custom_profile_data'))
