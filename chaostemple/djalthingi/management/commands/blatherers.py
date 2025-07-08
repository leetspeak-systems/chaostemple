import operator
from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from djalthingi.stats import stats_speeches
from djalthingi.utils import human_readable_seconds
from django.core.management.base import BaseCommand
from tabulate import tabulate


class Command(BaseCommand):

    help = "Analyzes and displays speech statistics by MPs and parties."

    def print_help(self):
        print("Usage: python manage.py blatherers")
        print()

    def error(self, msg, show_help=True):
        print("Error: %s" % msg)
        print()
        if show_help:
            self.print_help()
        quit(2)

    def add_arguments(self, parser):
        parser.add_argument("-t", "--today", nargs="*", help="Show only today")
        parser.add_argument(
            "-u",
            "--current-issue",
            nargs="*",
            help="Only current issue (automatically skips speaker)",
        )
        parser.add_argument(
            "-i",
            "--issue",
            nargs="*",
            help="Only given issue_num (automatically skips speaker)",
        )
        parser.add_argument(
            "-s", "--skip-speaker", nargs="*", help="Skip speeches by speaker"
        )
        parser.add_argument(
            "-m",
            "--only-main",
            nargs="*",
            help="Only include main speeches, not f.e. responses",
        )
        parser.add_argument(
            "-e",
            "--iteration",
            nargs="*",
            help="Only speeches held in given iteration (1, 2, 3, F, S)",
        )
        parser.add_argument("-c", "--sort-by-count", nargs="*", help="Sort by count")

    def handle(self, *args, **options):
        try:
            mp_rows, party_rows = stats_speeches(CURRENT_PARLIAMENT_NUM, options)

            # Massage the data for printing to screen.
            for mp_row in mp_rows:
                mp_row[3] = human_readable_seconds(mp_row[3])
            for party_row in party_rows:
                party_row[1] = human_readable_seconds(party_row[1])

            # Sort rows by speech count if requested.
            if options["sort_by_count"] is not None:
                mp_rows = sorted(mp_rows, key=operator.itemgetter(4))
                party_rows = sorted(party_rows, key=operator.itemgetter(2))

            print(tabulate(
                mp_rows,
                headers=[
                    "Nr.",
                    "Nafn",
                    "Flokkur",
                    "Tími",
                    "Fj.",
                    "Tími %",
                    "Fj. %",
                ],
            ))

            print(tabulate(
                party_rows,
                headers=[
                    "Flokkur",
                    "Tími",
                    "Fjöldi",
                    "Tími %",
                    "Fjöldi %",
                    "Þingm.",
                    "Þingm. %",
                ],
            ))

        except KeyboardInterrupt:
            quit(1)
