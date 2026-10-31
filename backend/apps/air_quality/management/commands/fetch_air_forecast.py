from django.core.management.base import BaseCommand, CommandError

from apps.air_quality.services import AirQualityIngestionError, ingest_air_forecast
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Ingest the modelled PM2.5 and PM10 forecast. No key required."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--all-areas", action="store_true")

    def handle(self, *args, **options):
        areas = Area.objects.filter(is_active=True)
        areas = areas if options["all_areas"] else areas.filter(slug=options["area"])
        if not areas:
            raise CommandError(f"Unknown area: {options['area']}")
        for area in areas:
            try:
                result = ingest_air_forecast(area)
            except AirQualityIngestionError as exc:
                raise CommandError(f"{area.slug}: {exc}") from exc
            self.stdout.write(self.style.SUCCESS(f"{area.slug}: {result['written']} air forecast hours"))
