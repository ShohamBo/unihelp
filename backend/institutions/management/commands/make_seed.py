from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Load seed data: institutions fixture"

    def handle(self, *args, **options):
        self.stdout.write("Loading institutions seed data...")
        call_command("loaddata", "seed_institutions")
        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully."))
