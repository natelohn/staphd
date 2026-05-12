from django.core.management.base import BaseCommand
from django.core.management import call_command

from schedules.models import Stapher


class Command(BaseCommand):
    help = 'Delete all Stapher (and cascading Staphing) records, then reload from the demo fixture.'

    def handle(self, *args, **options):
        count, _ = Stapher.objects.all().delete()
        self.stdout.write(f'Deleted {count} record(s).')
        call_command('loaddata', 'demo_staphers')
        self.stdout.write(self.style.SUCCESS('Demo staphers loaded.'))
