from django.core.management.base import BaseCommand

from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        try:
            users = (
                User.objects.select_related("userprofile")
                .exclude(userprofile__last_seen=None)
                .order_by("-userprofile__last_seen")
            )

            for user in users:
                print(
                    "%s: %s"
                    % (
                        user.userprofile.last_seen.strftime("%Y-%m-%d %H:%M:%S"),
                        user.username,
                    )
                )

        except KeyboardInterrupt:
            quit(1)
