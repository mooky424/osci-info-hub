from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run full seed: partners and users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=3,
            help="Number of partners to seed (default: 3)",
        )

    def handle(self, *args, **options):
        count = max(1, options["count"])

        self.stdout.write(self.style.NOTICE("Running seed_partners..."))
        call_command("seed_partners", count=count)

        self.stdout.write(self.style.NOTICE("Running seed_users..."))
        call_command("seed_users")

        self.stdout.write(self.style.SUCCESS("Full seed completed."))
