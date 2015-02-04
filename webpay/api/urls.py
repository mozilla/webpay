from django.conf.urls import include, patterns, url

from .api import PayViewSet, SimulateViewSet


# Disable these API's on production until we are sure they are working well.
urlpatterns = patterns(
    '',
    url('^pin/', include('webpay.pin.urls')),
    url('^pay/',
        PayViewSet.as_view({'post': 'create', 'get': 'retrieve'}),
        name='pay'),
    url('^simulate/',
        SimulateViewSet.as_view({'post': 'create'}),
        name='simulate'),
)
