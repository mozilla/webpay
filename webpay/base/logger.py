import logging
import threading

_local = threading.local()


def get_remote_addr():
    return getattr(_local, 'REMOTE_ADDR', '')


def get_transaction_id():
    return getattr(_local, 'TRANSACTION_ID', None)


def getLogger(name=None):
    logger = logging.getLogger(name)
    return WebpayAdapter(logger)


# For bonus points turn this into a filter.
class WebpayAdapter(logging.LoggerAdapter):
    """
    Adds user, transaction id, remote_addr to every logging message's kwargs.
    """

    def __init__(self, logger, extra=None):
        logging.LoggerAdapter.__init__(self, logger, extra or {})

    def process(self, msg, kwargs):
        kwargs['extra'] = {'REMOTE_ADDR': get_remote_addr(),
                           'TRANSACTION_ID': get_transaction_id()}
        return msg, kwargs


class WebpayFormatter(logging.Formatter):

    def format(self, record):
        for name in 'REMOTE_ADDR', 'TRANSACTION_ID':
            record.__dict__.setdefault(name, '')
        return logging.Formatter.format(self, record)


class LoggerMiddleware(object):

    def process_request(self, request):
        _local.TRANSACTION_ID = request.session.get('trans_id', '-')
        _local.REMOTE_ADDR = request.META.get('REMOTE_ADDR', '')
