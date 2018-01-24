import datetime as dt
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models

from . import fields

User = settings.AUTH_USER_MODEL


class Qualification(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	title 			= models.CharField(max_length=100, unique=True, default='QUALIFICATION')

	def __str__(self):
		return "%s" % (self.title)

	def get_absolute_url(self):
		return reverse('settings')


class Flag(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	title 			= models.CharField(max_length=100, unique=True,default='TYPE OF SHIFT')

	def __str__(self):
		return "%s" % (self.title)

	def get_absolute_url(self):
		return reverse('settings')

class Stapher(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	first_name 		= models.CharField(max_length=100, default='FIRST NAME')
	last_name 		= models.CharField(max_length=100, default='LAST NAME')
	title 			= models.CharField(max_length=100, default='JOB TITLE')
	gender 			= fields.GenderField(blank=True)
	qualifications	= models.ManyToManyField(Qualification, blank=True)
	age 			= models.IntegerField(default=18)
	class_year 		= models.IntegerField(default=dt.datetime.today().year + 3)
	summers_worked 	= models.IntegerField(default=0)
	# Need to show shifts stapher is covering...
	# OneToManyField ??

	def __str__(self):
		return "%s %s" % (self.first_name, self.last_name)

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})


def get_default_start_time():
		now = dt.datetime.now()
		default_start = now.replace(minute=0, second=0)
		return default_start

def get_default_end_time():
		now = dt.datetime.now()
		end_hour = now.hour + 1
		default_end = now.replace(hour=end_hour, minute=0, second=0)
		return default_end


class Shift(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	title 			= models.CharField(max_length=100,default='NAME OF SHIFT')
	flag 			= models.ForeignKey(Flag, default=1, null=True, on_delete=models.SET_NULL)
	day 			= fields.DayOfTheWeekField(default=0)
	start			= models.TimeField(default=get_default_start_time)
	end		 		= models.TimeField(default=get_default_end_time)
	qualifications	= models.ManyToManyField(Qualification, blank=True)
	workers_needed	= models.IntegerField(default=1)
	difficult		= models.BooleanField(default=False)
	# Need to show stapher(s) covering the shifts...
	# OneToManyField ??

	def __str__(self):
		return "%s" % (self.title)

	def get_absolute_url(self):
		return reverse('schedules:shift-detail', kwargs={'pk': self.id})





