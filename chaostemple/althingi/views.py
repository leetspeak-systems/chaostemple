from althingi.models import Review
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

def parliament_review(request, parliament_num, log_num):
    '''
    A proxy function that will retrieve remote PDF content and pass it
    through, byte-for-byte. This is done to avoid cross-origin issues. In the
    future it may also support some kind of auto-download feature, where we
    download the PDF the first time it is accessed but retrieved from local
    disk in subsequent requests.
    '''
    review = get_object_or_404(Review, issue__parliament__parliament_num=parliament_num, log_num=log_num)

    # Check if we have a copy on the local disk.
    if review.pdf_filename:
        filepath = 'althingi/static/%s' % review.pdf_filename
        with open(filepath, 'rb') as f:
            content = f.read()
    else:
        response = requests.get(review.pdf_link())
        content = response.content

    return HttpResponse(content, content_type='application/pdf')
