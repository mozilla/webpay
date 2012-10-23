from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^$', views.lobby, name='pay.lobby'),
    url(r'^complete$', views.complete, name='pay.complete'),
    url(r'^fakepay$', views.fakepay, name='pay.fakepay'),
)
