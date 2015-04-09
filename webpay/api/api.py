from django import http

from rest_framework import response, viewsets

from webpay.api.base import BuyerIsLoggedIn
from webpay.base.logger import getLogger
from webpay.pay import tasks

log = getLogger('w.api')


class SimulateViewSet(viewsets.ViewSet):
    permission_classes = (BuyerIsLoggedIn,)

    def create(self, request):
        if not request.session.get('is_simulation', False):
            log.info('Request to simulate without a valid session')
            return http.HttpResponseForbidden()

        tasks.simulate_notify.delay(request.session['notes']['issuer_key'],
                                    request.session['notes']['pay_request'])

        return response.Response(status=204)
