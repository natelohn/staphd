import datetime
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models

from . import fields

# My models
class Qualification(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, unique = True, default = 'QUALIFICATION')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('settings')


class Flag(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, unique = True,default = 'TYPE OF SHIFT')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('settings')


class Stapher(models.Model):
	active			= models.BooleanField(default = True)
	first_name 		= models.CharField(max_length = 100, default = 'FIRST NAME')
	last_name 		= models.CharField(max_length = 100, default = 'LAST NAME')
	title 			= models.CharField(max_length = 100, default = 'JOB TITLE')
	gender 			= fields.GenderField(blank = True)
	qualifications	= models.ManyToManyField(Qualification, blank = True)
	age 			= models.IntegerField(default = 18)
	class_year 		= models.IntegerField(default = datetime.datetime.today().year + 3)
	summers_worked 	= models.IntegerField(default = 0)

	def __str__(self):
		return f'{self.first_name} {self.last_name}'

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})

	def is_qualified(self, shift):
		for qualification in shift.qualifications.all():
			if qualification not in self.qualifications.all():
				return False
		return True

	def is_free(self, shift, schedule):
		staphings = Staphing.objects.filter(stapher__id = self.id, schedule__id = schedule.id)
		for staphing in staphings:
			if staphing.shift.overlaps(shift):
				return False
		return True

	def hours_in_day(self, schedule, day):
		staphings = Staphing.objects.filter(schedule__id=schedule.id, stapher__id=self.id, shift__day=day)
		hours = datetime.timedelta()
		for staphing in staphings:
			hours += staphing.shift.length()
		return hours

	def total_hours(self, schedule):
		staphings = Staphing.objects.filter(schedule__id=schedule.id, stapher__id=self.id)
		hours = datetime.timedelta()
		for staphing in staphings:
			hours += staphing.shift.length()
		return hours


class Shift(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100,default = 'NAME OF SHIFT')
	flags 			= models.ManyToManyField(Flag, blank = False)
	day 			= fields.DayOfTheWeekField(default = 0)
	start			= models.TimeField(default = datetime.time(11, 0, 0, 0))
	end		 		= models.TimeField(default = datetime.time(12, 0, 0, 0))
	qualifications	= models.ManyToManyField(Qualification, blank = True)
	workers_needed	= models.IntegerField(default= 1)
	difficult		= models.BooleanField(default = False)

	def __str__(self):
		days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
		start_str = self.start.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()
		end_str = self.end.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()
		return f'{self.title} on {days[int(self.day)]}, {start_str}-{end_str}'

	def save(self, *args, **kwargs):
		# Start of shift must be before the end of shift and day must be between 0 and 6 (Sun-Sat)
		if self.start < self.end and self.day in range(0,6):
			super(Shift, self).save(*args, **kwargs)
		else:
			return

	def get_absolute_url(self):
		return reverse('schedules:shift-detail', kwargs = {'pk': self.id})

	def overlaps(self, shift):
		return int(self.day) == int(shift.day) and self.start < shift.end and self.end > shift.start

	def is_covered(self, staphings):
		staphings = Staphing.objects.filter(shift__id = self.id, schedule__id = schedule.id)
		return len(staphings) == self.workers_needed

	def length(self):
		start_td = datetime.timedelta(hours = self.start.hour, minutes = self.start.minute)
		end_td = datetime.timedelta(hours = self.end.hour, minutes = self.end.minute)
		return end_td - start_td

	def left_to_cover(self, schedule):
		count_of_covered = Staphing.objects.filter(shift__id = self.id, schedule__id = schedule.id).count()
		return self.workers_needed - count_of_covered



# A class representing all shift/staph pairs for a user - this will allow for multiple schedules
class Schedule(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100,default = 'NAME OF SCHEDULE')

	def __str__(self):
		return f'{self.title}'

	# TEMP!
	def print(self):
		staphers = Stapher.objects.all()
		for stapher in staphers:
			print(stapher)
			staphings = Staphing.objects.filter(schedule__id = self.id, stapher__id = stapher.id).order_by('shift__day', 'shift__start')
			for staphing in staphings:
				print('	' + str(staphing.shift))


# A class representing a single pair of Shift & Stapher in a specific schedule
class Staphing(models.Model):
	stapher 		= models.ForeignKey(Stapher, on_delete = models.CASCADE)
	shift 			= models.ForeignKey(Shift, on_delete = models.CASCADE)
	schedule 		= models.ForeignKey(Schedule, on_delete = models.CASCADE)

	def __str__(self):
		return f'{self.stapher.first_name}: {self.shift}'

class Parameter(models.Model):
	title 			= models.CharField(max_length = 100, default = 'PARAMETER TITLE')
	description 	= models.CharField(max_length = 500, default = 'PARAMETER DESCRIPTION')
	use 			= models.BooleanField(default = True)
	rank			= models.IntegerField(unique = True, default = 1)
	function_id		= models.IntegerField(unique = True, default = 1)

	def __str__(self):
		return f'{self.title}'

class Settings(models.Model):
	parameters		= models.ManyToManyField(Parameter, blank = False)
	auto_schedule 	= models.BooleanField(default = True)
	auto_threshold	= models.IntegerField(default = 1)
	tie_breaker		= fields.TieBreakerField(default = 0)

	def __str__(self):
		return 'Default Settings'





