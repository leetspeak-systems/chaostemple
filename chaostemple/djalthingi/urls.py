from django.urls import path

from djalthingi import dataviews
from djalthingi import views

urlpatterns = [
    path("calendars/", dataviews.calendars, name="calendars"),
    path("calendars/ical/", dataviews.ical, name="ical"),
    path(
        "parliament/<int:parliament_num>/issues/csv/",
        dataviews.csv_parliament_issues,
        name="csv_parliament_issues",
    ),
    path(
        "parliament/<int:parliament_num>/issue/<int:issue_num>/speeches/csv/",
        dataviews.csv_parliament_issue_speeches,
        name="csv_parliament_issue_speeches",
    ),
    path(
        "parliament/<int:parliament_num>/document/<int:doc_num>/",
        views.parliament_document,
        name="parliament_document",
    ),
    path(
        "parliament/<int:parliament_num>/review/<int:log_num>/",
        views.parliament_review,
        name="parliament_review",
    ),
]
