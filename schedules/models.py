import datetime
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from operator import attrgetter

from . import fields

# My models
class Qualification(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, unique = True, default = 'QUALIFICATION')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('schedules:qualification-settings')

	def delete(self, *args, **kwargs):
		cache.set('sorted_shifts', None, 0)
		super(Qualification, self).delete(*args, **kwargs)

class Flag(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, unique = True, default = 'TYPE OF SHIFT')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('schedules:flag-settings')

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
		cache.set('sorted_shifts', None, 0)
		super(Stapher, self).save(*args, **kwargs)
			

	def delete(self, *args, **kwargs):
		cache.set('sorted_shifts', None, 0)
		super(Stapher, self).delete(*args, **kwargs)

	def get_absolute_url(self):
		return reverse('schedules:stapher-detail', kwargs={'pk': self.id})

	def full_name(self):
		return f'{self.first_name} {self.last_name}'

	# This method only works for SSC Staph. (those w/ off day qualifications listed below)
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

	# Returns true if the stapher has a qualification w/ the same title as the string that was passed in
	def has_qualification(self, title):
		try:
			qualification = Qualification.objects.get(title = title)
			return qualification in self.qualifications.all()
		except:
			return False

	def is_qualified(self, shift):
		for qualification in shift.qualifications.all():
			if qualification not in self.qualifications.all():
				return False
		return True

	def free_during_window(self, staphings, day, start, end):
		for staphing in staphings:
			if staphing.stapher.id == self.id and staphing.shift.is_in_window(day, start, end):
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
			if staphing.stapher.id == self.id and staphing.shift.day == day and not staphing.shift.is_unpaid():
				hours += staphing.shift.length()
		return hours

	def total_hours(self, staphings):
		hours = datetime.timedelta()
		for staphing in staphings:
			if staphing.stapher.id == self.id and not staphing.shift.is_unpaid():
				hours += staphing.shift.length()
		return hours

	def overlapping_staphings(self, shift, staphings):
		overlapping_staphings = []
		for staphing in staphings:
			if staphing.stapher.id == self.id and staphing.shift.overlaps(shift):
				overlapping_staphings.append(staphing)
		return overlapping_staphings


	def get_previous_shift(self, shift, staphings):
		all_shifts = self.all_shifts_from_list(staphings)
		if not all_shifts:
			return None
		all_shifts.append(shift)
		all_shifts = sorted(all_shifts, key=attrgetter('day', 'start'))
		for i in range(0, len(all_shifts)):
			if all_shifts[i] == shift:
				if i == 0:
					return all_shifts[-1]
				else:
					return all_shifts[i - 1]

	def get_next_shift(self, shift, staphings):
		all_shifts = self.all_shifts_from_list(staphings)
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
	def all_shifts_from_qs(self, staphings):
		return [staphing.shift for staphing in staphings.filter(stapher__id = self.id)]

	def all_shifts_from_list(self, staphings):
		return [staphing.shift for staphing in staphings if self.id == staphing.stapher.id]

	# This returns a list of the person's shifts ordered chronologically.
	def ordered_shifts(self, staphings):
		return sorted(self.all_shifts_from_qs(staphings), key=attrgetter('day', 'start'))

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
				shifts_by_day[day] = sorted(shifts_by_day[day], key = attrgetter('start'))
			else:
				shifts_by_day[day] = []
		return shifts_by_day

	def get_staphing_during_time(self, day, time, staphings):
		for staphing in staphings:
			if self.id == staphing.stapher.id and staphing.shift.is_during_day_and_time(day, time):
				return staphing
		return None

# A class representing a set of shifts used at different times over the summer (mirco bopper week/conference season)
# - this will allow for different types of schedules
class ShiftSet(models.Model):
	DEAULT_PK 		= 1
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, default = 'NAME OF SHIFT SET')

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('schedules:set-add', kwargs = {'pk': self.id})

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
	shift_set 		= models.ForeignKey(ShiftSet, on_delete = models.CASCADE, default = ShiftSet.DEAULT_PK)

	def __str__(self):
		days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
		start_str = self.start.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()
		end_str = self.end.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()
		return f'{self.title} on {self.get_day_string()}, {start_str}-{end_str}'

	def save(self, *args, **kwargs):
		cache.set('sorted_shifts', None, 0)
		super(Shift, self).save(*args, **kwargs)

	def delete(self, *args, **kwargs):
		cache.set('sorted_shifts', None, 0)
		super(Shift, self).delete(*args, **kwargs)
			

	def get_absolute_url(self):
		return reverse('schedules:shift-detail', kwargs = {'pk': self.id})

	def is_during_time(self, time):
		return self.start <= time and self.end > time

	def is_during_day_and_time(self, day, time):
		return self.day == day and self.is_during_time(time)

	def is_in_window(self, day, start, end):
		if start > end:
			return False
		else:
			return self.day == day and self.start < end and self.end > start


	def overlaps(self, shift):
		return self.is_in_window(shift.day, shift.start, shift.end)
		

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

	def get_time_str(self):
		start_str = self.start.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()
		end_str = self.end.strftime("%I:%M%p").replace(':00','').lstrip('0').lower()
		return f'{start_str} - {end_str}'

	def get_excel_str(self):
		return f'{self.title} ({self.get_time_str()})'
	
	# Using these with a non-flag-title will cause a crash
	def has_flag(self, title):
		try:
			flag = Flag.objects.get(title = title)
			return flag in self.flags.all()
		except:
			return False

	def has_qualification(self, title):
		try:
			qualification = Qualification.objects.get(title = title)
			return qualification in self.qualifications.all()
		except:
			return False

	def is_unpaid(self):
		return self.has_flag('unpaid')

	def is_programming(self):
		return self.has_flag('programming')

	def has_no_qualifications(self):
		return bool(self.qualifications.all())

	def get_day_string(self):
		return ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][self.day]
	

