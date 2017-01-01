from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.utils import IntegrityError
from django.template.loader import render_to_string

from althingi.models import Proposer

from core.breadcrumbs import append_to_crumb_string

from core.models import Access
from core.models import Issue
from core.models import IssueBookmark

from jsonizer.utils import jsonize

@jsonize
def proposer_subproposers(request, proposer_id):

    crumb_string = append_to_crumb_string(request.POST.get('path'), request.POST.get('crumb_string', ''))

    proposer = Proposer.objects.get(id=proposer_id)
    if proposer.committee_id:
        subproposers = Proposer.objects.select_related('person').filter(parent_id=proposer_id)
    else:
        subproposers = Proposer.objects.select_related('person').filter(issue_id=proposer.issue_id)

    ctx = {'subproposers': []}

    for sp in subproposers:
        ctx['subproposers'].append({
            'url': '%s?from=%s' % (reverse('person', args=(sp.person.slug, sp.person.subslug)), crumb_string),
            'name': sp.person.name
        })

    return ctx

@jsonize
def list_issues(request, parliament_num):

    issues = Issue.objects.filter(parliament__parliament_num=parliament_num, issue_group='A')

    issue_list_json = []
    for issue in issues:
        issue_list_json.append({'id': issue.id, 'name': issue.detailed() })

    ctx = {
        'parliament_num': parliament_num,
        'issue_list': issue_list_json,
    }
    return ctx

@login_required
@jsonize
def issue_bookmark_toggle(request, issue_id):

    is_bookmarked = None

    try:
        issue_bookmark = IssueBookmark.objects.get(user_id=request.user.id, issue_id=issue_id)
        issue_bookmark.delete()
        is_bookmarked = False
    except IssueBookmark.DoesNotExist:
        issue_bookmark = IssueBookmark.objects.create(user_id=request.user.id, issue_id=issue_id)
        is_bookmarked = True

    ctx = {
        'is_bookmarked': is_bookmarked,
    }
    return ctx

@login_required
@jsonize
def issue_bookmark_menu(request, parliament_num):

    bookmarked_issues = request.extravars['bookmarked_issues']

    html_content = render_to_string('core/stub/issue_bookmark_menuitems.html', {
        'bookmarked_issues': bookmarked_issues,
        'parliament_num': parliament_num
    })
    bookmarked_issue_count = len(bookmarked_issues)

    ctx = {
        'html_content': html_content,
        'bookmarked_issue_count': bookmarked_issue_count,
    }
    return ctx

@login_required
@jsonize
def user_access_grant(request, friend_id, issue_id=None):

    try:
        access = Access.objects.get(user_id=request.user.id, friend_id=friend_id)
    except Access.DoesNotExist:
        access = Access(user_id=request.user.id, friend_id=friend_id)

    if request.GET.has_key('full_access'):
        access.full_access = request.GET.get('full_access', False) == 'true'

    access.save()

    try:
        if issue_id is not None and not access.full_access:
            access.issues.add(issue_id)
    except IntegrityError:
        pass

    access_list = Access.objects.prefetch_related('issues__parliament').select_related('friend').filter(user_id=request.user.id)

    html_content = render_to_string('core/stub/user_access_list.html', { 'access_list': access_list })

    ctx = {
        'full_access': access.full_access,
        'html_content': html_content,
    }
    return ctx

@login_required
@jsonize
def user_access_revoke(request, friend_id, issue_id=None):

    access = Access.objects.get(user_id=request.user.id, friend_id=friend_id)

    if issue_id is None:
        access.delete()
    else:
        issue_id = int(issue_id) # This should work or we should fail
        access.issues.remove(issue_id)

    access_list = Access.objects.prefetch_related('issues__parliament').select_related('friend').filter(user_id=request.user.id)

    html_content = render_to_string('core/stub/user_access_list.html', { 'access_list': access_list })

    ctx = {
        'html_content': html_content,
    }
    return ctx

