from django.conf import settings
from django.http import HttpResponse
import json


def jsonize(f):
    def wrapped(*args, **kwargs):
        try:
            m = f(*args, **kwargs)
            if isinstance(m, HttpResponse):
                return m
            m['ok'] = True
            return HttpResponse(json.dumps(m), content_type='text/json')
        except Exception as e:
            if settings.DEBUG:
                return HttpResponse(json.dumps(json_error(e.args[0])), content_type='text/json')
            else:
                raise

    return wrapped


def json_error(msg, ctx={}):
    ctx['ok'] = False
    ctx['error'] = msg
    return ctx

