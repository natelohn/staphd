from django.conf.urls import url

from . import views

# Temporary?
from django.views.generic import TemplateView

app_name = 'schedules'
urlpatterns = [
    url(r'^staphers/$', views.StapherListView.as_view(), name='staphers'),
    url(r'^staphers/create/$', views.StapherCreateView.as_view(), name='stapher-create'),
    url(r'^staphers/(?P<pk>[\w-]+)/$', views.StapherDetailView.as_view(), name='stapher-detail'),
    url(r'^staphers/(?P<pk>[\w-]+)/edit$', views.StapherUpdateView.as_view(), name='stapher-update'),
    url(r'^shifts/$', views.ShiftView.as_view(), name='shifts'),
]
