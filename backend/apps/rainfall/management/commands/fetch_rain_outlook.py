import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.locations.services.regions import reporting_areas
from apps.rainfall.outlook import refresh_outlook


class Command(BaseCommand):
    help = "Store rain chances for every reporting area from ensemble forecasts."

    def handle(self, *args, **options):
        written, failed = 0, 0
        for area in reporting_areas():
            try:
                written += int(refresh_outlook(area, now=timezone.now()) is not None)
            except (requests.RequestException, KeyError, ValueError) as exc:
                failed += 1
                self.stderr.write(f"{area.slug}: {type(exc).__name__}")
        self.stdout.write(f"Rain outlooks: {written} written, {failed} failed")
        if failed and not written:
            raise CommandError("No rain outlook could be read.")
