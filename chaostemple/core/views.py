# -*- coding: utf-8 -*-
import operator

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Case
from django.db.models import Count
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import When
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import dateparse
from django.utils import timezone

from core.models import Access
from core.models import AccessUtilities
from core.models import Issue
from core.models import IssueBookmark
from core.models import IssueUtilities

from dossier.models import Dossier
from dossier.models import DossierStatistic
from dossier.models import Memo

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import Document
from althingi.models import Parliament
from althingi.models import Party
from althingi.models import Person
from althingi.models import Review
from althingi.models import Session


def home(request):
    return redirect(reverse('day'))


def day(request, input_date=None):

    # Redirect to today if no date specified
    if input_date is None:
        now = timezone.now()
        return redirect(reverse('day', args=(now.strftime('%Y-%m-%d'),)))

    # Make sure that the date makes sense and otherwise result in a "Page not found" error
    try:
        requested_date = timezone.make_aware(dateparse.parse_datetime('%s 00:00:00' % input_date))
    except ValueError:
        raise Http404

    requested_yesterday = requested_date - timezone.timedelta(days=1)
    requested_tomorrow = requested_date + timezone.timedelta(days=1)

    # Get issues of specified day
    sessions = Session.objects.select_related('parliament').prefetch_related('session_agenda_items').on_date(requested_date)
    for session in sessions:
        session.session_agenda_items_loaded = session.session_agenda_items.select_related(
            'issue__parliament'
        ).prefetch_related(
            'issue__proposers__person',
            'issue__proposers__committee'
        )

        # Populate the dossier statistics
        IssueUtilities.populate_dossier_statistics([i.issue for i in session.session_agenda_items_loaded])

    # Get committee agendas of specified day
    committee_agendas = CommitteeAgenda.objects.select_related('committee').prefetch_related(
        'committee_agenda_items'
    ).on_date(requested_date)
    for committee_agenda in committee_agendas:
        committee_agenda.committee_agenda_items_loaded = committee_agenda.committee_agenda_items.select_related(
            'issue__parliament'
        ).prefetch_related(
            'issue__proposers__person'
        )

        # Populate the dossier statistics
        IssueUtilities.populate_dossier_statistics([a.issue for a in committee_agenda.committee_agenda_items_loaded])

    ctx = {
        'requested_yesterday': requested_yesterday,
        'requested_date': requested_date,
        'requested_tomorrow': requested_tomorrow,
        'sessions': sessions,
        'committee_agendas': committee_agendas,
    }
    return render(request, 'core/day.html', ctx)


def upcoming(request):

    next_sessions = request.extravars['next_sessions']
    next_committee_agendas = request.extravars['next_committee_agendas']

    # Get issues that are upcoming in sessions
    # They are prepended with "garbled_" because we know in advance that they may contain duplicates.
    garbled_session_issues = Issue.objects.select_related('parliament').prefetch_related(
        'proposers__person',
        'session_agenda_items__session'
    ).filter(
        issue_group = 'A',
        session_agenda_items__session__in=next_sessions
    ).order_by('session_agenda_items__session__session_num', 'session_agenda_items__order').distinct()

    # Get issues that are upcoming in committee agendas
    # They are prepended with "garbled_" because we know in advance that they may contain duplicates.
    garbled_committee_issues = Issue.objects.select_related('parliament').prefetch_related(
        'proposers__person',
        'committee_agenda_items__committee_agenda',
    ).filter(committee_agenda_items__committee_agenda__in=next_committee_agendas).order_by(
        'committee_agenda_items__committee_agenda__timing_start_planned'
    ).distinct()

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
    IssueUtilities.populate_dossier_statistics(session_issues + committee_issues)

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Get upcoming sessions for each issue (can this be optimized?)
    for issue in session_issues:
        issue.upcoming_sessions = Session.objects.select_related('parliament').filter(
            session_agenda_items__issue_id=issue.id,
            timing_start_planned__gt=today
        ).distinct()

    # Get upcoming committee agendas for each issue (can this be optimized?)
    for issue in committee_issues:
        issue.upcoming_committee_agendas = CommitteeAgenda.objects.select_related('parliament', 'committee').filter(
            committee_agenda_items__issue_id=issue.id,
            timing_start_planned__gt=today
        ).distinct()

    ctx = {
        'session_issues': session_issues,
        'committee_issues': committee_issues,
    }
    return render(request, 'core/upcoming.html', ctx)


def parliament(request, parliament_num):

    ctx = {
    }
    return render(request, 'core/parliament.html', ctx)


def parliament_issues(request, parliament_num):

    issues = Issue.objects.select_related('parliament').prefetch_related('proposers__person', 'proposers__committee').filter(
        parliament__parliament_num=parliament_num,
        document_count__gt=0
    )

    IssueUtilities.populate_dossier_statistics(issues)

    ctx = {
        'issues': issues,
    }
    return render(request, 'core/parliament_issues.html', ctx)


