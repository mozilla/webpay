from django_paranoia.decorators import require_GET


@require_GET
def success(request):
    raise NotImplementedError


@require_GET
def error(request):
    raise NotImplementedError
