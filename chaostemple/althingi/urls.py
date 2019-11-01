from django.conf.urls import url
from django.urls import path

from althingi import dataviews

urlpatterns = [
    path('calendars/', dataviews.calendars, name='calendars'),
    path('calendars/ical/', dataviews.ical, name='ical'),
    path('parliament/<int:parliament_num>/issues/csv/', dataviews.csv_parliament_issues, name='csv_parliament_issues'),
]

