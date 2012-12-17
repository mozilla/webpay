from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^$', views.lobby, name='pay.lobby'),
    url(r'^complete$', views.complete, name='pay.complete'),
    url(r'^fakepay$', views.fakepay, name='pay.fakepay'),
    # Be careful if you change this because it could be hard
    # coded into settings. See BANGO_PAY_URL.
    url(r'^fake-bango-url$', views.fake_bango_url,
        name='pay.fake_bango_url'),
    url(r'^wait_to_start$', views.wait_to_start, name='pay.wait_to_start'),
    url(r'^trans_start_url$', views.trans_start_url,
        name='pay.trans_start_url'),
)
