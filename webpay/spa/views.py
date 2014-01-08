from django.conf import settings
from django.shortcuts import render
from django.http import Http404


def index(request):
    """
    The index page for the single page app.
    """
    if not settings.ENABLE_SPA:
        raise Http404

    data = {}
    return render(request, 'spa.html', data)
