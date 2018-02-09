import datetime as dt
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models

from . import fields

User = settings.AUTH_USER_MODEL


# My models
class Qualification(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	# ^ Need to change to give each user their own DB
	active			= models.BooleanField(default=True)
	title 			= models.CharField(max_length=100, unique=True, default='QUALIFICATION')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('settings')


class Flag(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	# ^ Need to change to give each user their own DB
	active			= models.BooleanField(default=True)
	title 			= models.CharField(max_length=100, unique=True,default='TYPE OF SHIFT')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('settings')


class Stapher(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	# ^Need to change to give each user their own DB
	active			= models.BooleanField(default=True)
	first_name 		= models.CharField(max_length=100, default='FIRST NAME')
	last_name 		= models.CharField(max_length=100, default='LAST NAME')
	title 			= models.CharField(max_length=100, default='JOB TITLE')
	gender 			= fields.GenderField(blank=True)
	qualifications	= models.ManyToManyField(Qualification, blank=True)
	age 			= models.IntegerField(default=18)
	class_year 		= models.IntegerField(default=dt.datetime.today().year + 3)
	summers_worked 	= models.IntegerField(default=0)

	def __str__(self):
		return f'{self.first_name} {self.last_name}'

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})


class Shift(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE) 
	# ^Need to change to give each user their own DB
	active			= models.BooleanField(default=True)
	title 			= models.CharField(max_length=100,default='NAME OF SHIFT')
	flags 			= models.ManyToManyField(Flag, blank=False)
	day 			= fields.DayOfTheWeekField(default=0)
	start			= models.TimeField(default=dt.datetime(2018, 1, 1, 11, 0, 0, 0))
	end		 		= models.TimeField(default=dt.datetime(2018, 1, 1, 12, 0, 0, 0))
	qualifications	= models.ManyToManyField(Qualification, blank=True)
	workers_needed	= models.IntegerField(default=1)
	difficult		= models.BooleanField(default=False)

	def __str__(self):
		return f'{self.title} on {self.day}, {self.start} to {self.end}.'

	def save(self, *args, **kwargs):
		# Start of shift must be before the end of shift and day must be between 0 and 6 (Sun-Sat)
		if self.start < self.end and self.day in range(0,6):
			super(Shift, self).save(*args, **kwargs)
		else:
			return

	def get_absolute_url(self):
		return reverse('schedules:shift-detail', kwargs={'pk': self.id})


# A class representing a single pair of Shift & Stapher
class Staphing(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	# ^ Need to change to give each user their own DB
	stapher 		= models.ForeignKey(Stapher, on_delete=models.CASCADE)
	shift 			= models.ForeignKey(Shift, on_delete=models.CASCADE)

	def __str__(self):
		return f'{self.stapher.first_name}: {self.shift}'


# A class representing all shift/staph pairs for a user - this is to allow for multiple schedules in the future
class Schedule(models.Model):
	user 			= models.ForeignKey(User, default=1, on_delete=models.CASCADE)
	# ^ Need to change to give each user their own DB
	active			= models.BooleanField(default=True)
	title 			= models.CharField(max_length=100,default='NAME OF SCHEDULE')
	staphings		= models.ManyToManyField(Staphing)

	def __str__(self):
		return f'{self.title}'












