from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^$', views.verify, name='pay.verify'),
    url(r'^complete$', views.complete, name='pay.complete'),
)
