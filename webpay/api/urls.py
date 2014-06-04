from django.conf.urls import patterns, url

from api import PayViewSet, PinCheckViewSet, PinViewSet


# Disable these API's on production until we are sure they are working well.
urlpatterns = patterns('',
    url('^pin/$', PinViewSet.as_view({
            'get': 'retrieve', 'post': 'create', 'patch': 'update'}),
        name='pin'),
    url('^pin/check/', PinCheckViewSet.as_view({'post': 'check'}),
        name='pin.check'),
    url('^pay/',
        PayViewSet.as_view({'post': 'create', 'get': 'retrieve'}),
        name='pay'),
)
