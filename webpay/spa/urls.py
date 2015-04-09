from django.conf import settings
from django.conf.urls import patterns, url

from webpay.spa import views

urlpatterns = patterns(
    '',
    url(r'^(?P<view_name>' + '|'.join(settings.SPA_URLS) + ')$',
        views.index, name='index'),
)
