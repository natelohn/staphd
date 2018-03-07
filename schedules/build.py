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

# Returns True if all shifts are covered, and a Recomendation if all shifts can not be covered.
def build_schedules(sorted_shifts, settings):
	schedule = Schedule()
	schedule.save()
	staphings = []
	for ratio, length, shift, qualified_staphers in sorted_shifts:
		# print(f'Ratio: {ratio}. Length: {length}\n{shift}\n{shift.workers_needed} needed, {len(qualified_staphers)} qualified.\n===========================')
		if not shift.is_covered(staphings):
			free_and_qualified = get_free_staphers(qualified_staphers, shift, staphings)

			# Fail case, not enough qualified staphers to cover the shift
			if len(free_and_qualified) < shift.left_to_cover(staphings):
				for staphing in staphings:
					staphing.save()
				print('\n\n**************************************************************\n*************************** FAILED ***************************\n**************************************************************')
				print(f'	{shift}')
				print(f'	{len(free_and_qualified)} free and qualified, {shift.workers_needed} needed, {shift.left_to_cover(staphings)} left.')
				schedule.save()
				schedule.print_overlaping_qualifiers(shift)
				print('=======================================================================')
				# return

			# In this system, all shifts that have no other options of people to cover them will be automatically scheduled.
			elif len(free_and_qualified) == shift.left_to_cover(staphings):
				# print(f'Auto Schedule: {shift}')
				for stapher in free_and_qualified:
					staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))

			# If the shift can be covered and there are more than just enough staphers to cover it, we make recommendations as to who should cover it
			# Depending on the settings, we either auto-schedule those recommendations or return them.
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
							# print(f'	Recomended Staphing Made: {stapher} takes {shift}')
							staphings.append(Staphing(stapher = stapher, shift = shift, schedule = schedule))
							recommendations_used += 1
					recommendations = recommendations[recommendations_used:]
	print('+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=++=+=+=+=+')
	uncovered_shifts = 0
	uncovered_staphings = 0
	total_staphings = 0
	for info in sorted_shifts:
		shift = info[2]
		if not shift.is_covered(staphings):
			uncovered_shifts += 1
			uncovered_staphings += shift.workers_needed
		total_staphings += shift.workers_needed

	print(f'{uncovered_staphings / total_staphings}% staphings uncovered.')
	print(f'{ uncovered_shifts / len(sorted_shifts)}% shifts uncovered.')
	Schedule.objects.all().delete()
	print(f'Current Schedules in DB: {Schedule.objects.all().count()}')
	print(f'Current Staphings in DB: {Staphing.objects.all().count()}')
	return True

