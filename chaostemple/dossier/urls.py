from django.conf.urls import url
from django.urls import path

from dossier import views

urlpatterns = [
    path('parliament/<int:parliament_num>/document/<int:doc_num>/fieldstate/<str:fieldname>/', views.dossier_fieldstate),
    path('parliament/<int:parliament_num>/review/<int:log_num>/fieldstate/<str:fieldname>/', views.dossier_fieldstate),

    url(r'^issue/(?P<issue_id>\d+)/delete/$', views.delete_issue_dossiers, name='json_delete_issue_dossiers'),

    path('parliament/<int:parliament_num>/document/<int:doc_num>/', views.dossier, name='dossier_document'),
    path('parliament/<int:parliament_num>/document/<int:doc_num>/create/', views.create_dossier),
    path('parliament/<int:parliament_num>/document/<int:doc_num>/delete/', views.delete_dossier),
    path('parliament/<int:parliament_num>/review/<int:log_num>/', views.dossier, name='dossier_review'),
    path('parliament/<int:parliament_num>/review/<int:log_num>/create/', views.create_dossier),
    path('parliament/<int:parliament_num>/review/<int:log_num>/delete/', views.delete_dossier),

    path('parliament/<int:parliament_num>/document/<int:doc_num>/set-notes/', views.set_notes),
    path('parliament/<int:parliament_num>/review/<int:log_num>/set-notes/', views.set_notes),

]
