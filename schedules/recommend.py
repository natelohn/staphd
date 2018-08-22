from .parameters import get_parameter_scores, get_best_scores

def get_win_loss_info(best_scores, stapher_scores):
	wins_losses = []
	for i, score in enumerate(stapher_scores):
		wins_losses.append(score == best_scores[i])
	return wins_losses

def get_wins(item):
	return item[2].count(True)

# Returns a list of staphers that is reccomended based on the settings.
def get_recommended_staphers(staphers, shift, staphings, settings, all_shifts):
	print(f'staphers = {staphers}')
	print(f'shift = {shift}')
	print(f'staphings = {staphings}')
	print(f'settings = {settings}')
	print(f'all_shifts = {all_shifts}')

	parameters = settings.parameters.all().order_by('rank')
	all_scores = []
	best_scores = []

	# First we loop to determine everyones scores and what the best scores are.
	for stapher in staphers:
		parameter_scores = get_parameter_scores(stapher, shift, staphings, parameters, all_shifts)
		print(f'parameter_scores = {parameter_scores}')
		if best_scores == []:
			best_scores = parameter_scores
			print(f'Initial Best Scores = {best_scores}')
		else:
			best_scores = get_best_scores(parameters, parameter_scores, best_scores)
			print(f'Best Scores = {best_scores}')
		all_scores.append([stapher, parameter_scores[:]])

	# Next we loop to determine which staphers have the best scores.
	reccomendations = []
	for stapher, scores in all_scores:
		wins_losses = get_win_loss_info(best_scores, scores)
		print(f'wins_losses = {wins_losses}')
		reccomendations.append([stapher, scores, wins_losses[:]])
		print(f'reccomendations = {reccomendations}')

	# Finally, we return a list of staphers, scores, and wins/losses with the stapher with the most wins at the front.
	reccomendations.sort(reverse = True, key = get_wins)
	print(f'reccomendations post sort = {reccomendations}')
	return reccomendations