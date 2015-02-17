from django.conf.urls import patterns, url

from .api import PinCheckViewSet, PinViewSet


urlpatterns = patterns(
    '',
    url('^$', PinViewSet.as_view({'get': 'retrieve', 'post': 'create',
                                  'patch': 'update'}),
        name='pin'),
    url('^check/', PinCheckViewSet.as_view({'post': 'check'}),
        name='pin.check'),
)
