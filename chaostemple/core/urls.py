from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'^$', 'core.views.home', name='home'),
    url(r'^parliament/(?P<parliament_num>\d+)/$', 'core.views.parliament', name='parliament'),
    url(r'^parliament/(?P<parliament_num>\d+)/issues/$', 'core.views.parliament_issues', name='parliament_issues'),
    url(r'^parliament/(?P<parliament_num>\d+)/issue/(?P<issue_num>\d+)/$', 'core.views.parliament_issue', name='parliament_issue'),
    url(r'^parliament/(?P<parliament_num>\d+)/sessions/$', 'core.views.parliament_sessions', name='parliament_sessions'),
    url(r'^parliament/(?P<parliament_num>\d+)/session/(?P<session_num>\d+)/$', 'core.views.parliament_session', name='parliament_session'),

    url(r'^json/dossier/(?P<dossier_id>\d+)/fieldstate/(?P<fieldname>.+)/$', 'core.json_views.dossier_fieldstate', name='json_dossier_fieldstate'),
    url(r'^json/dossier/(?P<dossier_id>\d+)/delete/$', 'core.json_views.delete_dossier', name='json_delete_dossier'),

    url(r'^json/bookmark/issue/toggle/(?P<issue_id>\d+)/$', 'core.json_views.issue_bookmark_toggle', name='json_issue_bookmark_toggle'),
    url(r'^json/bookmark/issue/menu/$', 'core.json_views.issue_bookmark_menu', name='json_issue_bookmark_menu'),
)

