import datetime
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from operator import attrgetter

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

	def save(self, *args, **kwargs):
		cache.set('resort', True, None)
		super(Stapher, self).save(*args, **kwargs)
			

	def delete(self, *args, **kwargs):
		cache.set('resort', True, None)
		super(Stapher, self).delete(*args, **kwargs)

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})

	def full_name(self):
		return f'{self.first_name} {self.last_name}'

	# This method only works for SSC staph.
	def get_off_day(self):
		mon = Qualification.objects.get(title = 'sumo')
		tue = Qualification.objects.get(title = 'motue')
		wed = Qualification.objects.get(title = 'tueway')
		thu = Qualification.objects.get(title = 'wethur')
		fri = Qualification.objects.get(title = 'stirfry')
		quals = self.qualifications.all()
		if mon in quals:
			return 1
		elif tue in quals:
			return 2
		elif wed in quals:
			return 3
		elif thu in quals:
			return 4
		elif fri in quals:
			return 5
		return -1

	def is_qualified(self, shift):
		for qualification in shift.qualifications.all():
			if qualification not in self.qualifications.all():
				return False
		return True

	def is_free(self, staphings, shift):
		for staphing in staphings:
			if staphing.stapher.id == self.id and staphing.shift.overlaps(shift):
				return False
		return True

	def can_cover(self, shift, staphings):
		return self.is_qualified(shift) and self.is_free(staphings, shift)

	def hours_in_day(self, staphings, day):
		hours = datetime.timedelta()
		for staphing in staphings:
			if staphing.stapher.id == self.id and staphing.shift.day == day:
				hours += staphing.shift.length()
		return hours

	def total_hours(self, staphings):
		unpaid = Flag.objects.get(title = 'unpaid')
		hours = datetime.timedelta()
		for staphing in staphings:
			if staphing.stapher.id == self.id and unpaid not in staphing.shift.flags.all():
				hours += staphing.shift.length()
		return hours

	def overlapping_staphings(self, shift, staphings):
		overlapping_staphings = []
		for staphing in staphings:
			if staphing.stapher.id == self.id and staphing.shift.overlaps(shift):
				overlapping_staphings.append(staphing)
		return overlapping_staphings


	def get_previous_shift(self, shift, staphings):
		all_shifts = self.all_shifts(staphings)
		if not all_shifts:
			return None
		all_shifts.append(shift)
		all_shifts = sorted(all_shifts, key=attrgetter('day', 'start'))
		for i in range(0, len(all_shifts)):
			if all_shifts[i] == shift:
				if i == 0:
					return all_shifts[- 1]
				else:
					return all_shifts[i - 1]

	def get_next_shift(self, shift, staphings):
		all_shifts = self.all_shifts(staphings)
		if not all_shifts:
			return None
		all_shifts.append(shift)
		all_shifts = sorted(all_shifts, key=attrgetter('day', 'start'))
		for i in range(0, len(all_shifts)):
			if all_shifts[i] == shift:
				if i == len(all_shifts) - 1:
					return all_shifts[0]
				else:
					return all_shifts[i + 1]


	# This returns a list of the person's shifts 
	def all_shifts(self, staphings):
		all_shifts = []
		for staphing in staphings:
			if self.id == staphing.stapher.id:
				all_shifts.append(staphing.shift)
		return all_shifts

	# This returns a list of the person's shifts ordered chronologically.
	def ordered_shifts(self, staphings):
		all_shifts = []
		for staphing in staphings:
			if self.id == staphing.stapher.id:
				all_shifts.append(staphing.shift)
		return sorted(all_shifts, key=attrgetter('day', 'start'))

	# This returns a dictionary of ints (days) to the person's shifts for that day of the week ordered chronologically.
	def shifts_by_day(self, staphings):
		shifts_by_day = {}
		for staphing in staphings:
			if self.id == staphing.stapher.id:
				if staphing.shift.day not in shifts_by_day:
					shifts_by_day[staphing.shift.day] = [staphing.shift]
				else:
					shifts_by_day[staphing.shift.day].append(staphing.shift)
		for day in range(0, 7):
			if day in shifts_by_day:
				shifts_by_day[day] = sorted(shifts_by_day[day], key=attrgetter('start'))
			else:
				shifts_by_day[day] = []
		return shifts_by_day


