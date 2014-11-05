
from django.core.management.base import BaseCommand

from althingi.utils import update_issues
from althingi.utils import update_issue
from althingi.utils import update_next_sessions
from althingi.utils import update_sessions
from althingi.utils import update_session


class Command(BaseCommand):

    help = 'Updates data'

    def handle(self, *args, **options):
        # update_sessions()
        update_next_sessions()
        # update_session(25, 144)

        # update_issues()
        # update_issue(167, 143)
        # update_issue(71, 143)
        # update_issue(240, 144)
        # update_issue(1, 143)
