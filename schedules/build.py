from .models import Schedule, Staphing
from .sort import get_sorted_shifts
from .recommend import get_recommended_staphers

def add_shift(stapher, shift, schedule):
	staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
	staphing.save()

def get_free_staphers(staphers, shift, schedule):
	free_staphers = []
	for stapher in staphers:
		if stapher.is_free(shift, schedule):
			free_staphers.append(stapher)
	return free_staphers 


def build_schedules():
	schedule = Schedule()
	schedule.save()
	sorted_shift_info = get_sorted_shifts()
	for shift_info in sorted_shift_info:
		ratio = shift_info[0]
		shift = shift_info[1]
		qualified_staphers = shift_info[2]
		free_and_qualified = get_free_staphers(qualified_staphers, shift, schedule)
		recommended = get_recommended_staphers(free_and_qualified, shift, schedule)
	return