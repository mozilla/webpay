from django.conf import settings
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# Run jingo monkey patch - see https://github.com/jbalogh/jingo#forms
import jingo.monkey
jingo.monkey.patch()

urlpatterns = patterns('',
    (r'^mozpay/auth/', include('webpay.auth.urls')),
    (r'^mozpay/bango/', include('webpay.bango.urls')),
    (r'^mozpay/services/', include('webpay.services.urls')),
    (r'^mozpay/', include('webpay.pay.urls')),
    # When jsi18n is ready, re-enable this.
    #url('^mozpay/jsi18n.js$',
    #    cache_page(60 * 60 * 24 * 365)(javascript_catalog),
    #    {'domain': 'javascript', 'packages': ['webpay']}, name='jsi18n'),
    url(r'^mozpay/pin/', include('webpay.pin.urls')),
    # This is served by marketplace.
    # (r'^robots\.txt$',
    #  lambda r: HttpResponse(
    #      "User-agent: *\n%s: /" % (
    #          'Allow' if settings.ENGAGE_ROBOTS else 'Disallow'
    #      ),
    #      mimetype="text/plain"
    #  )
    # ),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

if settings.TEMPLATE_DEBUG:

    from django.views.defaults import page_not_found, server_error
    from django.views.generic.base import TemplateView
    from urlparse import urlparse

    # Remove leading and trailing slashes so the regex matches.
    path = urlparse(settings.MEDIA_URL).path
    media_url = path.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        url(r'^404$', page_not_found, name="error_404"),
        url(r'^500$', server_error, name="error_500"),
        (r'^was-locked/$', TemplateView.as_view(
         template_name='pin/pin_was_locked.html')),
        (r'^is-locked/$', TemplateView.as_view(
         template_name='pin/pin_is_locked.html')),
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
