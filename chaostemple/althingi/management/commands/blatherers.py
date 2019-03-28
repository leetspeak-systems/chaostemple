import operator

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Parliament
from althingi.models import Person

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models import Sum

from tabulate import tabulate

# Turns seconds into a human-readable string representing length of time.
def human_readable(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    hr = '%d days, %d:%02d:%02d' % (days, hours, minutes, seconds)
    return hr

class Command(BaseCommand):

    help = 'Analyzes and displays speech statistics by MPs and parties.'

    def print_help(self):
        print('Usage: python manage.py blatherers')
        print()

    def error(self, msg, show_help=True):
        print('Error: %s' % msg)
        print()
        if show_help:
            self.print_help()
        quit(2)

    def handle(self, *args, **options):
        try:

            parliament_num = CURRENT_PARLIAMENT_NUM

            date_from = None
            date_to = None

            parliament = Parliament.objects.get(parliament_num=parliament_num)

            persons = Person.objects.filter(
                #speeches__president=False,
                speeches__session__parliament=parliament
            ).annotate(
                seconds=Sum('speeches__seconds'),
                count=Count('speeches')
            ).prefetch_latest_seats(parliament).prefetch_latest_minister_seats(parliament)

            party_seconds = {'': 0}
            party_counts = {'': 0}
            for party in parliament.parties.all():
                party_seconds[party.name] = 0
                party_counts[party.name] = 0

            rows = []
            for i, person in enumerate(persons):
                if date_from and date_to:
                    speeches = person.speeches.filter(
                        session__parliament__parliament_num=parliament_num,
                        timing_start__gte=date_from,
                        timing_end__lte=date_to
                    )

                    count = len(speeches)
                    seconds = sum([s.seconds for s in speeches])

                else:
                    count = person.count
                    seconds = person.seconds

                hr = human_readable(seconds)
                try:
                    party = person.last_seat[0].party.name
                except IndexError:
                    try:
                        party = person.last_minister_seats[0].party.name
                    except IndexError:
                        party = ''

                party_seconds[party] += seconds
                party_counts[party] += count

                rows.append([None, person, party, seconds, count])

            rows = sorted(rows, key=operator.itemgetter(3))
            row_count = len(rows)
            for i, row in enumerate(rows):
                row[0] = row_count - i # Set the seat
                row[3] = human_readable(row[3])

            print(tabulate(rows, headers=['Sæti', 'Nafn', 'Flokkur', 'Tími', 'Fjöldi']))

            ordered = sorted(party_seconds.items(), key=operator.itemgetter(1))
            rows = []
            for party, seconds in ordered:
                rows.append([party, human_readable(seconds), party_counts[party]])

            print(tabulate(rows, headers=['Flokkur', 'Tími', 'Fjöldi']))

        except KeyboardInterrupt:
            quit(1)
