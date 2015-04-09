from django.conf.urls import patterns, url

from .api import (callback_error_url, callback_success_url, PayViewSet,
                  trans_start_url)


urlpatterns = patterns(
    '',
    url('^$',
        PayViewSet.as_view({'post': 'create', 'get': 'retrieve'}),
        name='pay'),
    url(r'^trans_start_url$', trans_start_url,
        name='pay.trans_start_url'),
    url(r'^callback_success_url$', callback_success_url,
        name='pay.callback_success_url'),
    url(r'^callback_error_url$', callback_error_url,
        name='pay.callback_error_url'),
)
