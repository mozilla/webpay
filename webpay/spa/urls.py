from django.conf import settings
from django.conf.urls import patterns, url

from webpay.spa import views

urlpatterns = patterns('',
    url(r'^mozpay/spa/(?P<provider_name>[^/]+)/wait-to-finish',
        views.wait_to_finish, name='wait_to_finish'),
    url(r'^mozpay/spa/(?:' + '|'.join(settings.SPA_URLS) + ')$',
        views.index, name='index'),
)
