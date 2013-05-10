from django.conf import settings


def defaults(request):
    return {'session': request.session,
            'STATIC_URL': settings.STATIC_URL}
