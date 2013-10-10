from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.views.defaults import page_not_found, server_error
from django.views.generic.base import TemplateView
from urlparse import urlparse

from webpay.testing.persona import fake_include, fake_verify

# Remove leading and trailing slashes so the regex matches.
path = urlparse(settings.MEDIA_URL).path
media_url = path.lstrip('/').rstrip('/')

urlpatterns = patterns('',
    url(r'^404$', page_not_found, name="error_404"),
    url(r'^500$', server_error, name="error_500"),
    url(r'^include.js$', fake_include, name="fake_include"),
    url(r'^verify$', fake_verify, name="fake_verify"),
    (r'^was-locked/$', TemplateView.as_view(
     template_name='pin/pin_was_locked.html')),
    (r'^is-locked/$', TemplateView.as_view(
     template_name='pin/pin_is_locked.html')),
    (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
     {'document_root': settings.MEDIA_ROOT}),
)