class Shift(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, default = 'NAME OF SHIFT')
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
		return f'{self.title} on {days[self.day]}, {start_str}-{end_str}'

	def save(self, *args, **kwargs):
		if isinstance(self.day, str):
			print('its a str...')
			self.day = 1
			super(Shift, self).save(*args, **kwargs)
		# Start of shift must be before the end of shift and day must be between 0 and 6 (Sun-Sat)
		if self.start < self.end and self.day in range(0,6):
			cache.set('resort', True, None)
			super(Shift, self).save(*args, **kwargs)
		else:
			return

	def delete(self, *args, **kwargs):
		cache.set('resort', True, None)
		super(Shift, self).delete(*args, **kwargs)
			

	def get_absolute_url(self):
		return reverse('schedules:shift-detail', kwargs = {'pk': self.id})


	def overlaps(self, shift):
		return self.day == shift.day and self.start < shift.end and self.end > shift.start


	def is_covered(self, staphings):
		count_of_workers = 0
		for staphing in staphings:
			if self.id == staphing.shift.id:
				count_of_workers += 1
		return count_of_workers == self.workers_needed

	def length(self):
		start_td = datetime.timedelta(hours = self.start.hour, minutes = self.start.minute)
		end_td = datetime.timedelta(hours = self.end.hour, minutes = self.end.minute)
		return end_td - start_td

	def previous_day(self):
		if self.day == 0:
			return 6
		return self.day - 1

	def next_day(self):
		if self.day == 6:
			return 0
		return self.day + 1


	def left_to_cover(self, staphings):
		count_of_workers = 0
		for staphing in staphings:
			if self.id == staphing.shift.id:
				count_of_workers += 1
		return self.workers_needed - count_of_workers

	def has_matching_flags(self, shift):
		return bool(set(self.flags.all()) & set(shift.flags.all()))


	def has_exact_flags(self, shift):
		return set(self.flags.all()) == set(shift.flags.all())
	

# A class representing all shift/staph pairs for a user - this will allow for multiple schedules
class Schedule(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, default = 'NAME OF SCHEDULE')

	def __str__(self):
		return f'{self.title}'

	# TEMP!
	def print(self):
		staphers = Stapher.objects.all()
		days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thur', 'Fri', 'Sat']
		count_out_of_zone = 0
		count_in_zone = 0
		for stapher in staphers:
			staphings = Staphing.objects.filter(schedule__id = self.id, stapher__id = stapher.id).order_by('shift__day', 'shift__start')
			totsec = stapher.total_hours(staphings).total_seconds()
			h = totsec // 3600
			m = (totsec % 3600) // 60
			if h <= 44 or h >= 52:
				print(f'{stapher} - {h} hrs {m} mins')
				count_out_of_zone += 1
			else:
				count_in_zone += 1
		print(f'{count_in_zone} good schedules. {count_out_of_zone} bad schedules.')
			# last_day = 0
			# staphings_for_day = []
			# for staphing in staphings:
			# 	if staphing.shift.day != last_day:
			# 		totsec = stapher.total_hours(staphings_for_day).total_seconds()
			# 		h = totsec // 3600
			# 		m = (totsec % 3600) // 60
			# 		print(f'	{days[last_day]} - {h} hrs {m} mins')
			# 		for day_staphing in staphings_for_day:
			# 			print(f'		{str(day_staphing.shift)}')
			# 		staphings_for_day = []
			# 	last_day = staphing.shift.day
			# 	staphings_for_day.append(staphing)

	def print_overlaping_qualifiers(self, shift):
		staphers = Stapher.objects.all()
		for stapher in staphers:
			if stapher.is_qualified(shift):
				print(stapher)
				staphings = Staphing.objects.filter(schedule__id = self.id, stapher__id = stapher.id).order_by('shift__day', 'shift__start')
				for staphing in staphings:
					if shift.overlaps(staphing.shift):
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
	use 			= models.BooleanField(default = False)
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

	def break_ties_randomly(self):
		return int(self.tie_breaker) == 0

	def ranked_wins_break_ties(self):
		return int(self.tie_breaker) == 1

	def user_breaks_ties(self):
		return int(self.tie_breaker) == 2





