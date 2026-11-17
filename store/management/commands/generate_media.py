from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Generate professional 1600px studio packshots for seeded products using Hugging Face."
    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")
    def handle(self, *args, **options):
        call_command("seed_data", generate_images=True, force=options["force"])
