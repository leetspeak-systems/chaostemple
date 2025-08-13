from djalthingi.models import Document
from djalthingi.models import Review
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404


def parliament_document(request: HttpRequest, parliament_num: int, doc_num: int):
    document: Document = get_object_or_404(
        Document,
        issue__parliament__parliament_num=parliament_num,
        doc_num=doc_num
    )

    content = document.html_content()

    response = HttpResponse(content)
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


def parliament_review(request: HttpRequest, parliament_num: int, log_num: int):
    review = get_object_or_404(
        Review,
        issue__parliament__parliament_num=parliament_num,
        log_num=log_num
    )

    content = review.pdf_content()

    response = HttpResponse(content, content_type="application/pdf")
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response
