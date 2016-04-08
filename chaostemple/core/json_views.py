import json

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.db.utils import IntegrityError
from django.template.loader import render_to_string

from althingi.models import SessionAgendaItem

from core.models import Access
from core.models import Document
from core.models import Dossier
from core.models import DossierStatistic
from core.models import Issue
from core.models import IssueBookmark
from core.models import IssueUtilities
from core.models import Memo

from jsonizer.utils import jsonize

@login_required
@jsonize
def dossier_fieldstate(request, dossier_id, fieldname):
    fieldstate = request.GET.get('fieldstate', None)

    if not fieldname in Dossier.tracker.fields:
        raise Exception('"%s" is not a recognized fieldname of a dossier' % fieldname)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if fieldstate is not None and getattr(dossier, fieldname) != fieldstate:
        # Ensure proper type of field
        fieldtype = type(getattr(dossier, fieldname))
        fieldstate = fieldtype(fieldstate)

        setattr(dossier, fieldname, fieldstate)
        dossier.save()

    ctx = {
        fieldname: getattr(dossier, fieldname),
    }
    return ctx

@login_required
@jsonize
def delete_dossier(request, dossier_id):

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    document_id = dossier.document_id
    review_id = dossier.review_id

    dossier.delete()

    ctx = {
        'document_id': document_id,
        'review_id': review_id,
    }
    return ctx

@jsonize
def list_issues(request, parliament_id):

    issues = Issue.objects.filter(parliament_id=parliament_id, issue_group='A')

    issue_list_json = []
    for issue in issues:
        issue_list_json.append({'id': issue.id, 'name': issue.__str__().capitalize() })

    ctx = {
        'parliament_id': parliament_id,
        'issue_list': issue_list_json,
    }
    return ctx

@login_required
@jsonize
def delete_issue_dossiers(request, issue_id):

    Dossier.objects.filter(issue_id=issue_id, user_id=request.user.id).delete()
    DossierStatistic.objects.filter(issue_id=issue_id, user_id=request.user.id).delete()

    issue = Issue.objects.select_related('parliament').get(id=issue_id)
    IssueUtilities.populate_dossier_statistics([issue], request.user.id)

    bookmarked_issues = request.extravars['bookmarked_issues']

    # Get session agenda item info to display with the issue HTML returned
    session_agenda_item_id = int(request.GET.get('session_agenda_item_id', 0) or 0)
    if session_agenda_item_id:
        session_agenda_item = SessionAgendaItem.objects.get(id=session_agenda_item_id)
    else:
        session_agenda_item = None

    stub_ctx = {
        'request': request,
        'issue': issue,
        'user': request.user,
        'bookmarked_issues': bookmarked_issues,
        'agenda_item': session_agenda_item,
    }
    html_content = render_to_string('core/stub/issue.html', stub_ctx)

    ctx = {
        'issue_id': issue_id,
        'html_content': html_content,
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
def issue_bookmark_menu(request):

    bookmarked_issues = request.extravars['bookmarked_issues']
    parliament_num = request.extravars['parliament_num']

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
def add_memo(request, dossier_id):

    max_order = Memo.objects.filter(
        user_id=request.user.id,
        dossier_id=dossier_id
    ).aggregate(maximum=Max('order'))['maximum']

    memo = Memo(user_id=request.user.id, dossier_id=dossier_id)
    memo.content = request.POST.get('content')
    memo.order = max_order + 1 if max_order is not None else 1
    memo.save()

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)

    html_content = render_to_string('core/stub/dossier_memos.html', { 'memos': memos, 'dossier_id': dossier_id })

    ctx = {
        'html_content': html_content,
        'dossier_id': dossier_id,
        'memo_count': len(memos),
    }
    return ctx

@login_required
@jsonize
def edit_memo(request, memo_id):

    memo = Memo.objects.get(id=memo_id, user_id=request.user.id)
    dossier_id = memo.dossier_id

    memo.content = request.POST.get('content')
    memo.save()

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)

    html_content = render_to_string('core/stub/dossier_memos.html', { 'memos': memos, 'dossier_id': dossier_id })

    ctx = {
        'html_content': html_content,
        'dossier_id': dossier_id,
    }
    return ctx

@login_required
@jsonize
def delete_memo(request, memo_id):

    memo = Memo.objects.get(id=memo_id, user_id=request.user.id)
    dossier_id = memo.dossier_id
    memo.delete()

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)

    html_content = render_to_string('core/stub/dossier_memos.html', { 'memos': memos, 'dossier_id': dossier_id })

    ctx = {
        'html_content': html_content,
        'dossier_id': dossier_id,
        'memo_count': len(memos),
    }
    return ctx

@login_required
@jsonize
def sort_memos(request, dossier_id):

    order_map = json.loads(request.POST.get('order_map'))

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)
    for memo in memos:
        if memo.order != order_map[str(memo.id)]:
            memo.order = order_map[str(memo.id)]
            memo.save()

    memos = memos.order_by('order')

    html_content = render_to_string('core/stub/dossier_memos.html', { 'memos': memos, 'dossier_id': memo.dossier_id })

    ctx = {
        'html_content': html_content,
        'dossier_id': memo.dossier_id,
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

