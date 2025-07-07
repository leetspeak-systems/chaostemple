import operator
from datetime import timedelta
from djalthingi.models import Parliament
from djalthingi.models import Person
from djalthingi.models import Speech
from django.db.models import Count
from django.db.models import Sum
from django.utils import timezone


def stats_speeches(parliament_num: int, options):

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

    mp_rows = []
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

        mp_rows.append([None, person, party, seconds, count])

    # Calculate ratios, which must be calculated after we've gathered
    # total_seconds and total_count in the previous iteration.
    for row in mp_rows:
        row.append(round(100 * float(row[3]) / total_seconds, 2))
        row.append(round(100 * float(row[4]) / total_count, 2))

    # Sort rows by speech count if requested.
    if options["sort_by_count"] is not None:
        mp_rows = sorted(mp_rows, key=operator.itemgetter(4))
    else:
        mp_rows = sorted(mp_rows, key=operator.itemgetter(3))

    row_count = len(mp_rows)
    for i, row in enumerate(mp_rows):
        row[0] = row_count - i  # Set the seat

    party_rows = []
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

        party_rows.append(
            [
                party,
                seconds,
                party_counts[party],
                ratio_seconds,
                ratio_count,
                mp_count,
                ratio_mp_count,
            ]
        )

    # Sort party rows by speech count if requested.
    if options["sort_by_count"] is not None:
        party_rows = sorted(party_rows, key=operator.itemgetter(2))
    else:
        party_rows = sorted(party_rows, key=operator.itemgetter(1))

    return mp_rows, party_rows
