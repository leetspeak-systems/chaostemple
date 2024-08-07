import operator
import os
import requests
from functools import reduce

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Case
from django.db.models import Count
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import When
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.defaultfilters import capfirst
from django.utils import dateparse
from django.utils import timezone
from django.utils.translation import gettext as _

from chaostemple.settings import FEATURES
from chaostemple.settings import MEANING_OF_RECENT

from core.models import Access
from core.models import AccessUtilities
from core.models import Document
from core.models import Issue
from core.models import IssueMonitor
from core.models import IssueUtilities
from core.models import MembershipRequest
from core.models import Review
from core.models import Subscription
from core.utils import complete_person

from dossier.models import Dossier
from dossier.models import DossierStatistic

from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from djalthingi.models import Category
from djalthingi.models import CategoryGroup
from djalthingi.models import Committee
from djalthingi.models import CommitteeAgenda
from djalthingi.models import CommitteeSeat
from djalthingi.models import Parliament
from djalthingi.models import Party
from djalthingi.models import Person
from djalthingi.models import Session


def home(request):
    return redirect(reverse("day"))


def day(request, input_date=None):

    # Redirect to today if no date specified
    if input_date is None:
        now = timezone.now()
        return redirect(reverse("day", args=(now.strftime("%Y-%m-%d"),)))

    # Make sure that the date makes sense and otherwise result in a "Page not found" error
    try:
        requested_date = timezone.make_aware(
            dateparse.parse_datetime("%s 00:00:00" % input_date)
        )
    except ValueError:
        raise Http404

    requested_yesterday = requested_date - timezone.timedelta(days=1)
    requested_tomorrow = requested_date + timezone.timedelta(days=1)

    # Contains issues that should be populated with issue data. Issues will
    # be collected through iterations of committees and sessions agendas and
    # then populated, all at once.
    issues_to_populate = []

    # Get issues of specified day
    sessions = (
        Session.objects.select_related("parliament")
        .prefetch_related("session_agenda_items")
        .on_date(requested_date)
    )
    for session in sessions:
        session.session_agenda_items_loaded = (
            session.session_agenda_items.select_related(
                "issue__to_committee", "issue__parliament"
            ).prefetch_related(
                "issue__proposers__person", "issue__proposers__committee"
            )
        )

        # Mark issues for populating data.
        issues_to_populate += [i.issue for i in session.session_agenda_items_loaded]

    # Get committee agendas of specified day
    committee_agendas = (
        CommitteeAgenda.objects.select_related("committee", "parliament")
        .prefetch_related("committee_agenda_items")
        .on_date(requested_date)
    )
    for committee_agenda in committee_agendas:
        committee_agenda.committee_agenda_items_loaded = (
            committee_agenda.committee_agenda_items.select_related(
                "issue__to_committee", "issue__parliament"
            ).prefetch_related("issue__proposers__person")
        )

        # Mark issues for populating data.
        issues_to_populate += [
            a.issue for a in committee_agenda.committee_agenda_items_loaded
        ]

    # Populate collected issues with data.
    IssueUtilities.populate_issue_data(issues_to_populate)

    ctx = {
        "requested_yesterday": requested_yesterday,
        "requested_date": requested_date,
        "requested_tomorrow": requested_tomorrow,
        "sessions": sessions,
        "committee_agendas": committee_agendas,
    }
    return render(request, "core/day.html", ctx)


