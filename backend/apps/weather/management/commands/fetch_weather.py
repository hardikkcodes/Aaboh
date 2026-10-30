from django.core.management.base import BaseCommand, CommandError

from apps.locations.models import Area
from apps.weather.services import WeatherIngestionError, ingest_open_meteo


class Command(BaseCommand):
    help = "Ingest current conditions and a 7-day forecast from Open-Meteo for an area."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--forecast-days", type=int, default=7)

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc
        try:
            result = ingest_open_meteo(area, forecast_days=options["forecast_days"])
        except WeatherIngestionError as exc:
            raise CommandError(f"Open-Meteo ingestion failed: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Open-Meteo: {result['written']} records written "
                f"(current={result['current']}, hourly={result['hourly']}, daily={result['daily']})"
            )
        )
