from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.http import Http404
from django.http import HttpResponse
from django.urls import reverse
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import capfirst
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from althingi.models import Proposer

from core.breadcrumbs import append_to_crumb_string

from core.models import Access
from core.models import Issue
from core.models import IssueMonitor
from core.models import IssueUtilities
from core.models import MembershipRequest
from core.models import Subscription
from core.models import UserProfile
from core.utils import quote

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
def issue_monitor_toggle(request, issue_id):

    is_monitored = None

    try:
        issue_monitor = IssueMonitor.objects.get(user_id=request.user.id, issue_id=issue_id)
        issue_monitor.delete()
        is_monitored = False
    except IssueMonitor.DoesNotExist:
        issue_monitor = IssueMonitor.objects.create(user_id=request.user.id, issue_id=issue_id)
        is_monitored = True

    issue = Issue.objects.select_related('parliament').get(id=issue_id)
    IssueUtilities.populate_issue_data([issue])

    monitored_issues = request.extravars['monitored_issues']

    # Determine which template to use. Currently 'small' is the only viable
    # option aside from the default.
    stub_type = request.GET.get('stub_type', '')
    if stub_type == 'small':
        template_filename = 'core/stub/%s/issue.html' % stub_type
    else:
        template_filename = 'core/stub/issue.html'

    stub_ctx = {
        'issue': issue,
        'user': request.user,
        'monitored_issues': monitored_issues,
    }
    html_content = render_to_string(template_filename, stub_ctx, request=request)

    ctx = {
        'is_monitored': is_monitored,
        'issue_id': issue_id,
        'html_content': html_content,
    }
    return ctx


@login_required
@jsonize
def issue_monitor_menu(request, parliament_num):

    monitored_issues = request.extravars['monitored_issues']

    html_content = render_to_string('core/stub/issue_monitor_menuitems.html', {
        'monitored_issues': monitored_issues,
        'parliament_num': parliament_num
    })
    monitored_issue_count = len(monitored_issues)

    ctx = {
        'html_content': html_content,
        'monitored_issue_count': monitored_issue_count,
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
        'auto_monitor',
        'hide_concluded_from_monitors',
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


# This function returns CSV instead of JSON but is here because in reality,
# this views file is for data URLs, not just for JSON.
def csv_parliament_issues(request, parliament_num):

    # Standard SQL not only used for a massive performance boost but actually
    # also for clarity. The ORM way turned out to be way more convoluted and
    # involved a lot of advanced ORM features.
    issues = Issue.objects.raw(
        '''
        SELECT DISTINCT
            i.id,
            i.issue_num,
            i.issue_type,
            i.name,
            i.description,
            i.current_step,
            i.fate,
            prop_pers.name AS proposer_person,
            prop_com.name AS proposer_committee,
            i.from_government,
            mini.name AS minister,
            i.time_published,
            party.name AS party,
            com.name AS committee,
            rap_pers.name AS rapporteur,
            COUNT(cai.id) AS committee_meeting_count
        FROM
            -- Basic info
            althingi_issue AS i
            INNER JOIN althingi_parliament AS par ON par.id = i.parliament_id

            -- Proposers
            INNER JOIN althingi_proposer AS prop ON (
                prop.issue_id = i.id
                AND (
                    prop.order = 1
                    OR prop.order IS NULL
                )
            )
            LEFT OUTER JOIN althingi_person AS prop_pers ON (
                prop_pers.id = prop.person_id
            )
            LEFT OUTER JOIN althingi_committee AS prop_com ON (
                prop_com.id = prop.committee_id
            )

            -- Timing of person's seat, party etc.
            LEFT OUTER JOIN althingi_seat AS seat ON (
                seat.person_id = prop_pers.id
                AND (
                    seat.timing_out >= i.time_published
                    OR seat.timing_out IS NULL
                )
                AND seat.timing_in <= i.time_published
            )
            LEFT OUTER JOIN althingi_ministerseat AS mseat ON (
                mseat.person_id = prop_pers.id
                AND (
                    mseat.timing_out >= i.time_published
                    OR mseat.timing_out IS NULL
                )
                AND mseat.timing_in <= i.time_published
            )
			LEFT OUTER JOIN althingi_minister AS mini ON (
				mini.id = mseat.minister_id
            )
            LEFT OUTER JOIN althingi_party AS party ON (
                party.id = seat.party_id
                OR party.id = mseat.party_id
            )

            -- Committee
            LEFT OUTER JOIN althingi_committee AS com ON com.id = i.to_committee_id
            LEFT OUTER JOIN althingi_rapporteur AS rap ON rap.issue_id = i.id
            LEFT OUTER JOIN althingi_person AS rap_pers ON rap_pers.id = rap.person_id
            LEFT OUTER JOIN althingi_committeeagendaitem AS cai ON cai.issue_id = i.id
        WHERE
            par.parliament_num = %s
            AND i.issue_group = 'A'
        GROUP BY
            id,
            issue_num,
            issue_type,
            name,
            description,
            current_step,
            fate,
            proposer_person,
            proposer_committee,
            from_government,
            time_published,
            party,
            committee,
            rapporteur
        ORDER BY
            i.issue_num
        ''',
        [parliament_num]
    )

    first_line = [
        _('Nr'),
        _('Name'),
        _('Issue type'),
        _('Status'),
        _('Fate'),
        '%s (%s)' % (_('Proposer'), _('person')),
        '%s (%s)' % (_('Proposer'), _('committee')),
        _('Published'),
        _('Government issue'),
        _('Minister'),

        _('Party'),
        _('Committee'),
        _('Rapporteur'),
        _('Committee meetings'),
    ]

    lines = ['# "%s"' % '","'.join(first_line)]
    for issue in issues:

        # Prepare basic info.
        issue_num = str(issue.issue_num)
        if len(issue.description):
            name = quote('%s (%s)' % (capfirst(issue.name), issue.description))
        else:
            name = quote(capfirst(issue.name))
        issue_type = quote(capfirst(issue.get_issue_type_display()))
        status = quote(issue.get_current_step_display())
        fate = quote(capfirst(issue.get_fate_display()))
        proposer_person = quote(issue.proposer_person)
        proposer_committee = quote(issue.proposer_committee)
        published = quote(issue.time_published.strftime('%Y-%m-%d'))
        from_government = quote(_('Yes') if issue.from_government else _('No'))
        minister = quote(capfirst(issue.minister))
        party = quote(capfirst(issue.party))
        committee = quote(capfirst(issue.committee))
        rapporteur = quote(capfirst(issue.rapporteur))
        committee_meeting_count = str(issue.committee_meeting_count)

        # Construct line for issue.
        line = [
            issue_num,
            name,
            issue_type,
            status,
            fate,
            proposer_person,
            proposer_committee,
            published,
            from_government,
            minister,
            party,
            committee,
            rapporteur,
            committee_meeting_count,
        ]
        lines.append(','.join(line))

    return HttpResponse('\n'.join(lines) + '\n', content_type='text/csv')