def upcoming(request):

    next_sessions = request.extravars["next_sessions"]
    next_committee_agendas = request.extravars["next_committee_agendas"]

    # Get issues that are upcoming in sessions
    # They are prepended with "garbled_" because we know in advance that they may contain duplicates.
    garbled_session_issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person", "session_agenda_items__session")
        .filter(issue_group="A", session_agenda_items__session__in=next_sessions)
        .order_by(
            "session_agenda_items__session__session_num", "session_agenda_items__order"
        )
        .distinct()
    )

    # Get issues that are upcoming in committee agendas
    # They are prepended with "garbled_" because we know in advance that they may contain duplicates.
    garbled_committee_issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related(
            "proposers__person",
            "committee_agenda_items__committee_agenda",
        )
        .filter(committee_agenda_items__committee_agenda__in=next_committee_agendas)
        .order_by("committee_agenda_items__committee_agenda__timing_start_planned")
        .distinct()
    )

    # Remove duplicates which cannot be excluded by database query, since same issue may pop up at two different times.
    session_issues = []
    for issue in garbled_session_issues:
        if issue not in session_issues:
            session_issues.append(issue)
    committee_issues = []
    for issue in garbled_committee_issues:
        if issue not in committee_issues:
            committee_issues.append(issue)

    # Get the relevant dossier statistics
    IssueUtilities.populate_issue_data(session_issues + committee_issues)

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get upcoming sessions for each issue (can this be optimized?)
    for issue in session_issues:
        issue.upcoming_sessions = (
            Session.objects.select_related("parliament")
            .filter(
                session_agenda_items__issue_id=issue.id, timing_start_planned__gte=today
            )
            .distinct()
        )

    # Get upcoming committee agendas for each issue (can this be optimized?)
    for issue in committee_issues:
        issue.upcoming_committee_agendas = (
            CommitteeAgenda.objects.select_related("parliament", "committee")
            .filter(
                committee_agenda_items__issue_id=issue.id,
                timing_start_planned__gte=today,
            )
            .distinct()
        )

    ctx = {
        "session_issues": session_issues,
        "committee_issues": committee_issues,
    }
    return render(request, "core/upcoming.html", ctx)


def parliaments(request, parliament_num=None):
    """
    Note: The parliament_num variable is actually handled by middleware, so we
    don't need to concern ourselves with it here. It is only an optional
    parameter to this function so that we can use the same view for both
    "parliaments" and "parliament number something" in the urlconf, since
    their view code is the same.
    """

    parliaments = Parliament.objects.exclude(last_full_update=None)

    ctx = {
        "parliaments": parliaments,
    }
    return render(request, "core/parliaments.html", ctx)


def parliament_documents_new(request, parliament_num):
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    a_while_ago = today - MEANING_OF_RECENT
    documents = (
        Document.objects.select_related("issue__parliament", "issue__to_committee")
        .prefetch_related("issue__proposers__person")
        .filter(time_published__gte=a_while_ago)
        .order_by("-time_published")
    )

    IssueUtilities.populate_issue_data([d.issue for d in documents])

    ctx = {"documents": documents}

    return render(request, "core/parliament_documents_new.html", ctx)


def parliament_issues(request, parliament_num):

    issues = (
        Issue.objects.select_related("parliament")
        .prefetch_related("proposers__person", "proposers__committee", "to_committee")
        .filter(
            issue_group="A",
            parliament__parliament_num=parliament_num,
            document_count__gt=0,
        )
    )

    issue_types = set(
        issues.filter(issue_group="A").values_list("issue_type", flat=True).distinct()
    )

    issue_type_labels = []
    for issue_type, issue_type_label in Issue.ISSUE_TYPES:
        if issue_type in issue_types:
            issue_type_labels += [issue_type_label]

    IssueUtilities.populate_issue_data(issues)

    ctx = {
        "issues": issues,
        "issue_type_labels": issue_type_labels,
    }
    return render(request, "core/parliament_issues.html", ctx)


def parliament_issue(request, parliament_num, issue_num):

    issue = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("categories__group")
        .get(
            parliament__parliament_num=parliament_num,
            issue_group="A",
            issue_num=issue_num,
        )
    )

    visible_dossiers = Dossier.objects.by_user(request.user)

    documents = (
        Document.objects.prefetch_related(
            Prefetch("dossiers", queryset=visible_dossiers),
            "dossiers__user__userprofile",
            "proposers__person",
            "proposers__committee",
        )
        .annotate_seen(request.user)
        .filter(issue=issue)
    )

    reviews = (
        Review.objects.prefetch_related(
            Prefetch("dossiers", queryset=visible_dossiers),
            "dossiers__user__userprofile",
            "committee",
        )
        .select_related("issue__parliament")
        .annotate_seen(request.user)
        .filter(issue=issue)
    )

    issue_sessions = Session.objects.select_related("parliament").filter(
        session_agenda_items__issue_id=issue.id
    )
    issue_committee_agendas = CommitteeAgenda.objects.select_related(
        "parliament", "committee"
    ).filter(committee_agenda_items__issue_id=issue.id)

    IssueUtilities.populate_issue_data([issue])

    # Construct the page title.
    page_title = "%d. %s: %s" % (issue.issue_num, _("issue"), capfirst(issue.name))

    ctx = {
        "page_title": page_title,
        "issue": issue,
        "issue_sessions": issue_sessions,
        "issue_committee_agendas": issue_committee_agendas,
        "documents": documents,
        "reviews": reviews,
        "attentionstates": Dossier.ATTENTION_STATES,
        "knowledgestates": Dossier.KNOWLEDGE_STATES,
        "supportstates": Dossier.SUPPORT_STATES,
        "proposalstates": Dossier.PROPOSAL_STATES,
    }
    return render(request, "core/parliament_issue.html", ctx)


