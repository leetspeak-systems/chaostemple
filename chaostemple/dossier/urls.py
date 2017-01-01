from django.conf.urls import url

from dossier import views

urlpatterns = [
    url(r'^(?P<dossier_id>\d+)/fieldstate/(?P<fieldname>.+)/$', views.dossier_fieldstate, name='json_dossier_fieldstate'),
    url(r'^(?P<dossier_id>\d+)/delete/$', views.delete_dossier, name='json_delete_dossier'),

    url(r'^issue/(?P<issue_id>\d+)/delete/$', views.delete_issue_dossiers, name='json_delete_issue_dossiers'),

    url(r'^memo/(?P<dossier_id>\d+)/add/$', views.add_memo, name='json_add_memo'),
    url(r'^memo/(?P<memo_id>\d+)/edit/$', views.edit_memo, name='json_edit_memo'),
    url(r'^memo/(?P<memo_id>\d+)/delete/$', views.delete_memo, name='json_delete_memo'),
    url(r'^memo/sort/(?P<dossier_id>\d+)/', views.sort_memos, name='json_sort_memos'),

]
