from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.template.loader import render_to_string

from core.models import Document
from core.models import Dossier
from core.models import IssueBookmark

from core.jsonizer import jsonize

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
    request_context = RequestContext(request)

    bookmarked_issues = request_context['bookmarked_issues']

    html_content = render_to_string('core/stub/issue_bookmark_menuitems.html', {}, request_context)
    bookmarked_issue_count = len(bookmarked_issues)

    ctx = {
        'html_content': html_content,
        'bookmarked_issue_count': bookmarked_issue_count,
    }
    return ctx

