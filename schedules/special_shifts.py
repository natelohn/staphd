from operator import attrgetter

from .models import ShiftPreference, Schedule, Shift


def swap(pref_a, pref_b):
	temp_ranking = -1
	saved_ranking = pref_a.ranking

	pref_a.ranking = temp_ranking
	pref_a.save() # Not the final ranking

	temp_ranking = pref_b.ranking
	pref_b.ranking = saved_ranking # pref_a's ranking
	pref_b.save()

	pref_a.ranking = temp_ranking # pref_b's ranking
	pref_a.save()


def swap_shift_preferences(swap, preferences, up):
	for i in range(1, len(preferences)):
		pref_a = preferences[i - 1]
		pref_b = preferences[i]
		if pref_a.ranking <= swap.ranking and swap.ranking <= pref_b.ranking:
			if up and pref_a != swap:
				swap(pref_a, swap)
			elif pref_b != swap:
				swap(swap, pref_b)

def get_special_shift_flags():
	try:
		schedule = Schedule.objects.get(active = True)
		all_shifts = Shift.objects.filter(shift_set = schedule.shift_set)
	except:
		all_shifts = Shift.objects.all()
	all_special_flags = []
	for shift in all_shifts:
		if shift.is_special() and not shift.is_unpaid():
			new_flags = [flag for flag in shift.flags.all() if flag.title not in 'special' and flag not in all_special_flags]
			all_special_flags += new_flags
	return all_special_flags