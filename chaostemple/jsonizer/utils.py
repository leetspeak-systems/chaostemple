from django.conf import settings
from django.http import HttpResponse
import json
import traceback


def jsonize(f):
    def wrapped(*args, **kwargs):
        try:
            m = f(*args, **kwargs)
            if isinstance(m, HttpResponse):
                return m
            m["ok"] = True
            return HttpResponse(json.dumps(m), content_type="text/json")
        except Exception as e:
            if settings.DEBUG:
                output = "%s\n\n%s" % (e.args[0], traceback.format_exc())
                return HttpResponse(
                    json.dumps(json_error(output)), content_type="text/json"
                )
            else:
                raise

    return wrapped


def json_error(msg, ctx={}):
    ctx["ok"] = False
    ctx["error"] = msg
    return ctx
