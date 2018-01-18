import datetime as dt
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models


User = settings.AUTH_USER_MODEL


class Stapher(models.Model):
	user 			= models.ForeignKey(User, default=1)
	first_name 		= models.CharField(max_length=100, default='FIRST')
	last_name 		= models.CharField(max_length=100, default='LAST')
	title 			= models.CharField(max_length=100, default='DEFAULT')
	gender 			= models.CharField(max_length=100, default='')
	qualifications	= models.TextField(default='') # Should this be it's own model??
	age 			= models.IntegerField(default=18)
	class_year 		= models.IntegerField(default=dt.datetime.today().year)
	summers_worked 	= models.IntegerField(default=0)
	# Need to show shifts stapher is covering...
	# OneToManyField ??

	def __str__(self):
		return self.first_name + self.last_name

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})

class Shift(models.Model):
	user 			= models.ForeignKey(User, default=1)
	title 			= models.CharField(max_length=100,default='DEFAULT')
	flag 			= models.CharField(max_length=100, default='')
	start			= models.DateTimeField(default=dt.datetime.now)
	end		 		= models.DateTimeField(default=dt.datetime.now)
	qualifications 	= models.TextField(default='') # Should this be it's own model??
	workers_needed	= models.IntegerField(default=0)
	difficult		= models.BooleanField(default=False)
	# Could change to below fields to a repeating value 
	# (ie. repeats daily, weekly, etc) and only use DateTime from start and end.
	on_sunday 		= models.BooleanField(default=False)
	on_monday 		= models.BooleanField(default=False)
	on_tuesday 		= models.BooleanField(default=False)
	on_wednesday 	= models.BooleanField(default=False)
	on_thursday 	= models.BooleanField(default=False)
	on_friday 		= models.BooleanField(default=False)
	on_saturday 	= models.BooleanField(default=False)
	# Need to show staphers covering the shifts...
	# OneToManyField ??

	def __str__(self):
		return self.title

