from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import Http404
from django.http import HttpResponse
from django.urls import reverse
from django.db.models import Prefetch
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import capfirst
from django.template.loader import render_to_string

from djalthingi.models import Proposer

from core.breadcrumbs import append_to_crumb_string

from core.models import Access
from core.models import Document
from core.models import Issue
from core.models import IssueMonitor
from core.models import IssueUtilities
from core.models import MembershipRequest
from core.models import Review
from core.models import Subscription
from core.models import UserProfile

from dossier.models import Dossier

from jsonizer.utils import jsonize


@jsonize
def proposer_subproposers(request, proposer_id):

    crumb_string = append_to_crumb_string(
        request.POST.get("path"), request.POST.get("crumb_string", "")
    )

    proposer = Proposer.objects.get(id=proposer_id)
    if proposer.committee_id:
        subproposers = Proposer.objects.select_related("person").filter(
            parent_id=proposer_id
        )
    else:
        subproposers = Proposer.objects.select_related("person").filter(
            issue_id=proposer.issue_id
        )

    ctx = {"subproposers": []}

    for sp in subproposers:
        ctx["subproposers"].append(
            {
                "url": "%s?from=%s"
                % (
                    reverse("person", args=(sp.person.slug, sp.person.subslug)),
                    crumb_string,
                ),
                "name": sp.person.name,
            }
        )

    return ctx


@jsonize
def list_issues(request, parliament_num):

    issues = Issue.objects.filter(
        parliament__parliament_num=parliament_num, issue_group="A"
    )

    issue_list_json = []
    for issue in issues:
        issue_list_json.append({"id": issue.id, "name": issue.detailed()})

    ctx = {
        "parliament_num": parliament_num,
        "issue_list": issue_list_json,
    }
    return ctx


@login_required
@jsonize
def document(request, parliament_num, doc_num):

    prefetch_q = Dossier.objects.by_user(request.user)

    document = (
        Document.objects.prefetch_related(Prefetch("dossiers", queryset=prefetch_q))
        .annotate_seen(request.user)
        .get(issue__parliament__parliament_num=parliament_num, doc_num=doc_num)
    )

    html = render_to_string(
        "core/stub/document.html", {"document": document}, request=request
    )

    ctx = {
        "document_id": document.id,
        "html": html,
    }
    return ctx


@login_required
@jsonize
def review(request, parliament_num, log_num):

    prefetch_q = Dossier.objects.by_user(request.user)

    review = (
        Review.objects.prefetch_related(Prefetch("dossiers", queryset=prefetch_q))
        .annotate_seen(request.user)
        .get(issue__parliament__parliament_num=parliament_num, log_num=log_num)
    )

    html = render_to_string(
        "core/stub/review.html", {"review": review}, request=request
    )

    ctx = {
        "review_id": review.id,
        "html": html,
    }
    return ctx


@login_required
@jsonize
def issue_monitor_toggle(request, issue_id):

    is_monitored = None

    try:
        issue_monitor = IssueMonitor.objects.get(
            user_id=request.user.id, issue_id=issue_id
        )
        issue_monitor.delete()
        is_monitored = False
    except IssueMonitor.DoesNotExist:
        issue_monitor = IssueMonitor.objects.create(
            user_id=request.user.id, issue_id=issue_id
        )
        is_monitored = True

    # Prepare basic result object.
    ctx = {
        "is_monitored": is_monitored,
        "issue_id": issue_id,
    }

    # If a stub_type is provided we'll need to return some HTML to display.
    stub_type = request.GET.get("stub_type", "")
    if stub_type:
        issue = Issue.objects.select_related("parliament").get(id=issue_id)
        IssueUtilities.populate_issue_data([issue])

        monitored_issues = request.extravars["monitored_issues"]

        # Determine which template to use. Currently 'small' is the only
        # viable option aside from the default.
        if stub_type == "small":
            template_filename = "core/stub/%s/issue.html" % stub_type
        elif stub_type == "normal":
            template_filename = "core/stub/issue.html"
        else:
            raise Exception('Unknown stub type "%s"' % stub_type)

        stub_ctx = {
            "issue": issue,
            "user": request.user,
            "monitored_issues": monitored_issues,
        }

        ctx["html_content"] = render_to_string(
            template_filename, stub_ctx, request=request
        )

    return ctx


@login_required
@jsonize
def issue_monitor_menu(request, parliament_num):

    monitored_issues = request.extravars["monitored_issues"]

    html_content = render_to_string(
        "core/stub/issue_monitor_menuitems.html",
        {"monitored_issues": monitored_issues, "parliament_num": parliament_num},
    )
    monitored_issue_count = len(monitored_issues)

    ctx = {
        "html_content": html_content,
        "monitored_issue_count": monitored_issue_count,
    }
    return ctx


