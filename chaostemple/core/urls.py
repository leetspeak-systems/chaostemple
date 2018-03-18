from django.conf.urls import include, url
from django.urls import path

from core import views
from core import json_views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^day/$', views.day, name='day'),
    url(r'^day/(?P<input_date>(\d{4}-[01]\d-[0-3]\d){0,1})/$', views.day, name='day'),
    url(r'^upcoming/$', views.upcoming, name='upcoming'),
    url(r'^parliament/(?P<parliament_num>\d+)/$', views.parliament, name='parliament'),
    url(r'^parliament/(?P<parliament_num>\d+)/documents/new/', views.parliament_documents_new, name='parliament_documents_new'),
    url(r'^parliament/(?P<parliament_num>\d+)/issues/$', views.parliament_issues, name='parliament_issues'),
    url(r'^parliament/(?P<parliament_num>\d+)/issue/(?P<issue_num>\d+)/$', views.parliament_issue, name='parliament_issue'),
    url(r'^parliament/(?P<parliament_num>\d+)/sessions/$', views.parliament_sessions, name='parliament_sessions'),
    url(r'^parliament/(?P<parliament_num>\d+)/session/(?P<session_num>\d+)/$', views.parliament_session, name='parliament_session'),
    url(r'^parliament/(?P<parliament_num>\d+)/committees/$', views.parliament_committees, name='parliament_committees'),
    url(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/$', views.parliament_committee, name='parliament_committee'),
    url(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/agenda/(?P<agenda_id>\d+)/$', views.parliament_committee_agenda, name='parliament_committee_agenda'),
    url(r'^parliament/(?P<parliament_num>\d+)/parties/$', views.parliament_parties, name='parliament_parties'),
    url(r'^parliament/(?P<parliament_num>\d+)/persons/$', views.parliament_persons, name='parliament_persons'),
    url(r'^parliament/(?P<parliament_num>\d+)/persons/party/(?P<party_slug>[A-Za-z0-9\-]+)/$', views.parliament_persons, name='parliament_persons'),
    url(r'^parliament/missing-data/', views.parliament_missing_data, name='parliament_missing_data'),

    url(r'^person/(?P<slug>[A-Za-z\-]+)/$', views.person, name='person'),
    url(r'^person/(?P<slug>[A-Za-z\-]+)/(?P<subslug>[A-Za-z0-9\-]+)/$', views.person, name='person'),

    url(r'^user/home/(?P<username>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/$', views.user_home, name='user_home'),
    url(r'^user/home/(?P<username>\w+)/$', views.user_home, name='user_home'),
    url(r'^user/access/$', views.user_access, name='user_access'),
    url(r'^parliament/(?P<parliament_num>\d+)/user/issues/bookmarked/$', views.user_issues_bookmarked, name='user_issues_bookmarked'),
    url(r'^user/issues/incoming/$', views.user_issues_incoming, name='user_issues_incoming'),
    url(r'^parliament/(?P<parliament_num>\d+)/user/issues/open/$', views.user_issues_open, name='user_issues_open'),

    url(r'^json/proposer/(?P<proposer_id>\d+)/subproposers/$', json_views.proposer_subproposers, name='json_proposers_subproposers'),
    url(r'^json/issue/list/(?P<parliament_num>\d+)/$', json_views.list_issues, name='json_list_issues'),

    url(r'^json/bookmark/issue/toggle/(?P<issue_id>\d+)/$', json_views.issue_bookmark_toggle, name='json_issue_bookmark_toggle'),
    url(r'^json/bookmark/issue/menu/(?P<parliament_num>\d+)$', json_views.issue_bookmark_menu, name='json_issue_bookmark_menu'),

    path('json/access/grant/group/<int:friend_group_id>/', json_views.access_grant),
    path('json/access/grant/group/<int:friend_group_id>/issue/<int:issue_id>/', json_views.access_grant),
    path('json/access/grant/user/<int:friend_id>/', json_views.access_grant),
    path('json/access/grant/user/<int:friend_id>/issue/<int:issue_id>/', json_views.access_grant),
    path('json/access/revoke/group/<int:friend_group_id>/', json_views.access_revoke),
    path('json/access/revoke/group/<int:friend_group_id>/issue/<int:issue_id>/', json_views.access_revoke),
    path('json/access/revoke/user/<int:friend_id>/', json_views.access_revoke),
    path('json/access/revoke/user/<int:friend_id>/issue/<int:issue_id>/', json_views.access_revoke),
    path('json/access/request/membership/<int:group_id>/', json_views.membership_request, { 'action': 'request' }),
    path('json/access/withdraw/membership-request/<int:group_id>/',
        json_views.membership_request,
        { 'action': 'withdraw' }
    ),
    path('json/access/process/membership-request/', json_views.process_membership_request),

    url(r'^dossier/', include('dossier.urls')),
]

handler500 = 'core.views.error500'

