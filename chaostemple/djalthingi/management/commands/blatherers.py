import operator

from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from djalthingi.models import Parliament
from djalthingi.models import Person
from djalthingi.models import Speech

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models import Sum
from django.utils import timezone

from tabulate import tabulate


# Turns seconds into a human-readable string representing length of time.
def human_readable(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    hr = "%d days, %02d:%02d:%02d" % (days, hours, minutes, seconds)
    return hr


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

            parliament_num = CURRENT_PARLIAMENT_NUM

            if options["today"] is not None:
                today = timezone.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                date_from = today
                date_to = today + timedelta(days=1)
            else:
                date_from = None
                date_to = None

            parliament = Parliament.objects.get(parliament_num=parliament_num)

            # Base conditions for person lookup.
            # This must be constructed and then manipulated according to
            # options because we have to issue a single filter.
            q_conditions = {
                "speeches__session__parliament": parliament,
            }

            # Process option for limiting to current issue.
            if options["current_issue"] is not None:
                last_issue = Speech.objects.last().issue
                q_conditions["speeches__issue"] = last_issue

                # Option implies skipping speaker.
                options["skip_speaker"] = True

            # Process option for limiting to given issue.
            if options["issue"] is not None:
                q_conditions["speeches__issue__issue_num"] = options["issue"].pop()
                q_conditions["speeches__issue__issue_group"] = "A"

                # Option implies skipping speaker.
                options["skip_speaker"] = True

            # Process option for skipping speaker.
            if options["skip_speaker"] is not None:
                q_conditions["speeches__president"] = False

            # Process option for only selecting main speeches.
            if options["only_main"] is not None:
                q_conditions["speeches__speech_type"] = "ræða"

            # Process option for selecting speeches by iteration.
            if options["iteration"] is not None:
                q_conditions["speeches__iteration"] = options["iteration"].pop()

            persons = Person.objects.filter(**q_conditions)

            # Add annotations and get more data.
            persons = (
                persons.annotate(
                    seconds=Sum("speeches__seconds"), count=Count("speeches")
                )
                .prefetch_latest_seats(parliament)
                .prefetch_latest_minister_seats(parliament)
            )

            total_seconds = 0
            total_count = 0
            party_seconds = {"": 0}
            party_counts = {"": 0}
            party_mp_counts = {}
            for party in parliament.parties.annotate_mp_counts(parliament):
                party_seconds[party.abbreviation_long] = 0
                party_counts[party.abbreviation_long] = 0
                party_mp_counts[party.abbreviation_long] = party.mp_count

            rows = []
            for i, person in enumerate(persons):
                if date_from and date_to:
                    speeches = person.speeches.filter(
                        session__parliament__parliament_num=parliament_num,
                        timing_start__gte=date_from,
                        timing_end__lte=date_to,
                    )

                    count = len(speeches)
                    seconds = sum([s.seconds for s in speeches])

                else:
                    count = person.count
                    seconds = person.seconds

                hr = human_readable(seconds)
                try:
                    party = person.last_seat[0].party.abbreviation_long
                except IndexError:
                    try:
                        party = person.last_minister_seats[0].party.abbreviation_long
                    except IndexError:
                        party = ""

                party_seconds[party] += seconds
                party_counts[party] += count

                total_seconds += seconds
                total_count += count

                rows.append([None, person, party, seconds, count])

            # Calculate ratios, which must be calculated after we've gathered
            # total_seconds and total_count in the previous iteration.
            for row in rows:
                row.append(round(100 * float(row[3]) / total_seconds, 2))
                row.append(round(100 * float(row[4]) / total_count, 2))

            # Sort rows by speech count if requested.
            if options["sort_by_count"] is not None:
                rows = sorted(rows, key=operator.itemgetter(4))
            else:
                rows = sorted(rows, key=operator.itemgetter(3))

            row_count = len(rows)
            for i, row in enumerate(rows):
                row[0] = row_count - i  # Set the seat
                row[3] = human_readable(row[3])

            print(
                tabulate(
                    rows,
                    headers=[
                        "Nr.",
                        "Nafn",
                        "Flokkur",
                        "Tími",
                        "Fj.",
                        "Tími %",
                        "Fj. %",
                    ],
                )
            )

            rows = []
            for party, seconds in party_seconds.items():
                count = party_counts[party]

                if total_seconds == 0 or total_count == 0:
                    ratio_seconds = 0
                    ratio_count = 0
                else:
                    ratio_seconds = round(100 * float(seconds) / total_seconds, 2)
                    ratio_count = round(100 * float(count) / total_count, 2)

                if party in party_mp_counts:
                    mp_count = party_mp_counts[party]
                    ratio_mp_count = round(100 * float(mp_count) / 63, 2)
                else:
                    mp_count = None
                    ratio_mp_count = None

                rows.append(
                    [
                        party,
                        human_readable(seconds),
                        party_counts[party],
                        ratio_seconds,
                        ratio_count,
                        mp_count,
                        ratio_mp_count,
                    ]
                )

            # Sort party rows by speech count if requested.
            if options["sort_by_count"] is not None:
                rows = sorted(rows, key=operator.itemgetter(2))
            else:
                rows = sorted(rows, key=operator.itemgetter(1))

            print(
                tabulate(
                    rows,
                    headers=[
                        "Flokkur",
                        "Tími",
                        "Fjöldi",
                        "Tími %",
                        "Fjöldi %",
                        "Þingm.",
                        "Þingm. %",
                    ],
                )
            )

        except KeyboardInterrupt:
            quit(1)
