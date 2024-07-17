from django.conf import settings
from django.urls import include
from django.urls import path
from django.urls import re_path

from core import views
from core import dataviews

urlpatterns = [
    re_path(r'^$', views.home, name='home'),
    re_path(r'^day/$', views.day, name='day'),
    re_path(r'^day/(?P<input_date>(\d{4}-[01]\d-[0-3]\d){0,1})/$', views.day, name='day'),
    re_path(r'^upcoming/$', views.upcoming, name='upcoming'),
    path('parliaments/', views.parliaments, name='parliaments'),
    path('parliament/<int:parliament_num>/stats/', views.parliament_stats, name='parliament_stats'),
    path('parliament/<int:parliament_num>/', views.parliaments, name='parliament'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/documents/new/', views.parliament_documents_new, name='parliament_documents_new'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/issues/$', views.parliament_issues, name='parliament_issues'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/issue/(?P<issue_num>\d+)/$', views.parliament_issue, name='parliament_issue'),
    path('parliament/<int:parliament_num>/categories/', views.parliament_categories, name='parliament_categories'),
    path('parliament/<int:parliament_num>/category/<str:category_slug>/', views.parliament_category, name='parliament_category'),
    path('parliament/<int:parliament_num>/category/<str:category_slug>/issues/', views.parliament_category, {'view': 'issues'}, name='parliament_category_issues'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/sessions/$', views.parliament_sessions, name='parliament_sessions'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/session/(?P<session_num>\d+)/$', views.parliament_session, name='parliament_session'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/committees/$', views.parliament_committees, name='parliament_committees'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/$', views.parliament_committee, name='parliament_committee'),
    path('parliament/<int:parliament_num>/committee/<int:committee_id>/issues/', views.parliament_committee_issues, name='parliament_committee_issues'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/agenda/(?P<agenda_id>\d+)/$', views.parliament_committee_agenda, name='parliament_committee_agenda'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/parties/$', views.parliament_parties, name='parliament_parties'),
    path('parliament/<int:parliament_num>/party/<str:party_slug>/', views.parliament_party, name='parliament_party'),
    path('parliament/<int:parliament_num>/party/<str:party_slug>/issues/', views.parliament_party_issues, name='parliament_party_issues'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/persons/$', views.parliament_persons, name='parliament_persons'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/persons/party/(?P<party_slug>[A-Za-z0-9\-]+)/$', views.parliament_persons, name='parliament_persons'),
    path('parliament/<int:parliament_num>/issue-overview/<str:slug_type>/<str:slug>/', views.parliament_issue_overview, name='parliament_issue_overview'),
    path('parliament/<int:parliament_num>/issue-overview/<str:slug_type>/<str:slug>/<str:subslug>/', views.parliament_issue_overview, name='parliament_issue_overview'),
    re_path(r'^parliament/missing-data/', views.parliament_missing_data, name='parliament_missing_data'),

    re_path(r'^person/(?P<slug>[A-Za-z\-]+)/$', views.person, name='person'),
    re_path(r'^person/(?P<slug>[A-Za-z\-]+)/(?P<subslug>[A-Za-z0-9\-]+)/$', views.person, name='person'),

    re_path(r'^user/home/$', views.user_home, name='user_home'),
    re_path(r'^user/access/$', views.user_access, name='user_access'),
    re_path(r'^parliament/(?P<parliament_num>\d+)/user/issues/monitored/$', views.user_issues_monitored, name='user_issues_monitored'),

    re_path(r'^json/proposer/(?P<proposer_id>\d+)/subproposers/$', dataviews.proposer_subproposers, name='json_proposers_subproposers'),
    re_path(r'^json/issue/list/(?P<parliament_num>\d+)/$', dataviews.list_issues, name='json_list_issues'),
    path('json/parliament/<int:parliament_num>/document/<int:doc_num>/', dataviews.document, name='json_document'),
    path('json/parliament/<int:parliament_num>/review/<int:log_num>/', dataviews.review, name='json_review'),

    re_path(r'^json/monitor/issue/toggle/(?P<issue_id>\d+)/$', dataviews.issue_monitor_toggle, name='json_issue_monitor_toggle'),
    re_path(r'^json/monitor/issue/menu/(?P<parliament_num>\d+)$', dataviews.issue_monitor_menu, name='json_issue_monitor_menu'),

    path('json/settings/set/<str:setting_name>/<str:setting_value>/', dataviews.setting_set),

    path('json/access/grant/group/<int:friend_group_id>/', dataviews.access_grant),
    path('json/access/grant/group/<int:friend_group_id>/issue/<int:issue_id>/', dataviews.access_grant),
    path('json/access/grant/user/<int:friend_id>/', dataviews.access_grant),
    path('json/access/grant/user/<int:friend_id>/issue/<int:issue_id>/', dataviews.access_grant),
    path('json/access/revoke/group/<int:friend_group_id>/', dataviews.access_revoke),
    path('json/access/revoke/group/<int:friend_group_id>/issue/<int:issue_id>/', dataviews.access_revoke),
    path('json/access/revoke/user/<int:friend_id>/', dataviews.access_revoke),
    path('json/access/revoke/user/<int:friend_id>/issue/<int:issue_id>/', dataviews.access_revoke),
    path('json/access/request/membership/<int:group_id>/', dataviews.membership_request, { 'action': 'request' }),
    path('json/access/withdraw/membership-request/<int:group_id>/',
        dataviews.membership_request,
        { 'action': 'withdraw' }
    ),
    path('json/access/process/membership-request/', dataviews.process_membership_request),

    path('json/subscription/toggle/<str:sub_type>/<int:sub_id>/', dataviews.subscription_toggle),

    re_path(r'^dossier/', include('dossier.urls')),
]

if settings.FEATURES['incoming_issues']:
    urlpatterns += [
        re_path(r'^user/issues/incoming/$', views.user_issues_incoming, name='user_issues_incoming'),
        re_path(r'^parliament/(?P<parliament_num>\d+)/user/issues/open/$', views.user_issues_open, name='user_issues_open'),
    ]


handler500 = 'core.views.error500'

