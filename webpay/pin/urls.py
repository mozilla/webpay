from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^create', views.create, name='pin.create'),
    url(r'^confirm', views.confirm, name='pin.confirm'),
    url(r'^verify', views.verify, name='pin.verify'),
    url(r'^change', views.change, name='pin.change'),
)
