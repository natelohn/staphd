from django.conf.urls import url

from . import views

app_name = 'schedules'
urlpatterns = [
	url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^staphers/$', views.StapherView.as_view(), name='staphers'),
    url(r'^shifts/$', views.ShiftView.as_view(), name='shifts'),
]