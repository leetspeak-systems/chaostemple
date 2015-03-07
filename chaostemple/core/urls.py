from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'^$', 'core.views.home', name='home'),
    url(r'^parliament/(?P<parliament_num>\d+)/$', 'core.views.parliament', name='parliament'),
    url(r'^parliament/(?P<parliament_num>\d+)/issues/$', 'core.views.parliament_issues', name='parliament_issues'),
    url(r'^parliament/(?P<parliament_num>\d+)/issue/(?P<issue_num>\d+)/$', 'core.views.parliament_issue', name='parliament_issue'),
    url(r'^parliament/(?P<parliament_num>\d+)/sessions/$', 'core.views.parliament_sessions', name='parliament_sessions'),
    url(r'^parliament/(?P<parliament_num>\d+)/session/(?P<session_num>\d+)/$', 'core.views.parliament_session', name='parliament_session'),
    url(r'^parliament/(?P<parliament_num>\d+)/committees/$', 'core.views.parliament_committees', name='parliament_committees'),
    url(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/$', 'core.views.parliament_committee', name='parliament_committee'),
    url(r'^parliament/(?P<parliament_num>\d+)/committee/(?P<committee_id>\d+)/agenda/(?P<agenda_id>\d+)/$', 'core.views.parliament_committee_agenda', name='parliament_committee_agenda'),

    url(r'^user/issues/bookmarked/$', 'core.views.user_issues_bookmarked', name='user_issues_bookmarked'),

    url(r'^json/dossier/(?P<dossier_id>\d+)/fieldstate/(?P<fieldname>.+)/$', 'core.json_views.dossier_fieldstate', name='json_dossier_fieldstate'),
    url(r'^json/dossier/(?P<dossier_id>\d+)/delete/$', 'core.json_views.delete_dossier', name='json_delete_dossier'),

    url(r'^json/memo/(?P<dossier_id>\d+)/add/$', 'core.json_views.add_memo', name='json_add_memo'),
    url(r'^json/memo/(?P<memo_id>\d+)/edit/$', 'core.json_views.edit_memo', name='json_edit_memo'),
    url(r'^json/memo/(?P<memo_id>\d+)/delete/$', 'core.json_views.delete_memo', name='json_delete_memo'),
    url(r'^json/memo/sort/(?P<dossier_id>\d+)/', 'core.json_views.sort_memos', name='json_sort_memos'),

    url(r'^json/bookmark/issue/toggle/(?P<issue_id>\d+)/$', 'core.json_views.issue_bookmark_toggle', name='json_issue_bookmark_toggle'),
    url(r'^json/bookmark/issue/menu/$', 'core.json_views.issue_bookmark_menu', name='json_issue_bookmark_menu'),
)

handler500 = 'core.views.error500'

