from django.conf.urls import url
from django.urls import path

from dossier import views

urlpatterns = [
    url(r'^(?P<dossier_id>\d+)/fieldstate/(?P<fieldname>.+)/$', views.dossier_fieldstate, name='json_dossier_fieldstate'),

    url(r'^issue/(?P<issue_id>\d+)/delete/$', views.delete_issue_dossiers, name='json_delete_issue_dossiers'),

    path('parliament/<int:parliament_num>/document/<int:doc_num>/', views.dossier, name='dossier_document'),
    path('parliament/<int:parliament_num>/document/<int:doc_num>/create/', views.create_dossier),
    path('parliament/<int:parliament_num>/document/<int:doc_num>/delete/', views.delete_dossier),
    path('parliament/<int:parliament_num>/review/<int:log_num>/', views.dossier, name='dossier_review'),
    path('parliament/<int:parliament_num>/review/<int:log_num>/create/', views.create_dossier),
    path('parliament/<int:parliament_num>/review/<int:log_num>/delete/', views.delete_dossier),

    path('<int:dossier_id>/set-notes/', views.set_notes, name='json_dossier_set_notes'),

    url(r'^memo/(?P<dossier_id>\d+)/add/$', views.add_memo, name='json_add_memo'),
    url(r'^memo/(?P<memo_id>\d+)/edit/$', views.edit_memo, name='json_edit_memo'),
    url(r'^memo/(?P<memo_id>\d+)/delete/$', views.delete_memo, name='json_delete_memo'),
    url(r'^memo/sort/(?P<dossier_id>\d+)/', views.sort_memos, name='json_sort_memos'),

]
