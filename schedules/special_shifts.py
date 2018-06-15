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
		if pref_a < swap and swap < pref_b:
			if up:
				swap(pref_a, swap)
			else:
				swap(swap, pref_b)


