from django.conf.urls import patterns, url

from api import PayViewSet, PinViewSet


# Disable these API's on production until we are sure they are working well.
urlpatterns = patterns('',
    url('^pin/', PinViewSet.as_view({
        'get': 'retrieve', 'post': 'create', 'patch': 'update'}),
        name='pin'),
    url('^pay/', PayViewSet.as_view({'post': 'create'}), name='pay'),
)
