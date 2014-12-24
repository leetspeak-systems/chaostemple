from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.template.loader import render_to_string

from core.models import Document
from core.models import Dossier
from core.models import IssueBookmark

from core.jsonizer import jsonize

@login_required
@jsonize
def attentionstate(request, dossier_id):

    attentionstate = request.GET.get('attentionstate', None)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if attentionstate and dossier.attention != attentionstate:
        dossier.attention = attentionstate
        dossier.save()

    ctx = {
        'attentionstate': dossier.attention
    }
    return ctx

@login_required
@jsonize
def supportstate(request, dossier_id):

    supportstate = request.GET.get('supportstate', None)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if supportstate and dossier.support != supportstate:
        dossier.support = supportstate
        dossier.save()

    ctx = {
        'supportstate': dossier.support
    }
    return ctx

@login_required
@jsonize
def proposalstate(request, dossier_id):

    proposalstate = request.GET.get('proposalstate', None)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if proposalstate and dossier.proposal != proposalstate:
        dossier.proposal = proposalstate
        dossier.save()

    ctx = {
        'proposalstate': dossier.proposal
    }
    return ctx

@login_required
@jsonize
def knowledgestate(request, dossier_id):

    knowledgestate = request.GET.get('knowledgestate', None)
    if knowledgestate:
        knowledgestate = int(knowledgestate)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if knowledgestate is not None and dossier.knowledge != knowledgestate:
        dossier.knowledge = knowledgestate
        dossier.save()

    ctx = {
        'knowledgestate': dossier.knowledge
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

    content = render_to_string('core/stub/issue_bookmark_menuitems.html', {}, request_context)
    bookmarked_issue_count = len(bookmarked_issues)

    ctx = {
        'content': content,
        'bookmarked_issue_count': bookmarked_issue_count,
    }
    return ctx

