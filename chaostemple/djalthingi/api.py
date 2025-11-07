from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from djalthingi.models import Document
from djalthingi.schema import DocumentSchema
from django.http import HttpRequest
from ninja import NinjaAPI
from typing import List

api = NinjaAPI()


@api.get("/law_documents", response=List[DocumentSchema])
def api_law_documents(request: HttpRequest, parliament_num: int = CURRENT_PARLIAMENT_NUM):
    docs = Document.objects.select_related(
        "issue"
    ).exclude(
        law_identifier=None
    ).filter(
        issue__parliament__parliament_num=parliament_num
    ).order_by(
        # FIXME: This order is unreliable, because if "100/x" comes after
        # "99/x" and they are both published on the same day, the "99/x" will
        # erroneously come after the "100/x". I'm not online at the moment so I
        # can't look up how to deal with this gracefully. Presumably
        # `law_identifier` can be filled with `0` up to a fixed string length
        # to make it reliably sortable.
        "law_time_published",
        "law_identifier",
    )

    return docs


@api.get("/law_document", response=DocumentSchema)
def api_law_document(request: HttpRequest, law_identifier: str):
    doc = Document.objects.get(law_identifier=law_identifier)
    return doc