def parliament_issue(request, parliament_num, issue_num):

    issue = Issue.objects.select_related('parliament').get(
        parliament__parliament_num=parliament_num,
        issue_group='A',
        issue_num=issue_num
    )

    # Get access objects and sort them
    accesses = {'partial': [], 'full': []}
    for access in AccessUtilities.get_access():
        accesses['full' if access.full_access else 'partial'].append(access)

    visible_user_ids = [a.user_id for a in accesses['full']]

    partial_conditions = []
    for partial_access in accesses['partial']:
        for issue in partial_access.issues.all():
            partial_conditions.append(Q(user_id=partial_access.user_id) & Q(issue_id=issue.id))

    # Add dossiers from users who have given full access
    prefetch_query = Q(user_id__in=visible_user_ids) | Q(user_id=request.user.id)
    # Add dossiers from users who have given access to this particular issue
    if len(partial_conditions) > 0:
        prefetch_query.add(Q(reduce(operator.or_, partial_conditions)), Q.OR)

    # Add prefetch query but leave out useless information from other users
    prefetch_queryset = Dossier.objects.filter(prefetch_query).annotate(memo_count=Count('memos')).exclude(
        ~Q(user_id=request.user.id), attention='none', knowledge=0, support='undefined', proposal='none', memo_count=0
    )

    documents = Document.objects.prefetch_related(
        Prefetch('dossiers', queryset=prefetch_queryset),
        'dossiers__memos',
        'dossiers__user',
        'proposers__person',
        'proposers__committee',
    ).filter(issue=issue)

    reviews = Review.objects.prefetch_related(
        Prefetch('dossiers', queryset=prefetch_queryset),
        'dossiers__memos',
        'dossiers__user',
        'committee'
    ).select_related('issue__parliament').filter(issue=issue)

    issue_sessions = Session.objects.select_related('parliament').filter(session_agenda_items__issue_id=issue.id)
    issue_committee_agendas = CommitteeAgenda.objects.select_related(
        'parliament',
        'committee'
    ).filter(committee_agenda_items__issue_id=issue.id)

    if request.user.is_authenticated():
        statistic, c = DossierStatistic.objects.get_or_create(issue_id=issue.id, user_id=request.user.id)

        stats_updated = False
        for document in Document.objects.filter(issue_id=issue.id).exclude(dossiers__user_id=request.user.id):
            Dossier(document=document, user_id=request.user.id).save(input_statistic=statistic)
            stats_updated = True

        for review in Review.objects.filter(issue_id=issue.id).exclude(dossiers__user_id=request.user.id):
            Dossier(review=review, user_id=request.user.id).save(input_statistic=statistic)
            stats_updated = True

        if stats_updated:
            # Save previously collectec dossier statistics
            statistic.save()

    ctx = {
        'issue': issue,
        'issue_sessions': issue_sessions,
        'issue_committee_agendas': issue_committee_agendas,
        'documents': documents,
        'reviews': reviews,
        'attentionstates': Dossier.ATTENTION_STATES,
        'knowledgestates': Dossier.KNOWLEDGE_STATES,
        'supportstates': Dossier.SUPPORT_STATES,
        'proposalstates': Dossier.PROPOSAL_STATES,
        'max_memo_length': Memo._meta.get_field('content').max_length,
    }
    return render(request, 'core/parliament_issue.html', ctx)


def parliament_sessions(request, parliament_num):

    sessions = Session.objects.filter(parliament__parliament_num=parliament_num).annotate(
        session_agenda_item_count=Count('session_agenda_items')
    )

    ctx = {
        'sessions': sessions
    }
    return render(request, 'core/parliament_sessions.html', ctx)


def parliament_session(request, parliament_num, session_num):

    session = get_object_or_404(Session, parliament__parliament_num=parliament_num, session_num=session_num)
    session_agenda_items = session.session_agenda_items.select_related('issue__parliament').prefetch_related(
        'issue__proposers__person', 'issue__proposers__committee'
    ).all()

    IssueUtilities.populate_dossier_statistics([i.issue for i in session_agenda_items])

    ctx = {
        'session': session,
        'session_agenda_items': session_agenda_items,
    }
    return render(request, 'core/parliament_session.html', ctx)


def parliament_committees(request, parliament_num):

    committees = Committee.objects.filter(
        parliaments__parliament_num=parliament_num
    ).annotate(agenda_count=Count(
        Case(
            When(committee_agendas__parliament__parliament_num=parliament_num, then=1)
        )
    ))

    ctx = {
        'committees': committees
    }
    return render(request, 'core/parliament_committees.html', ctx)


def parliament_committee(request, parliament_num, committee_id):

    committee = Committee.objects.get(id=committee_id)
    agendas = committee.committee_agendas.filter(parliament__parliament_num=parliament_num).annotate(
        item_count=Count('committee_agenda_items')
    )

    ctx = {
        'committee': committee,
        'agendas': agendas,
    }
    return render(request, 'core/parliament_committee.html', ctx)


def parliament_committee_agenda(request, parliament_num, committee_id, agenda_id):

    committee = Committee.objects.get(id=committee_id)
    committee_agenda = committee.committee_agendas.get(id=agenda_id)
    committee_agenda_items = committee_agenda.committee_agenda_items.select_related('issue__parliament').prefetch_related(
        'issue__proposers__person', 'issue__proposers__committee'
    ).all()

    IssueUtilities.populate_dossier_statistics(filter(None, [i.issue for i in committee_agenda_items]))

    ctx = {
        'committee': committee,
        'committee_agenda': committee_agenda,
        'committee_agenda_items': committee_agenda_items,
    }
    return render(request, 'core/parliament_committee_agenda.html', ctx)


