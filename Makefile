.PHONY: run setup load-demo reset-demo test install-hooks

run:
	python manage.py runserver

setup:
	python manage.py migrate

load-demo:
	python manage.py loaddata shiftset
	python manage.py loaddata flags
	python manage.py loaddata qualifications
	python manage.py loaddata shifts
	python manage.py loaddata demo_staphers
	python manage.py create_demo_superuser

reset-demo:
	python manage.py loaddata shiftset
	python manage.py loaddata flags
	python manage.py loaddata qualifications
	python manage.py loaddata shifts
	python manage.py reset_demo_staphers
	python manage.py create_demo_superuser

test:
	python manage.py test schedules --verbosity=1

install-hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	chmod +x .githooks/pre-push
	@echo "Git hooks installed."
