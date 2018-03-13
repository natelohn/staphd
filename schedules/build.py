from operator import itemgetter
from random import shuffle


from .models import Schedule, Staphing
from .recommend import get_recommended_staphers


def get_free_staphers(staphers, shift, staphings):
	free_staphers = []
	for stapher in staphers:
		if stapher.is_free(staphings, shift):
			free_staphers.append(stapher)
	return free_staphers 

def get_tied_recs(recommendations, last_rec_loc):
	lowest_recommended = recommendations[last_rec_loc]
	lowest_recommended_wins = lowest_recommended[2].count(True)
	tied_recs = []
	for rec in recommendations:
		wins = rec[2].count(True)
		if wins == lowest_recommended_wins:
			tied_recs.append(rec)
	return tied_recs

def get_higher_ranked_wins(item):
	for rank, win in enumerate(item[2]):
		if win:
			return rank
	return len(item[2])
			



def resolve_ties(settings, recommendations, tied_recs):
	beat_tied_recs = []
	for i, rec in enumerate(recommendations):
		if rec in tied_recs:
			break
		beat_tied_recs = recommendations[:i]
	start_of_tie = len(beat_tied_recs)
	end_of_tie = start_of_tie + len(tied_recs) - 1
	reordered_staphers = recommendations[start_of_tie:end_of_tie]
	if settings.break_ties_randomly():
		shuffle(reordered_staphers)
	elif settings.ranked_wins_break_ties():
		reordered_staphers.sort(key=get_higher_ranked_wins)
	new_recommendations = beat_tied_recs + reordered_staphers
	if len(new_recommendations) == len(recommendations):
		non_tied_losers = []
	else:
		non_tied_losers = recommendations[end_of_tie + 1:]
	return new_recommendations + non_tied_losers
	

# Returns a schedule of given the staphers, shifts and settings.
# Currently is not guarenteed to cover every shift.
# Covering 99% of shift w/ the 2017 shifts and staphers.
def build_schedules(sorted_shifts, settings):
	schedule = Schedule()
	schedule.save()
	staphings = []
	count_of_shifts = len(sorted_shifts)
	counter = 0
	all_shifts = [shift[0] for shift in sorted_shifts]
	for shift, qualified_staphers in sorted_shifts:
		print(f'{round(((counter / count_of_shifts) * 100), 2)}% of shifts seen. Current Shift: {shift}...')
		if not shift.is_covered(staphings):
			free_and_qualified = get_free_staphers(qualified_staphers, shift, staphings)

			# Fail case, not enough qualified staphers to cover the shift
			if len(free_and_qualified) < shift.left_to_cover(staphings):
				for stapher in free_and_qualified:
					# print(f'---> Auto Schedule: {Staphing(stapher = stapher, shift = shift, schedule = schedule)}. (shift not fully scheudled)')
					staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
				# staphings = find_easiest_fix(shift, qualified_staphers, staphings)

			# In this system, all shifts that have no other options of people to cover them will be automatically scheduled.
			elif len(free_and_qualified) == shift.left_to_cover(staphings):
				for stapher in free_and_qualified:
					staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
					# print(f'---> Auto Schedule: {Staphing(stapher = stapher, shift = shift, schedule = schedule)}')
			# If the shift can be covered and there are more than just enough staphers to cover it, we make recommendations as to who should cover it
			# Depending on the settings, we either auto-schedule those recommendations or return them.
			else:
				recommendations = get_recommended_staphers(free_and_qualified, shift, staphings, settings, all_shifts)
				if not settings.auto_schedule:
					break
				else:
					tied_recs = get_tied_recs(recommendations, shift.left_to_cover(staphings) - 1)
					if len(tied_recs) != 0:
						if settings.user_breaks_ties():
							break
						else:
							recommendations = resolve_ties(settings, recommendations, tied_recs)
					recommendations_used = 0
					for stapher, scores, wins_losses in recommendations:
						wins = wins_losses.count(True)
						if wins >= settings.auto_threshold and not shift.is_covered(staphings):
							staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
							# print(f'---> Recomended Staphing Made: {Staphing(stapher = stapher, shift = shift, schedule = schedule)}')
							recommendations_used += 1
					recommendations = recommendations[recommendations_used:]
		counter += 1

	# Finally we save all the staphings that were made and return the Scheudle
	for staphing in staphings:
		staphing.save()
	return schedule

