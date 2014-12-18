from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'^$', 'core.views.home', name='home'),
    url(r'^parliament/(?P<parliament_num>\d+)/$', 'core.views.parliament', name='parliament'),
    url(r'^parliament/(?P<parliament_num>\d+)/issues/$', 'core.views.parliament_issues', name='parliament_issues'),
    url(r'^parliament/(?P<parliament_num>\d+)/issue/(?P<issue_num>\d+)/$', 'core.views.parliament_issue', name='parliament_issue'),
    url(r'^parliament/(?P<parliament_num>\d+)/sessions/$', 'core.views.parliament_sessions', name='parliament_sessions'),
    url(r'^parliament/(?P<parliament_num>\d+)/session/(?P<session_num>\d+)/$', 'core.views.parliament_session', name='parliament_session'),

    url(r'^json/dossier/(?P<dossier_id>\d+)/attentionstate/$', 'core.json_views.attentionstate', name='json_attentionstate'),
    url(r'^json/dossier/(?P<dossier_id>\d+)/knowledgestate/$', 'core.json_views.knowledgestate', name='json_knowledgestate'),
    url(r'^json/dossier/(?P<dossier_id>\d+)/supportstate/$', 'core.json_views.supportstate', name='json_supportstate'),
    url(r'^json/dossier/(?P<dossier_id>\d+)/delete/$', 'core.json_views.delete_dossier', name='json_delete_dossier'),
)

