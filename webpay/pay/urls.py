from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^mozpay$', views.verify, name='verify'),
)
