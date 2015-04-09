from django.conf.urls import include, patterns, url

from .api import SimulateViewSet

urlpatterns = patterns(
    '',
    url('^pin/', include('webpay.pin.urls')),
    url('^pay/', include('webpay.pay.urls')),
    # TODO: move /simulate to /pay/simulate after updating Spartacus.
    url('^simulate/',
        SimulateViewSet.as_view({'post': 'create'}),
        name='simulate'),
)
