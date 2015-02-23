from django.conf import settings
from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='pay.lobby'),
    url(r'^configure-transaction$', views.configure_transaction,
        name='pay.configure_transaction'),
    # Be careful if you change this because it could be hard
    # coded into settings. See settings.PAY_URLS.
    url(r'^fake-bango-url$', views.fake_bango_url,
        name='pay.fake_bango_url'),
    url(r'^bounce$', views.bounce, name='pay.bounce'),
    url(r'^simulate$', views.simulate, name='pay.simulate'),
    url(r'^super_simulate$', views.super_simulate, name='pay.super_simulate'),
    url(r'^wait_to_start$', views.wait_to_start, name='pay.wait_to_start'),
    url(r'^trans_start_url$', views.trans_start_url,
        name='pay.trans_start_url'),
    url(r'^callback_success_url$', views.callback_success_url,
        name='pay.callback_success_url'),
    url(r'^callback_error_url$', views.callback_error_url,
        name='pay.callback_error_url'),
)


if settings.DEBUG:

    from django.views.defaults import (
        page_not_found,
        permission_denied,
        server_error,
    )

    urlpatterns += patterns('',
        url(r'^403$', permission_denied, name="error_403"),
        url(r'^404$', page_not_found, name="error_404"),
        url(r'^500$', server_error, name="error_500"),
    )