def parliament_categories(request, parliament_num):

    category_groups = CategoryGroup.objects.prefetch_related("categories")

    subscriptions = Subscription.objects.filter(
        user_id=request.user.id, sub_type="category"
    )

    ctx = {
        "category_groups": category_groups,
        "subscriptions": subscriptions,
    }
    return render(request, "core/parliament_categories.html", ctx)


def parliament_category(request, parliament_num, category_slug, view=None):

    category_groups = CategoryGroup.objects.prefetch_related("categories")
    category = Category.objects.get(slug=category_slug)

    issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person")
        .filter(
            parliament__parliament_num=parliament_num,
            issue_group="A",
            categories=category,
        )
    )

    IssueUtilities.populate_issue_data(issues)

    subscriptions = Subscription.objects.filter(
        user_id=request.user.id, sub_type="category"
    )

    ctx = {
        "category_groups": category_groups,
        "category": category,
        "issues": issues,
        "subscriptions": subscriptions,
    }

    if view == "issues":
        # This is the expanded view, with a more detailed focus on the issues.
        # It takes exactly the same information so we decided to use the same
        # function here. If these two pages begin to differ in other ways than
        # mere presentation, then this function should be split in two.
        return render(request, "core/parliament_category_issues.html", ctx)
    else:
        return render(request, "core/parliament_categories.html", ctx)


def parliament_sessions(request, parliament_num):

    sessions = Session.objects.filter(
        parliament__parliament_num=parliament_num
    ).annotate(session_agenda_item_count=Count("session_agenda_items"))

    ctx = {"sessions": sessions}
    return render(request, "core/parliament_sessions.html", ctx)


def parliament_session(request, parliament_num, session_num):

    session = get_object_or_404(
        Session, parliament__parliament_num=parliament_num, session_num=session_num
    )
    session_agenda_items = (
        session.session_agenda_items.select_related(
            "issue__parliament", "issue__to_committee"
        )
        .prefetch_related("issue__proposers__person", "issue__proposers__committee")
        .all()
    )

    IssueUtilities.populate_issue_data([i.issue for i in session_agenda_items])

    ctx = {
        "session": session,
        "session_agenda_items": session_agenda_items,
    }
    return render(request, "core/parliament_session.html", ctx)


def parliament_committees(request, parliament_num):

    committees = Committee.objects.filter(
        parliaments__parliament_num=parliament_num, is_standing=True
    ).annotate(
        agenda_count=Count(
            Case(
                When(
                    committee_agendas__parliament__parliament_num=parliament_num, then=1
                )
            )
        )
    )

    subscriptions = None
    current_committees = None
    if request.user.is_authenticated:
        subscriptions = Subscription.objects.filter(
            user=request.user, committee__in=committees
        )

        current_committees = Committee.objects.currently_with_person(
            request.user.userprofile.person
        )

    ctx = {
        "committees": committees,
        "current_committees": current_committees,
        "subscriptions": subscriptions,
    }
    return render(request, "core/parliament_committees.html", ctx)


