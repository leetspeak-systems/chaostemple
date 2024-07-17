from django.core.management.base import BaseCommand

from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from djalthingi.exceptions import DataIntegrityException

from core.models import Issue

from dossier.models import Dossier


class Command(BaseCommand):
    help = "Utility command for safely cleaning up duplicate dossiers in reviews. May be necessary when an insane amount of reviews is delivered, which should be rare."

    def add_arguments(self, parser):
        parser.add_argument("issue_num", nargs=1, type=int)

    def handle(self, *args, **options):
        issue_num = options["issue_num"][0]

        issue = Issue.objects.get(
            issue_num=issue_num,
            issue_group="A",
            parliament__parliament_num=CURRENT_PARLIAMENT_NUM,
        )

        dossiers = (
            issue.dossiers.select_related("review", "user")
            .exclude(review=None)
            .order_by("review__log_num", "user__username")
        )

        kill_list = []

        last_dossier = None
        for dossier in dossiers:
            # First iteration cannot be a duplicate.
            if last_dossier is None:
                last_dossier = dossier
                continue

            is_duplicate = all(
                [
                    last_dossier.review.log_num == dossier.review.log_num,
                    last_dossier.user_id == dossier.user_id,
                ]
            )
            if is_duplicate:
                if dossier.is_useful:
                    print(
                        "USEFUL duplicate dossier found, not deleting: %s, %s"
                        % (dossier.user.username, dossier.review.sender_name)
                    )
                else:
                    print(
                        "Useless duplicate found, marked for deletion: %s, %s"
                        % (dossier.user.username, dossier.review.sender_name)
                    )
                    kill_list.append(dossier)

            last_dossier = dossier

        for dossier in kill_list:
            print(
                "Deleting dossier for %s, %s..."
                % (dossier.user.username, dossier.review.sender_name),
                end="",
                flush=True,
            )
            dossier.delete()
            print("done")