# A class representing all shift/staph pairs for a user - this will allow for multiple schedules
class Schedule(models.Model):
	active			= models.BooleanField(default = True)
	title 			= models.CharField(max_length = 100, default = 'NAME OF SCHEDULE')
	shift_set 		= models.ForeignKey(ShiftSet, on_delete = models.CASCADE, default = ShiftSet.DEAULT_PK)
	updated_on		= models.DateTimeField(default = timezone.now)
	excel_updated	= models.DateTimeField(default = timezone.now)

	def __str__(self):
		return f'{self.title}'

	def get_absolute_url(self):
		return reverse('schedules:schedule-selected', kwargs={'pk': self.id})


	def save(self, *args, **kwargs):
		cache.set('sorted_shifts', None, 0)
		super(Schedule, self).save(*args, **kwargs)
			

	def delete(self, *args, **kwargs):
		cache.set('sorted_shifts', None, 0)
		latest_excel = Schedule.objects.latest('excel_updated')
		if latest_excel == self:
			cache.set('latest_excel_deleted', True, None)
		super(Schedule, self).delete(*args, **kwargs)

	def get_percent_complete(self):
		shifts_in_set = Shift.objects.filter(shift_set = self.shift_set)
		staphings = Staphing.objects.filter(schedule_id__exact = self.id)
		total_needed = 0
		for shift in shifts_in_set:
			total_needed += shift.workers_needed
		percent_complete = int((len(staphings) / total_needed)  * 100) if total_needed else 100
		if percent_complete == 0: percent_complete = '0'
		return percent_complete

	
# A class representing a single pair of Shift & Stapher in a specific schedule
class Staphing(models.Model):
	stapher 		= models.ForeignKey(Stapher, on_delete = models.CASCADE)
	shift 			= models.ForeignKey(Shift, on_delete = models.CASCADE)
	schedule 		= models.ForeignKey(Schedule, on_delete = models.CASCADE)

	def __str__(self):
		return f"{self.shift} from {self.stapher.first_name}'s schedule on \"{self.schedule}\""

	def get_absolute_url(self):
		return reverse('schedules:stapher-schedule', kwargs={'pk':self.stapher.id})

	def save(self, *args, **kwargs):
		schedule = self.schedule
		schedule.updated_on = timezone.now()
		schedule.save()
		super(Staphing, self).save(*args, **kwargs)
			

	def delete(self, *args, **kwargs):
		schedule = self.schedule
		schedule.updated_on = timezone.now()
		schedule.save()
		super(Staphing, self).delete(*args, **kwargs)

	

class Parameter(models.Model):
	title 			= models.CharField(max_length = 100, default = 'PARAMETER TITLE')
	description 	= models.CharField(max_length = 500, default = 'PARAMETER DESCRIPTION')
	use 			= models.BooleanField(default = False)
	rank			= models.IntegerField(unique = True, default = 1)
	function_id		= models.IntegerField(unique = True, default = 1)

	def __str__(self):
		return f'{self.description} | ("{self.title}")'

	def swap_rankings(self, other_parameter):
		if self.rank != -1 and other_parameter.rank != -1:
			temp_rank = -1
			my_rank = self.rank
			other_rank = other_parameter.rank
			self.rank = temp_rank
			self.save()
			other_parameter.rank = my_rank
			other_parameter.save()
			self.rank = other_rank
			self.save()



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

class Master(models.Model):
	title 			= models.CharField(max_length = 100, default = 'NAME OF MASTER')
	template		= models.CharField(max_length = 100, default = 'TEMPLATE')
	flags 			= models.ManyToManyField(Flag, blank = False)

	def __str__(self):
		return self.title

	# Returns a queryset of staphings that are in the master
	def get_master_staphings(self, staphings):
		my_flags = [f.id for f in self.flags.all()]
		return staphings.filter(shift__flags__in = my_flags)


	def shifts_at_time(self, staphings, day, time):
		master_staphings = self.staphings_in_master(staphings)
		shifts_at_time = master_staphings.filter(shift__day__exact = day, shift__start__lte = time, shift__start__gte = time)
		return shifts_at_time


	def is_standard(self):
		return self.template == 'master-template'








