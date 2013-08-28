from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^$', views.lobby, name='pay.lobby'),
    url(r'^fakepay$', views.fakepay, name='pay.fakepay'),
    # Be careful if you change this because it could be hard
    # coded into settings. See BANGO_PAY_URL.
    url(r'^fake-bango-url$', views.fake_bango_url,
        name='pay.fake_bango_url'),
    url(r'^bounce$', views.bounce, name='pay.bounce'),
    url(r'^simulate$', views.simulate, name='pay.simulate'),
    url(r'^super_simulate$', views.super_simulate, name='pay.super_simulate'),
    url(r'^wait_to_start$', views.wait_to_start, name='pay.wait_to_start'),
    url(r'^trans_start_url$', views.trans_start_url,
        name='pay.trans_start_url'),
)
