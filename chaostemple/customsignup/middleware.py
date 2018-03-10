from django.urls import reverse
from django.shortcuts import redirect

class EnsureProfileDataMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_anonymous:
            up = request.user.userprofile
            view_name = request.resolver_match.view_name
            if (up.name == '' or up.initials is None) and view_name != 'custom_profile_data':
                return redirect(reverse('custom_profile_data'))
