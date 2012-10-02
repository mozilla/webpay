from django import http


def verify(request):
    return http.HttpResponse('Hello world.')
