from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.views.decorators.cache import cache_page
from django.views.i18n import javascript_catalog

from funfactory.monkeypatches import patch
patch()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^mozpay/auth/', include('webpay.auth.urls')),
    (r'^mozpay/services/', include('webpay.services.urls')),
    (r'^mozpay/', include('webpay.pay.urls')),
    url('^mozpay/jsi18n.js$',
        cache_page(60 * 60 * 24 * 365)(javascript_catalog),
        {'domain': 'javascript', 'packages': ['webpay']}, name='jsi18n'),
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
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
