import requests

from djalthingi.models import Document
from djalthingi.models import Review
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

def content_proxy_view(request, parliament_num, doc_num=None, log_num=None):
    '''
    A proxy function that will retrieve remote PDF content and pass it
    through, byte-for-byte. This may be done to avoid cross-origin issues when
    displaying content (documents or reviews) in an iframe, for example. In
    the future it may also support some kind of auto-download feature, where
    we download the PDF the first time it is accessed but retrieved from local
    disk in subsequent requests.
    '''

    if doc_num is not None:
        # We are retrieving a `document`.
        document = get_object_or_404(
            Document,
            issue__parliament__parliament_num=parliament_num,
            doc_num=doc_num
        )

        pdf_filename = document.pdf_filename
        pdf_link = document.pdf_link

    elif log_num is not None:
        # We are retrieving a `review`.
        review = get_object_or_404(
            Review,
            issue__parliament__parliament_num=parliament_num,
            log_num=log_num
        )

        pdf_filename = review.pdf_filename
        pdf_link = review.pdf_link

    # Check if we have a copy on the local disk.
    if pdf_filename:
        filepath = 'althingi/static/%s' % pdf_filename
        with open(filepath, 'rb') as f:
            content = f.read()
    else:
        response = requests.get(pdf_link())
        content = response.content

    return HttpResponse(content, content_type='application/pdf')
