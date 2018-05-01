web: gunicorn staphd.wsgi --log-file -
celeryworker: celery -A app.celery worker -E -B --loglevel=INFO