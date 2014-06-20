from .base import *
try:
    from .local import *
except ImportError, exc:
    print 'No local.py imported, skipping.'
