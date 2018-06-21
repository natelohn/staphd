from .models import ShiftPreference


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


def get_preferences_information(stapher):
	try:
		schedule = Schedule.objects.get(active = True)
		all_shifts = Shift.objects.filter(shift_set = schedule.shift_set)
	except:
		all_shifts = Shift.objects.all()
	all_special_flags = set()
	for shift in all_shifts:
		if shift.is_special() and not shift.is_unpaid():
			new_flags = [flag for flag in shift.flags.all() if flag.title not in 'special']
			all_special_flags.update(new_flags)
	preferences = ShiftPreference.objects.filter(stapher = stapher)
	pref_flags = [p.flag for p in preferences]
	flags_to_add = []
	for s_flag in sorted(all_special_flags, key = attrgetter('title')):
		if s_flag not in pref_flags:
			flags_to_add.append(s_flag)
	return [flags_to_add, preferences]