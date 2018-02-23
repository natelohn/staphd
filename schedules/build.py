from random import shuffle

from .models import Schedule, Staphing, Shift, Settings
from .sort import get_sorted_shifts
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

# Returns True if all shifts are covered, and a Recomendation if all shifts can not be covered.
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
		# In this system, all shifts that have no other options of people to cover them will be automatically scheduled.
		if len(free_and_qualified) == shift.left_to_cover(staphings):
			for stapher in free_and_qualified:
				staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
		else:
			recommendations = get_recommended_staphers(free_and_qualified, shift, staphings, settings)
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
						recommendations_used += 1
				recommendations = recommendations[recommendations_used:]
		if not shift.is_covered(staphings):
			print(f'{len(staphings)} shifts covered.')
			print(f'{shift.workers_needed} staphers needed. {shift.left_to_cover(staphings)} shifts left.')
			print(f'{len(qualified_staphers)} qualified staphers. {len(free_and_qualified)} of those staphers are free.')
			for staphing in staphings:
				staphing.save()
			print(f'{shift} NOT COVERED!')
			return [shift, recommendations]


	print('+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=++=+=+=+=+')
	schedule.print()
	print(f'{len(staphings)} shifts covered.')
	Schedule.objects.all().delete()
	print(f'Current Schedules in DB: {Schedule.objects.all().count()}')
	print(f'Current Staphings in DB: {Staphing.objects.all().count()}')
	
	return True

