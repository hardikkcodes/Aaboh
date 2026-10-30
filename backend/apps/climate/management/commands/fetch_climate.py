from django.core.management.base import BaseCommand, CommandError

from apps.climate.services import ClimateIngestionError, ingest_climate
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Ingest ERA5-Land climate metrics (via Open-Meteo archive) for an area."

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--start-year", type=int, default=1991)
        parser.add_argument("--end-year", type=int, default=None)
        parser.add_argument("--baseline-start", type=int, default=1991)
        parser.add_argument("--baseline-end", type=int, default=2020)

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc
        try:
            result = ingest_climate(
                area,
                start_year=options["start_year"],
                end_year=options["end_year"],
                baseline_start=options["baseline_start"],
                baseline_end=options["baseline_end"],
            )
        except ClimateIngestionError as exc:
            raise CommandError(f"Climate ingestion failed: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Climate metrics: {result['written']} written across {result['years']} complete years "
                f"(baseline years: {result['baseline_years']})"
            )
        )