def parliament_committee(request, parliament_num, committee_id):

    committee = Committee.objects.get(id=committee_id)
    agendas = committee.committee_agendas.filter(
        parliament__parliament_num=parliament_num
    ).annotate(item_count=Count("committee_agenda_items"))
    issues = (
        committee.issues.prefetch_related("proposers__person")
        .select_related("parliament")
        .filter(parliament__parliament_num=parliament_num)
    )

    parliament = request.extravars["parliament"]
    if parliament.timing_end:
        timing = parliament.timing_end - timezone.timedelta(minutes=1)
    else:
        timing = timezone.now()

    persons = (
        Person.objects.filter(
            committee_seats__committee_id=committee.id,
            committee_seats__parliament__parliament_num=parliament_num,
        )
        .prefetch_latest_committee_seats(committee, parliament)
        .prefetch_latest_seats(parliament, "party")
        .order_by("committee_seats__order")
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {
        "committee": committee,
        "agendas": agendas,
        "issues": issues,
        "persons": persons,
    }
    return render(request, "core/parliament_committee.html", ctx)


def parliament_committee_issues(request, parliament_num, committee_id):

    committee = Committee.objects.get(id=committee_id)
    issues = (
        committee.issues.prefetch_related("proposers__person")
        .select_related("parliament")
        .filter(parliament__parliament_num=parliament_num)
        .order_by("-issue_num")
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {
        "committee": committee,
        "issues": issues,
    }
    return render(request, "core/parliament_committee_issues.html", ctx)


def parliament_committee_agenda(request, parliament_num, committee_id, agenda_id):

    committee = Committee.objects.get(id=committee_id)
    committee_agenda = committee.committee_agendas.get(id=agenda_id)
    committee_agenda_items = (
        committee_agenda.committee_agenda_items.select_related("issue__parliament")
        .prefetch_related("issue__proposers__person", "issue__proposers__committee")
        .all()
    )

    IssueUtilities.populate_issue_data([i.issue for i in committee_agenda_items])

    ctx = {
        "committee": committee,
        "committee_agenda": committee_agenda,
        "committee_agenda_items": committee_agenda_items,
    }
    return render(request, "core/parliament_committee_agenda.html", ctx)


def parliament_parties(request, parliament_num):

    parliament = request.extravars["parliament"]

    parties = Party.objects.filter(
        Q(parliament_num_last__gte=parliament_num) | Q(parliament_num_last=None),
        parliament_num_first__lte=parliament_num,
    ).annotate_mp_counts(parliament)

    ctx = {
        "parties": parties,
    }
    return render(request, "core/parliament_parties.html", ctx)


def parliament_party(request, parliament_num, party_slug):

    parliament = request.extravars["parliament"]

    party = get_object_or_404(Party, slug=party_slug)

    persons = (
        Person.objects.prefetch_latest_seats(
            parliament, "party", "constituency", "parliament"
        )
        .prefetch_latest_minister_seats(parliament, "minister", "party")
        .prefetch_latest_president_seats(parliament, "president")
        .filter(
            Q(
                seats__parliament__parliament_num=parliament_num,
                seats__party__slug=party_slug,
            )
            | Q(
                minister_seats__parliament__parliament_num=parliament_num,
                minister_seats__party__slug=party_slug,
            )
        )
        .distinct()
    )

    issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person")
        .from_party(party)
        .filter(parliament_id=parliament.id, issue_group="A")
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {
        "party": party,
        "persons": persons,
        "issues": issues,
    }
    return render(request, "core/parliament_party.html", ctx)


def parliament_party_issues(request, parliament_num, party_slug):

    parliament = request.extravars["parliament"]

    party = get_object_or_404(Party, slug=party_slug)

    issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person")
        .from_party(party)
        .filter(parliament_id=parliament.id, issue_group="A")
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {
        "party": party,
        "issues": issues,
    }
    return render(request, "core/parliament_party_issues.html", ctx)


def parliament_persons(request, parliament_num, party_slug=None):

    parliament = request.extravars["parliament"]
    parties = Party.objects.filter(
        Q(parliament_num_last__gte=parliament_num) | Q(parliament_num_last=None),
        parliament_num_first__lte=parliament_num,
    )

    if party_slug:
        party = get_object_or_404(Party, slug=party_slug)

        q_persons = Q(
            seats__parliament__parliament_num=parliament_num,
            seats__party__slug=party_slug,
        ) | Q(
            minister_seats__parliament__parliament_num=parliament_num,
            minister_seats__party__slug=party_slug,
        )
    else:
        party = None
        q_persons = Q(seats__parliament__parliament_num=parliament_num) | Q(
            minister_seats__parliament__parliament_num=parliament_num
        )

    persons = (
        Person.objects.prefetch_latest_seats(
            parliament, "party", "constituency", "parliament"
        )
        .prefetch_latest_minister_seats(parliament, "minister", "party")
        .prefetch_latest_president_seats(parliament, "president")
        .filter(q_persons)
        .distinct()
    )

    ctx = {
        "parliament": parliament,
        "persons": persons,
        "parties": parties,
        "party": party,
    }
    return render(request, "core/parliament_persons.html", ctx)


def parliament_issue_overview(request, parliament_num, slug_type, slug, subslug=None):

    if slug_type == "person":
        if subslug is None:
            return complete_person(request, slug)

        persons = Person.objects.filter(slug=slug, subslug=subslug)
        party = None

    elif slug_type == "party":

        persons = Person.objects.filter(
            seats__party__slug=slug, seats__parliament__parliament_num=parliament_num
        ).distinct()
        party = Party.objects.get(slug=slug)

    else:
        raise Http404

    # Get issues either proposed or rapporteured by persons, annotating the
    # person_id of the rapporteur and proposer, so that we can later figure
    # out which issue belongs to which person and for what reason, with only a
    # single query for issues.
    issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person")
        .filter(
            Q(rapporteurs__person__in=persons) | Q(proposers__person__in=persons),
            proposers__order=1,
            parliament__parliament_num=parliament_num,
        )
        .annotate(
            rapporteur_person_id=F("rapporteurs__person_id"),
            proposer_person_id=F("proposers__person_id"),
        )
    )

    IssueUtilities.populate_issue_data(issues)

    # Tie rapporteured and proposed issues to their respective persons.
    for person in persons:

        person.rapporteured_issues = []
        person.proposed_issues = []

        for issue in issues:
            if issue.proposer_person_id == person.id:
                person.proposed_issues.append(issue)
            if issue.rapporteur_person_id == person.id:
                person.rapporteured_issues.append(issue)

    ctx = {
        "persons": persons,
        "party": party,
    }
    return render(request, "core/parliament_issue_overview.html", ctx)


def parliament_stats(request, parliament_num):

    inquiries = Issue.objects.prefetch_related("documents").filter(
        parliament__parliament_num=parliament_num, issue_type="q"
    )
    answered_inquiries = inquiries.prefetch_related("documents").filter(
        current_step="answered"
    )

    inquiry_count = inquiries.count()
    inquiry_count_answered = answered_inquiries.count()
    inquiry_ratio_answered = round(
        float(inquiry_count_answered) / float(inquiry_count) * 100, 2
    )

    # We'll need to iterate through the inquiries to create some data.
    total_seconds = 0
    max_time = None
    max_issue = None
    min_time = None
    min_issue = None
    for issue_q in answered_inquiries:
        # Done weirdly to save database hits. If this doesn't work, then
        # something is wrong with the data.
        for doc in issue_q.documents.all():
            if doc.is_main:
                doc_inquiry = doc
            elif doc.doc_type == "svar":
                doc_answer = doc

        timing_inquiry = doc_inquiry.time_published
        timing_answer = doc_answer.time_published

        # Find out how long it took to respond to the inquiry.
        time_taken = timing_answer - timing_inquiry

        # Collect the total number of seconds that have passed between an
        # inquiry being put forth and a response being delivered, so that we
        # can calculate the average response time.
        total_seconds += time_taken.total_seconds()

        # Catch the maximum time taken to respond.
        if max_time is None or max_time < time_taken:
            max_time = time_taken
            max_issue = issue_q

        # Catch the minimum time taken to respond.
        if min_time is None or min_time > time_taken:
            min_time = time_taken
            min_issue = issue_q

    # Actually calculate average.
    seconds = float(total_seconds) / float(len(answered_inquiries))
    inquiry_time_avg = timedelta(seconds=seconds)

    ctx = {
        "inquiry_count": inquiry_count,
        "inquiry_count_answered": inquiry_count_answered,
        "inquiry_ratio_answered": inquiry_ratio_answered,
        "inquiry_time_avg": inquiry_time_avg,
        "max_time": max_time,
        "max_issue": max_issue,
        "min_time": min_time,
        "min_issue": min_issue,
    }
    return render(request, "core/parliament_stats.html", ctx)


def parliament_missing_data(request):
    # If the requested parliament exists now, we'll redirect to the front page.
    if request.extravars["parliament"]:
        return redirect(reverse("home"))

    ctx = {}
    return render(request, "core/parliament_missing_data.html", ctx)


def person(request, slug, subslug=None):
    if subslug is None:
        return complete_person(request, slug)

    # Both 'slug' and 'subslug' exist at this point
    person = Person.objects.get(slug=slug, subslug=subslug)

    seats = person.seats.select_related("parliament", "party", "constituency").all()
    committee_seats = person.committee_seats.select_related(
        "parliament", "committee"
    ).all()
    minister_seats = person.minister_seats.select_related(
        "parliament", "minister", "party"
    ).all()

    issues = (
        Issue.objects.select_related("parliament")
        .prefetch_related("proposers__person", "proposers__committee", "to_committee")
        .filter(
            documents__proposers__person_id=person.id,
            documents__proposers__order=1,
            documents__is_main=True,
        )
        .order_by("parliament__parliament_num")
    )

    IssueUtilities.populate_issue_data(issues)

    special_discussions = (
        Issue.objects.select_related(
            "parliament", "special_inquisitor", "special_responder"
        )
        .filter(issue_group="B", issue_type="um", special_inquisitor_id=person.id)
        .order_by("-parliament__parliament_num")
    )

    # Figure out party affiliation.
    if len(minister_seats) > 0:
        party = minister_seats.last().party
    else:
        party = seats.last().party

    ctx = {
        "person": person,
        "party": party,
        "seats": seats,
        "committee_seats": committee_seats,
        "minister_seats": minister_seats,
        "issues": issues,
        "special_discussions": special_discussions,
    }
    return render(request, "core/person.html", ctx)


@login_required
def user_home(request):

    home_user = User.objects.get(id=request.user.id)

    subscriptions = (
        Subscription.objects.select_related("party", "committee", "person", "category")
        .filter(user_id=request.user.id)
        .order_by(
            "sub_type",
            "party__name",
            "committee__name",
            "person__name",
            "category__name",
        )
    )

    ctx = {
        "home_user": home_user,
        "subscriptions": subscriptions,
    }
    return render(request, "core/user_home.html", ctx)


@login_required
def user_access(request):

    access_list = (
        Access.objects.prefetch_related("issues__parliament")
        .select_related("friend__userprofile", "friend_group")
        .filter(user_id=request.user.id)
    )

    parliaments = Parliament.objects.all()
    issues = Issue.objects.filter(
        parliament__parliament_num=CURRENT_PARLIAMENT_NUM, issue_group="A"
    )
    users = User.objects.select_related("userprofile").exclude(id=request.user.id)
    user_groups = request.user.groups.prefetch_related("user_set__userprofile").all()
    groups = Group.objects.all()
    requestable_groups = Group.objects.exclude(
        membership_requests__user=request.user.id, membership_requests__status="pending"
    ).exclude(user__id=request.user.id)
    membership_requests = MembershipRequest.objects.select_related("group").filter(
        user_id=request.user.id, status="pending"
    )

    incoming_membership_requests = (
        MembershipRequest.objects.select_related("user__userprofile", "group")
        .exclude(user_id=request.user.id)
        .filter(group__user__id=request.user.id, status="pending")
    )

    # We want ordered users in the group listing, and no, I'm not implementing
    # a through-model in order to get ordering on ManyToMany fields.
    for user_group in user_groups:
        user_group.ordered_users = user_group.user_set.select_related(
            "userprofile"
        ).order_by("userprofile__name")

    ctx = {
        "access_list": access_list,
        "parliaments": parliaments,
        "users": users,
        "groups": groups,
        "requestable_groups": requestable_groups,
        "issues": issues,
        "user_groups": user_groups,
        "membership_requests": membership_requests,
        "incoming_membership_requests": incoming_membership_requests,
    }
    return render(request, "core/user_access.html", ctx)


@login_required
def user_issues_monitored(request, parliament_num):

    issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person", "proposers__committee")
        .filter(
            issue_monitors__user_id=request.user.id,
            parliament__parliament_num=parliament_num,
        )
        .order_by("-issue_num")
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {"issues": issues}
    return render(request, "core/user_issues_monitored.html", ctx)


@login_required
def user_issues_incoming(request):

    issues = request.extravars["incoming_issues"].prefetch_related(
        "proposers__person", "proposers__committee"
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {"issues": issues}

    return render(request, "core/user_issues_incoming.html", ctx)


@login_required
def user_issues_open(request, parliament_num):

    issues = (
        Issue.objects.select_related("parliament", "to_committee")
        .prefetch_related("proposers__person", "proposers__committee")
        .filter(
            dossierstatistic__user_id=request.user.id,
            dossierstatistic__has_useful_info=True,
            parliament__parliament_num=parliament_num,
        )
        .order_by("issue_num")
    )

    IssueUtilities.populate_issue_data(issues)

    ctx = {"issues": issues}

    return render(request, "core/user_issues_open.html", ctx)


def error500(request):
    response = render(request, "500.html")
    return response