def parliament_parties(request, parliament_num):

    parliament = request.extravars['parliament']
    if parliament.timing_end:
        timing = parliament.timing_end - timezone.timedelta(minutes=1)
    else:
        timing = timezone.now()

    parties = Party.objects.filter(
        Q(parliament_num_last__gte=parliament_num) | Q(parliament_num_last=None),
        parliament_num_first__lte=parliament_num
    ).annotate_mp_counts(timing)

    ctx = {
        'parties': parties,
    }
    return render(request,'core/parliament_parties.html', ctx)


def parliament_persons(request, parliament_num, party_slug=None):

    parliament = request.extravars['parliament']

    q_persons = Q(seats__parliament__parliament_num=parliament_num)

    if party_slug:
        party = get_object_or_404(Party, slug=party_slug)
        q_persons = q_persons & Q(seats__party__slug=party_slug)
    else:
        party = None

    persons = Person.objects.prefetch_latest_seats(
        parliament,
        'party',
        'constituency',
        'parliament'
    ).filter(q_persons).distinct()

    ctx = {
        'parliament': parliament,
        'persons': persons,
        'party': party,
    }
    return render(request, 'core/parliament_persons.html', ctx)


def parliament_missing_data(request):
    # If the requested parliament exists now, we'll redirect to the front page.
    if request.extravars['parliament']:
        return redirect(reverse('home'))

    ctx = {}
    return render(request, 'core/parliament_missing_data.html', ctx)


def person(request, slug, subslug=None):
    # If no subslug is provided, we try to figure out who the person is and if we can't, we ask the user
    if subslug is None:
        persons = Person.objects.filter(slug=slug).order_by('-birthdate')
        if persons.count() > 1:
            return render(request, 'core/person_select_from_multiple.html', { 'persons': persons })
        elif persons.count() == 1:
            return redirect(reverse('person', args=(slug, persons[0].subslug)))
        else:
            raise Http404

    # Both 'slug' and 'subslug' exist at this point
    person = Person.objects.get(slug=slug, subslug=subslug)

    seats = person.seats.select_related('parliament', 'party', 'constituency').all()
    committee_seats = person.committee_seats.select_related('parliament', 'committee').all()

    issues = Issue.objects.select_related('parliament').prefetch_related('proposers__person', 'proposers__committee').filter(
        documents__proposers__person_id=person.id,
        documents__proposers__order=1,
        documents__is_main=True
    ).order_by('-parliament__parliament_num')

    IssueUtilities.populate_dossier_statistics(issues)

    ctx = {
        'person': person,
        'seats': seats,
        'committee_seats': committee_seats,
        'issues': issues,
    }
    return render(request, 'core/person.html', ctx)


@login_required
def user_home(request, username):

    home_user = get_object_or_404(User, username=username)

    ctx = {
        'home_user': home_user,
    }
    return render(request, 'core/user_home.html', ctx)


@login_required
def user_access(request):

    access_list = Access.objects.prefetch_related('issues__parliament').select_related('friend').filter(user_id=request.user.id)

    parliaments = Parliament.objects.all()
    issues = Issue.objects.filter(parliament__parliament_num=CURRENT_PARLIAMENT_NUM, issue_group='A')
    users = User.objects.exclude(id=request.user.id)

    ctx = {
        'access_list': access_list,
        'parliaments': parliaments,
        'users': users,
        'issues': issues,
    }
    return render(request, 'core/user_access.html', ctx)


@login_required
def user_issues_bookmarked(request, parliament_num):

    issues = Issue.objects.select_related('parliament').prefetch_related('proposers__person', 'proposers__committee').filter(
        issue_bookmarks__user_id=request.user.id,
        parliament__parliament_num=parliament_num
    ).order_by('-issue_num')

    IssueUtilities.populate_dossier_statistics(issues)

    ctx = {
        'issues': issues
    }
    return render(request, 'core/user_issues_bookmarked.html', ctx)


@login_required
def user_issues_incoming(request):

    issues = request.extravars['incoming_issues'].prefetch_related('proposers__person', 'proposers__committee')

    IssueUtilities.populate_dossier_statistics(issues)

    ctx = {
        'issues': issues
    }

    return render(request, 'core/user_issues_incoming.html', ctx)


@login_required
def user_issues_open(request, parliament_num):

    issues = Issue.objects.select_related('parliament').prefetch_related('proposers__person', 'proposers__committee').filter(
        dossierstatistic__user_id=request.user.id,
        dossierstatistic__has_useful_info=True,
        parliament__parliament_num=parliament_num
    ).order_by('issue_num')

    IssueUtilities.populate_dossier_statistics(issues)

    ctx = {
        'issues': issues
    }

    return render(request, 'core/user_issues_open.html', ctx)


def error500(request):
    response = render(request, '500.html')
    return response
