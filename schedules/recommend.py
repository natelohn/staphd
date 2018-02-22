from .parameters import get_parameter_scores, get_best_scores

def get_win_loss_info(best_scores, stapher_scores):
	wins_losses = []
	for i, score in enumerate(stapher_scores):
		wins_losses.append(score == best_scores[i])
	return wins_losses

def get_wins(item):
	return item[2].count(True)

# Return the stapher that is reccomended based on the settings.
def get_recommended_staphers(staphers, shift, staphings, settings):
	parameters = settings.parameters.filter(use=True).order_by('rank')[:1]
	all_scores = []
	best_scores = []
	# First we loop to determine everyones scores and what the best scores are...
	for stapher in staphers:
		parameter_scores = get_parameter_scores(stapher, shift, staphings, parameters)
		if best_scores == []:
			best_scores = parameter_scores
		else:
			best_scores = get_best_scores(parameters, parameter_scores, best_scores)
		all_scores.append([stapher, parameter_scores])
	# Next we loop to determine which staphers have the best scores...
	reccomendations = []
	for stapher, scores in all_scores:
		wins_losses = get_win_loss_info(best_scores, scores)
		reccomendations.append([stapher, scores, wins_losses])
	reccomendations.sort(reverse=True, key=get_wins)
	return reccomendations
