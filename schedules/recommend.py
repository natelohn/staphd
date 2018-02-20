from .models import Staphing

def foo():
	print('foo')

def bar():
	print('bar')

def get_recommended_staphers(staphers, shift, schedule):
	func_arr = [foo, bar]
	for f in func_arr:
		f()
	return []
