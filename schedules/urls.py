from django.conf.urls import url

from . import views

# Temporary?
from django.views.generic import TemplateView

app_name = 'schedules'
urlpatterns = [
	url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^staphers/$', views.StapherListView.as_view(), name='staphers'),
    url(r'^shifts/$', views.ShiftView.as_view(), name='shifts'),
]
