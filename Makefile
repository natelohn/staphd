.PHONY: run setup load-demo

run:
	python manage.py runserver

setup:
	python manage.py migrate
	python manage.py createsuperuser

load-demo:
	python manage.py loaddata demo_staphers
