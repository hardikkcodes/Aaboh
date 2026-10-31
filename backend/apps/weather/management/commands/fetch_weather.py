from django.core.management.base import BaseCommand, CommandError

from apps.locations.models import Area
from apps.weather.services import WeatherIngestionError, ingest_open_meteo


class Command(BaseCommand):
    help = "Ingest current conditions and a 7-day forecast from Open-Meteo for an area."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--forecast-days", type=int, default=7)
        parser.add_argument("--all-areas", action="store_true")

    def handle(self, *args, **options):
        areas = Area.objects.filter(is_active=True)
        areas = areas if options["all_areas"] else areas.filter(slug=options["area"])
        if not areas:
            raise CommandError(f"Unknown area: {options['area']}")
        for area in areas:
            try:
                result = ingest_open_meteo(area, forecast_days=options["forecast_days"])
            except WeatherIngestionError as exc:
                raise CommandError(f"{area.slug}: Open-Meteo ingestion failed: {exc}") from exc
            self.stdout.write(
                self.style.SUCCESS(
                    f"{area.slug}: {result['written']} records written "
                    f"(current={result['current']}, hourly={result['hourly']}, daily={result['daily']})"
                )
            )
