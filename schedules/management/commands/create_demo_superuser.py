from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create the default demo superuser if it does not already exist.'

    def handle(self, *args, **options):
        if User.objects.filter(username='staphd').exists():
            self.stdout.write('Demo superuser already exists.')
            return
        User.objects.create_superuser('staphd', '', 'lamponthecake')
        self.stdout.write(self.style.SUCCESS('Demo superuser created.'))
