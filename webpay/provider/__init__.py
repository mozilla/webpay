from django.conf import settings

from webpay.base.logger import getLogger

log = getLogger('w.provider')


def get_start_url(trans_uid_pay):
    cnf = settings.PAY_URLS[settings.PAYMENT_PROVIDER]
    url = cnf['base'] + cnf['pay'].format(uid_pay=trans_uid_pay)

    log.info('Start pay provider payflow "{pr}" at: {url}'
             .format(pr=settings.PAYMENT_PROVIDER, url=url))
    return url
