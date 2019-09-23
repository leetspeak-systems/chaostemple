from django.conf.urls import url
from django.urls import path

from althingi import dataviews

urlpatterns = [
    path('calendars/', dataviews.calendars, name='calendars'),
    path('calendars/ical/', dataviews.ical, name='ical')
]

