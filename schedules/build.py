from .models import Schedule, Staphing, Shift, Settings
from .sort import get_sorted_shifts
from .recommend import get_recommended_stapher

def get_free_staphers(staphers, shift, staphings):
	free_staphers = []
	for stapher in staphers:
		if stapher.is_free(staphings, shift):
			free_staphers.append(stapher)
	return free_staphers 


def build_schedules():
	settings = Settings.objects.get(pk = 1)
	schedule = Schedule()
	schedule.save()
	sorted_shift_info = get_sorted_shifts()
	staphings = []
	for shift_info in sorted_shift_info:
		ratio = shift_info[0]
		shift = shift_info[1]
		qualified_staphers = shift_info[2]
		free_and_qualified = get_free_staphers(qualified_staphers, shift, staphings)
		if len(free_and_qualified) == shift.left_to_cover(staphings):
			for stapher in free_and_qualified:
				staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
		else:
			stapher = get_recommended_stapher(free_and_qualified, shift, staphings, settings)
			if stapher:
				staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
	for staphing in staphings:
		staphing.save()
	print('+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=++=+=+=+=+')
	schedule.print()
	Schedule.objects.all().delete()
	print(f'Current Schedules in DB: {Schedule.objects.all()}')
	return schedule