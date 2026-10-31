from django.core.management.base import BaseCommand, CommandError

from apps.air_quality.services import AirQualityIngestionError, ingest_air_forecast
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Ingest the modelled PM2.5 and PM10 forecast. No key required."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc
        try:
            result = ingest_air_forecast(area)
        except AirQualityIngestionError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Air forecast: {result['written']} hours written"))
