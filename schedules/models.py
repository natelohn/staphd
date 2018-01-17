import datetime as dt
from django.conf import settings
from django.db import models



class Stapher(models.Model):
	first_name 		= models.CharField(max_length=100, default='FIRST')
	last_name 		= models.CharField(max_length=100, default='LAST')
	title 			= models.CharField(max_length=100, default='DEFAULT')
	gender 			= models.CharField(max_length=100, default='')
	qualifications	= models.TextField(default='')
	age 			= models.IntegerField(default=18)
	class_year 		= models.IntegerField(default=dt.datetime.today().year)
	summers_worked 	= models.IntegerField(default=0)
	# Need to show shifts stapher is covering...


	def __str__(self):
		return self.first_name + self.last_name

class Shift(models.Model):
	title 			= models.CharField(max_length=100,default='DEFAULT')
	flag 			= models.CharField(max_length=100, default='')
	start			= models.DateTimeField(default=dt.datetime.now)
	end		 		= models.DateTimeField(default=dt.datetime.now)
	qualifications 	= models.TextField(default='')
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

	def __str__(self):
		return self.title

