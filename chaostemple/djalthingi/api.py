from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from djalthingi.models import Document
from djalthingi.schema import DocumentSchema
from django.http import HttpRequest
from ninja import NinjaAPI
from typing import List

api = NinjaAPI()


@api.get("/laws", response=List[DocumentSchema])
def api_law(request: HttpRequest, parliament_num: int = CURRENT_PARLIAMENT_NUM, issue_num: int = 0):
    docs = Document.objects.select_related(
        "issue"
    ).filter(
        is_law=True,
        issue__parliament__parliament_num=parliament_num
    )

    if issue_num:
        docs = docs.filter(issue__issue_num=issue_num)

    return docs
