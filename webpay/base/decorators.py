import functools
import json

from django import http


def json_view(f=None, status_code=200):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            response = func(*args, **kw)
            if isinstance(response, http.HttpResponse):
                return response
            else:
                return http.HttpResponse(
                    json.dumps(response),
                    content_type='application/json',
                    status=status_code)
        return wrapper
    if f:
        return decorator(f)
    else:
        return decorator