@login_required
@jsonize
def access_grant(request, friend_group_id=None, friend_id=None, issue_id=None):

    lookup_kwargs = {"user_id": request.user.id}

    if friend_group_id:
        lookup_kwargs["friend_group_id"] = friend_group_id
    elif friend_id:
        lookup_kwargs["friend_id"] = friend_id
    else:
        raise Http404

    try:
        access = Access.objects.get(**lookup_kwargs)
    except Access.DoesNotExist:
        access = Access(**lookup_kwargs)

    if "full_access" in request.GET:
        access.full_access = request.GET.get("full_access", False) == "true"

    access.save()

    if issue_id is not None and not access.full_access:
        access.issues.add(issue_id)

    access_list = (
        Access.objects.prefetch_related("issues__parliament")
        .select_related("friend__userprofile", "friend_group")
        .filter(user_id=request.user.id)
    )

    html_content = render_to_string(
        "core/stub/user_access_list.html", {"access_list": access_list}
    )

    ctx = {
        "full_access": access.full_access,
        "html_content": html_content,
    }
    return ctx


@login_required
@jsonize
def access_revoke(request, friend_group_id=None, friend_id=None, issue_id=None):

    lookup_kwargs = {"user_id": request.user.id}

    if friend_group_id:
        lookup_kwargs["friend_group_id"] = friend_group_id
    elif friend_id:
        lookup_kwargs["friend_id"] = friend_id
    else:
        raise Http404

    try:
        access = Access.objects.get(**lookup_kwargs)
    except Access.DoesNotExist:
        access = Access(**lookup_kwargs)

    if issue_id is None:
        access.delete()
    else:
        issue_id = int(issue_id)  # This should work or we should fail
        access.issues.remove(issue_id)

    access_list = (
        Access.objects.prefetch_related("issues__parliament")
        .select_related("friend__userprofile", "friend_group")
        .filter(user_id=request.user.id)
    )

    html_content = render_to_string(
        "core/stub/user_access_list.html", {"access_list": access_list}
    )

    ctx = {
        "html_content": html_content,
    }
    return ctx


@login_required
@jsonize
def membership_request(request, group_id, action):
    if action == "request":
        MembershipRequest.objects.get_or_create(
            user_id=request.user.id, group_id=group_id, status="pending"
        )
    elif action == "withdraw":
        MembershipRequest.objects.filter(
            user_id=request.user.id, group_id=group_id, status="pending"
        ).delete()
    else:
        raise Http404

    requestable_groups = Group.objects.exclude(
        membership_requests__user=request.user.id, membership_requests__status="pending"
    ).exclude(user__id=request.user.id)
    membership_requests = MembershipRequest.objects.select_related("group").filter(
        user_id=request.user.id, status="pending"
    )

    html_content = render_to_string(
        "core/stub/membership_requests.html",
        {
            "requestable_groups": requestable_groups,
            "membership_requests": membership_requests,
        },
    )

    ctx = {
        "html_content": html_content,
    }
    return ctx


@login_required
@jsonize
def process_membership_request(request):
    membership_request_id = int(request.POST.get("membership_request_id"))
    status = request.POST.get("status")

    if status not in ["accepted", "rejected"]:
        raise Http404

    membership_request = get_object_or_404(
        MembershipRequest, id=membership_request_id, group__user__id=request.user.id
    )

    membership_request.set_status(status, request.user)

    incoming_membership_requests = (
        MembershipRequest.objects.select_related("user__userprofile", "group")
        .exclude(user_id=request.user.id)
        .filter(group__user__id=request.user.id, status="pending")
    )

    html_content = render_to_string(
        "core/stub/incoming_membership_requests.html",
        {"incoming_membership_requests": incoming_membership_requests},
    )

    ctx = {
        "html_content": html_content,
    }
    return ctx


@login_required
@jsonize
def subscription_toggle(request, sub_type, sub_id):

    if sub_type not in ["party", "committee", "person", "category"]:
        raise Http404

    lookup = {
        "user": request.user,
        "%s_id" % sub_type: sub_id,
    }

    subscribed = None

    try:
        Subscription.objects.get(**lookup).delete()
        subscribed = False

    except Subscription.DoesNotExist:
        Subscription(**lookup).save()
        subscribed = True

    ctx = {
        "subscribed": subscribed,
    }
    return ctx


@login_required
@jsonize
def setting_set(request, setting_name, setting_value):
    allowed_settings = [
        "auto_monitor",
        "hide_concluded_from_monitors",
        "seen_if_worked_by_others",
    ]

    if setting_name not in allowed_settings:
        raise Http404

    # Boolean support.
    if setting_value.lower() in ["true", "false"]:
        setting_value = setting_value.lower() == "true"

    userprofile = UserProfile.objects.get(user_id=request.user.id)

    if getattr(userprofile, "setting_%s" % setting_name) != setting_value:
        setattr(userprofile, "setting_%s" % setting_name, setting_value)
        userprofile.save()
        value_changed = True
    else:
        value_changed = False

    ctx = {
        "value_changed": value_changed,
        "new_value": setting_value,
    }
    return ctx
