from django.conf import settings


def globals(request):

    ctx = request.extravars  # See chaostemple.middleware.ExtraVarsMiddleware

    ctx.update(
        {
            "PROJECT_NAME": settings.PROJECT_NAME,
            "PROJECT_VERSION": settings.PROJECT_VERSION,
            "LANGUAGE_CODE": settings.LANGUAGE_CODE,
            "FEATURES": settings.FEATURES,
        }
    )

    return ctx
