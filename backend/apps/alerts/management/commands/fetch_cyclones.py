import requests
from django.core.management.base import BaseCommand, CommandError

from apps.alerts.cyclones import ingest_cyclones


class Command(BaseCommand):
    help = "Store active Bay of Bengal and Arabian Sea cyclones from GDACS."

    def handle(self, *args, **options):
        try:
            count = ingest_cyclones()
        except (requests.RequestException, ValueError) as exc:
            raise CommandError(f"GDACS could not be read: {type(exc).__name__}") from exc
        self.stdout.write(f"Active cyclones: {count}")
