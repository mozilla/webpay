from .base import *
try:
    from .local import *
except ImportError, exc:
    print '%s (did you rename settings/local.py-dist?)' % exc.args[0]
    from .local_filler import *
