from operator import attrgetter

from .models import Schedule, Shift


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


def swap_shift_preferences(to_swap, preferences, up):
	for i in range(1, len(preferences)):
		pref_a = preferences[i - 1]
		pref_b = preferences[i]
		if pref_a.ranking <= to_swap.ranking and to_swap.ranking <= pref_b.ranking:
			print(f'pref_a = {pref_a}')
			print(f'pref_b = {pref_b}')
			print(f'to_swap = {to_swap}')
			print(f'up = {up}')
			if up and pref_a != to_swap:
				print('up!')
				swap(pref_a, to_swap)
			elif pref_b != to_swap:
				print('down!')
				swap(to_swap, pref_b)

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
	return sorted(all_special_flags, key = attrgetter('title'))