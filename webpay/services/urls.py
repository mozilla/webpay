from django.conf.urls.defaults import patterns, url

import views

urlpatterns = patterns('',
    url(r'^monitor$', views.monitor, name='monitor'),
    url(r'^sig_check$', views.sig_check, name='services.sig_check'),
    url(r'^csp/report$', views.csp_report, name='csp.report'),
    url(r'^error_legend$', views.error_legend, name='services.error_legend'),
)
