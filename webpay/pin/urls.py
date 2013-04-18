from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',  # noqa
    url(r'^create$', views.create, name='pin.create'),
    url(r'^confirm$', views.confirm, name='pin.confirm'),
    url(r'^verify$', views.verify, name='pin.verify'),
    url(r'^reset$', views.reset_start, name='pin.reset_start'),
    url(r'^reset/create$', views.reset_new_pin, name='pin.reset_new_pin'),
    url(r'^reset/confirm$', views.reset_confirm, name='pin.reset_confirm'),
    url(r'^reset/cancel$', views.reset_cancel, name='pin.reset_cancel'),
)
