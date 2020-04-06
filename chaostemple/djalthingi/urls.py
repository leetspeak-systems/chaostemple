from django.conf.urls import url
from django.urls import path

from djalthingi import dataviews
from djalthingi import views

urlpatterns = [
    path('calendars/', dataviews.calendars, name='calendars'),
    path('calendars/ical/', dataviews.ical, name='ical'),
    path('parliament/<int:parliament_num>/issues/csv/', dataviews.csv_parliament_issues, name='csv_parliament_issues'),
    path('parliament/<int:parliament_num>/document/<int:doc_num>/', views.content_proxy_view, name='parliament_document'),
    path('parliament/<int:parliament_num>/review/<int:log_num>/', views.content_proxy_view, name='parliament_review'),
]
