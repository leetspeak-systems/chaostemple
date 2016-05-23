# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.db.models import Prefetch
from django.db.models import F
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from core.models import Access
from core.models import Dossier
from core.models import DossierStatistic
from core.models import DossierUtilities
from core.models import Issue
from core.models import IssueBookmark
from core.models import IssueUtilities

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import Document
from althingi.models import Parliament
from althingi.models import Person
from althingi.models import Review
from althingi.models import Session

def home(request):
    if request.extravars['newest_parliament_num'] is not None:
        return redirect(reverse('parliament', args=(request.extravars['newest_parliament_num'],)))
    else:
        return render(request, 'core/parliament_none.html', {})

def parliament(request, parliament_num):

    ctx = {
    }
    return render(request, 'core/parliament.html', ctx)

def parliament_issues(request, parliament_num):

    issues = Issue.objects.select_related('parliament').filter(
        parliament__parliament_num=parliament_num,
        document_count__gt=0
    )

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues,
    }
    return render(request, 'core/parliament_issues.html', ctx)

def parliament_issue(request, parliament_num, issue_num):

    # NOTE: The use of these get_prefetched_* functions is to be revised when Django 1.8 is released.
    # Specifically, it is hoped that the .refresh_from_db() function introduced will be a good replacement.

    visible_user_ids = [a.user_id for a in Access.objects.filter(friend_id=request.user.id, full_access=True)]

    def get_prefetched_documents():
        return Document.objects.prefetch_related(
            Prefetch('dossiers', queryset=Dossier.objects.filter(
                Q(user_id__in=visible_user_ids) | Q(user_id=request.user.id))
            ),
            'dossiers__memos',
            'dossiers__user',
            'proposers__person',
            'proposers__committee',
        ).filter(issue=issue)

    def get_prefetched_reviews():
        return Review.objects.prefetch_related(
            Prefetch('dossiers', queryset=Dossier.objects.filter(
                Q(user_id__in=visible_user_ids) | Q(user_id=request.user.id))
            ),
            #Prefetch('dossiers', queryset=Dossier.objects.all()),
            'dossiers__memos',
            'dossiers__user',
            'committee'
        ).select_related('issue__parliament').filter(issue=issue)

    issue = Issue.objects.select_related('parliament').get(
        parliament__parliament_num=parliament_num,
        issue_group='A',
        issue_num=issue_num
    )
    documents = get_prefetched_documents()
    reviews = get_prefetched_reviews()

    issue_sessions = Session.objects.select_related('parliament').filter(session_agenda_items__issue_id=issue.id)
    issue_committee_agendas = CommitteeAgenda.objects.select_related(
        'parliament',
        'committee'
    ).filter(committee_agenda_items__issue_id=issue.id)

    reload_documents = False
    reload_reviews = False
    if request.user.is_authenticated():
        for document in documents:
            if document.dossiers.filter(user=request.user).count() == 0:
                Dossier(document=document, user=request.user).save(update_statistics=False)
                reload_documents = True

        for review in reviews:
            if review.dossiers.filter(user=request.user).count() == 0:
                Dossier(review=review, user=request.user).save(update_statistics=False)
                reload_reviews = True

    if reload_documents or reload_reviews:
        if reload_documents:
            documents = get_prefetched_documents()
        if reload_reviews:
            reviews = get_prefetched_reviews()

        # Reload incoming menu
        request.extravars['dossier_statistics_incoming'] = DossierUtilities.get_incoming_dossier_statistics(
            request.user.id,
            parliament_num
        )
        # Also reload bookmarks menu (where incoming stuff is also displayed)
        IssueUtilities.populate_dossier_statistics(request.extravars['bookmarked_issues'], request.user.id)

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
    session_agenda_items = session.session_agenda_items.select_related('issue__parliament').all()

    IssueUtilities.populate_dossier_statistics([i.issue for i in session_agenda_items], request.user.id)

    ctx = {
        'session': session,
        'session_agenda_items': session_agenda_items,
    }
    return render(request, 'core/parliament_session.html', ctx)

def parliament_committees(request, parliament_num):

    committees = Committee.objects.filter(parliaments__parliament_num=parliament_num)

    for committee in committees:
        committee.agenda_count = committee.committee_agendas.filter(parliament__parliament_num=parliament_num).count()

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
    committee_agenda_items = committee_agenda.committee_agenda_items.select_related('issue__parliament').all()

    IssueUtilities.populate_dossier_statistics(filter(None, [i.issue for i in committee_agenda_items]), request.user.id)

    ctx = {
        'committee': committee,
        'committee_agenda': committee_agenda,
        'committee_agenda_items': committee_agenda_items,
    }
    return render(request, 'core/parliament_committee_agenda.html', ctx)

def parliament_persons(request, parliament_num):

    persons = Person.objects.filter(seats__parliament__parliament_num=parliament_num, seats__seat_type=u'þingmaður').distinct()
    deputies = Person.objects.filter(seats__parliament__parliament_num=parliament_num, seats__seat_type=u'varamaður').distinct()

    ctx = {
        'persons': persons,
        'deputies': deputies,
    }
    return render(request, 'core/parliament_persons.html', ctx)

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

    seats = person.seats.select_related('parliament', 'party').all()
    committee_seats = person.committee_seats.select_related('parliament', 'committee').all()

    issues = Issue.objects.select_related('parliament').filter(
        documents__proposers__person_id=person.id,
        documents__proposers__order=1,
        documents__is_main=True
    ).order_by('-parliament__parliament_num')

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

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

    issues = Issue.objects.select_related('parliament').filter(
        issue_bookmarks__user_id=request.user.id,
        parliament__parliament_num=parliament_num
    ).order_by('-issue_num')

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }
    return render(request, 'core/user_issues_bookmarked.html', ctx)

@login_required
def user_issues_incoming(request):

    issues = Issue.objects.select_related('parliament').filter(
        Q(
            dossierstatistic__user_id=request.user.id,
            dossierstatistic__has_useful_info=True,
            parliament__parliament_num=request.extravars['parliament_num']
        ),
        ~Q(
            document_count=F('dossierstatistic__document_count'),
            review_count=F('dossierstatistic__review_count')
        )
    ).order_by('-issue_num')

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }

    return render(request, 'core/user_issues_incoming.html', ctx)

@login_required
def user_issues_open(request, parliament_num):

    issues = Issue.objects.select_related('parliament').filter(
        dossierstatistic__user_id=request.user.id,
        dossierstatistic__has_useful_info=True,
        parliament__parliament_num=parliament_num
    ).order_by('issue_num')

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }

    return render(request, 'core/user_issues_open.html', ctx)

def error500(request):
    response = render(request, '500.html')
    return response
