from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from apps.locations.models import Area
from apps.weather.services import WeatherIngestionError, ingest_weather_history


class Command(BaseCommand):
    help = "Ingest daily ERA5-Land archive weather (via Open-Meteo) for historical analysis."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--start", help="YYYY-MM-DD (default: 365 days ago)")
        parser.add_argument("--end", help="YYYY-MM-DD (default: yesterday)")

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc
        end = date.fromisoformat(options["end"]) if options.get("end") else date.today() - timedelta(days=1)
        start = date.fromisoformat(options["start"]) if options.get("start") else end - timedelta(days=365)
        try:
            result = ingest_weather_history(area, start=start, end=end)
        except WeatherIngestionError as exc:
            raise CommandError(f"Historical ingestion failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Historical weather: {result['written']} daily records written"))
