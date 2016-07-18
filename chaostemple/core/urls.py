from django.conf.urls import patterns, include, url

from core import views
from core import json_views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^parliament/(?P<parliament_num>\d+)/$', views.parliament, name='parliament'),
    url(r'^parliament/(?P<parliament_num>\d+)/issues/$', views.parliament_issues, name='parliament_issues'),
    url(r'^parliament/(?P<parliament_num>\d+)/issue/(?P<issue_num>\d+)/$', views.parliament_issue, name='parliament_issue'),
    url(r'^parliament/(?P<parliament_num>\d+)/sessions/$', views.parliament_sessions, name='parliament_sessions'),
    url(r'^parliament/(?P<parliament_num>\d+)/session/(?P<session_num>\d+)/$', views.parliament_session, name='parliament_session'),
    url(r'^parliament/(?P<parliament_num>\d+)/committees/$', views.parliament_committees, name='parliament_committees'),
    url(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/$', views.parliament_committee, name='parliament_committee'),
    url(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/agenda/(?P<agenda_id>\d+)/$', views.parliament_committee_agenda, name='parliament_committee_agenda'),
    url(r'^parliament/(?P<parliament_num>\d+)/persons/$', views.parliament_persons, name='parliament_persons'),

    url(r'^person/(?P<slug>[A-Za-z\-]+)/$', views.person, name='person'),
    url(r'^person/(?P<slug>[A-Za-z\-]+)/(?P<subslug>[A-Za-z0-9\-]+)/$', views.person, name='person'),

    url(r'^user/home/(?P<username>\w+)/$', views.user_home, name='user_home'),
    url(r'^user/access/$', views.user_access, name='user_access'),
    url(r'^parliament/(?P<parliament_num>\d+)/user/issues/bookmarked/$', views.user_issues_bookmarked, name='user_issues_bookmarked'),
    url(r'^user/issues/incoming/$', views.user_issues_incoming, name='user_issues_incoming'),
    url(r'^parliament/(?P<parliament_num>\d+)/user/issues/open/$', views.user_issues_open, name='user_issues_open'),

    url(r'^json/dossier/(?P<dossier_id>\d+)/fieldstate/(?P<fieldname>.+)/$', json_views.dossier_fieldstate, name='json_dossier_fieldstate'),
    url(r'^json/dossier/(?P<dossier_id>\d+)/delete/$', json_views.delete_dossier, name='json_delete_dossier'),
    url(r'^json/issue/list/(?P<parliament_num>\d+)/$', json_views.list_issues, name='json_list_issues'),
    url(r'^json/issue/(?P<issue_id>\d+)/dossiers/delete/$', json_views.delete_issue_dossiers, name='json_delete_issue_dossiers'),

    url(r'^json/memo/(?P<dossier_id>\d+)/add/$', json_views.add_memo, name='json_add_memo'),
    url(r'^json/memo/(?P<memo_id>\d+)/edit/$', json_views.edit_memo, name='json_edit_memo'),
    url(r'^json/memo/(?P<memo_id>\d+)/delete/$', json_views.delete_memo, name='json_delete_memo'),
    url(r'^json/memo/sort/(?P<dossier_id>\d+)/', json_views.sort_memos, name='json_sort_memos'),

    url(r'^json/bookmark/issue/toggle/(?P<issue_id>\d+)/$', json_views.issue_bookmark_toggle, name='json_issue_bookmark_toggle'),
    url(r'^json/bookmark/issue/menu/$', json_views.issue_bookmark_menu, name='json_issue_bookmark_menu'),

    url(r'^json/user/access/grant/(?P<friend_id>\d+)/$', json_views.user_access_grant),
    url(r'^json/user/access/grant/(?P<friend_id>\d+)/issue/(?P<issue_id>\d+)$', json_views.user_access_grant),
    url(r'^json/user/access/revoke/(?P<friend_id>\d+)/$', json_views.user_access_revoke),
    url(r'^json/user/access/revoke/(?P<friend_id>\d+)/issue/(?P<issue_id>\d+)/$', json_views.user_access_revoke),
]

handler500 = 'core.views.error500'

