from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import Http404
from django.urls import reverse
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from althingi.models import Proposer

from core.breadcrumbs import append_to_crumb_string

from core.models import Access
from core.models import Issue
from core.models import IssueBookmark
from core.models import MembershipRequest
from core.models import Subscription
from core.models import UserProfile

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
def access_grant(request, friend_group_id=None, friend_id=None, issue_id=None):

    lookup_kwargs = { 'user_id': request.user.id }

    if friend_group_id:
        lookup_kwargs['friend_group_id'] = friend_group_id
    elif friend_id:
        lookup_kwargs['friend_id'] = friend_id
    else:
        raise Http404

    try:
        access = Access.objects.get(**lookup_kwargs)
    except Access.DoesNotExist:
        access = Access(**lookup_kwargs)

    if 'full_access' in request.GET:
        access.full_access = request.GET.get('full_access', False) == 'true'

    access.save()

    if issue_id is not None and not access.full_access:
        access.issues.add(issue_id)

    access_list = Access.objects.prefetch_related(
        'issues__parliament'
    ).select_related(
        'friend__userprofile',
        'friend_group'
    ).filter(
        user_id=request.user.id
    )

    html_content = render_to_string('core/stub/user_access_list.html', { 'access_list': access_list })

    ctx = {
        'full_access': access.full_access,
        'html_content': html_content,
    }
    return ctx

@login_required
@jsonize
def access_revoke(request, friend_group_id=None, friend_id=None, issue_id=None):

    lookup_kwargs = { 'user_id': request.user.id }

    if friend_group_id:
        lookup_kwargs['friend_group_id'] = friend_group_id
    elif friend_id:
        lookup_kwargs['friend_id'] = friend_id
    else:
        raise Http404

    try:
        access = Access.objects.get(**lookup_kwargs)
    except Access.DoesNotExist:
        access = Access(**lookup_kwargs)

    if issue_id is None:
        access.delete()
    else:
        issue_id = int(issue_id) # This should work or we should fail
        access.issues.remove(issue_id)

    access_list = Access.objects.prefetch_related(
        'issues__parliament'
    ).select_related(
        'friend__userprofile',
        'friend_group'
    ).filter(
        user_id=request.user.id
    )

    html_content = render_to_string('core/stub/user_access_list.html', { 'access_list': access_list })

    ctx = {
        'html_content': html_content,
    }
    return ctx


@login_required
@jsonize
def membership_request(request, group_id, action):
    if action == 'request':
        MembershipRequest.objects.get_or_create(
            user_id=request.user.id,
            group_id=group_id,
            status='pending'
        )
    elif action == 'withdraw':
        MembershipRequest.objects.filter(user_id=request.user.id, group_id=group_id, status='pending').delete()
    else:
        raise Http404

    requestable_groups = Group.objects.exclude(
        membership_requests__user=request.user.id,
        membership_requests__status='pending'
    ).exclude(user__id=request.user.id)
    membership_requests = MembershipRequest.objects.select_related('group').filter(
        user_id=request.user.id,
        status='pending'
    )

    html_content = render_to_string('core/stub/membership_requests.html', {
        'requestable_groups': requestable_groups,
        'membership_requests': membership_requests,
    })

    ctx = {
        'html_content': html_content,
    }
    return ctx


@login_required
@jsonize
def process_membership_request(request):
    membership_request_id = int(request.POST.get('membership_request_id'))
    status = request.POST.get('status')

    if status not in ['accepted', 'rejected']:
        raise Http404

    membership_request = get_object_or_404(
        MembershipRequest,
        id=membership_request_id,
        group__user__id=request.user.id
    )

    membership_request.set_status(status, request.user)

    incoming_membership_requests = MembershipRequest.objects.select_related('user__userprofile', 'group').exclude(
        user_id=request.user.id
    ).filter(group__user__id=request.user.id, status='pending')

    html_content = render_to_string('core/stub/incoming_membership_requests.html', {
        'incoming_membership_requests': incoming_membership_requests
    })

    ctx = {
        'html_content': html_content,
    }
    return ctx


@login_required
@jsonize
def subscription_toggle(request, sub_type, sub_id):

    lookup = {
        'user': request.user,
        '%s_id' % sub_type: sub_id,
    }

    subscribed = None

    try:
        Subscription.objects.get(**lookup).delete()
        subscribed = False

    except Subscription.DoesNotExist:
        Subscription(**lookup).save()
        subscribed = True

    ctx = {
        'subscribed': subscribed,
    }
    return ctx


@login_required
@jsonize
def setting_set(request, setting_name, setting_value):
    allowed_settings = [
        'auto_bookmark',
    ]

    if setting_name not in allowed_settings:
        raise Http404

    # Boolean support.
    if setting_value.lower() in ['true', 'false']:
        setting_value = setting_value.lower() == 'true'

    userprofile = UserProfile.objects.get(user_id=request.user.id)

    if getattr(userprofile, 'setting_%s' % setting_name) != setting_value:
        setattr(userprofile, 'setting_%s' % setting_name, setting_value)
        userprofile.save()
        value_changed = True
    else:
        value_changed = False

    ctx = {
        'value_changed': value_changed,
        'new_value': setting_value,
    }
    return ctx
