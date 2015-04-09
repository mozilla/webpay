from .base import *  # noqa
try:
    from .local import *  # noqa
except ImportError, exc:
    print 'No local.py imported, skipping.'
