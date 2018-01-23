import datetime as dt
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models

from . import fields

User = settings.AUTH_USER_MODEL


class Stapher(models.Model):
	user 			= models.ForeignKey(User, default=1)
	first_name 		= models.CharField(max_length=100, default='FIRST')
	last_name 		= models.CharField(max_length=100, default='LAST')
	title 			= models.CharField(max_length=100, default='DEFAULT')
	gender 			= models.CharField(max_length=100, default='none')
	qualifications	= models.TextField(default='none') # Should this be it's own model??
	age 			= models.IntegerField(default=18)
	class_year 		= models.IntegerField(default=dt.datetime.today().year)
	summers_worked 	= models.IntegerField(default=0)
	# Need to show shifts stapher is covering...
	# OneToManyField ??

	def __str__(self):
		return self.first_name + ' ' +  self.last_name

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})

class Shift(models.Model):
	user 			= models.ForeignKey(User, default=1)
	title 			= models.CharField(max_length=100,default='DEFAULT')
	flag 			= models.CharField(max_length=100, default='flag')
	day 			= fields.DayOfTheWeekField(default=0)
	start			= models.TimeField(default=dt.datetime.now)
	end		 		= models.TimeField(default=dt.datetime.now)
	qualifications 	= models.TextField(default='none') # Should this be it's own model??
	workers_needed	= models.IntegerField(default=0)
	difficult		= models.BooleanField(default=False)
	# Need to show stapher(s) covering the shifts...
	# OneToManyField ??

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('schedules:shift-detail', kwargs={'pk': self.id})

