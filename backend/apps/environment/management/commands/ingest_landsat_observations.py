from django.core.management.base import BaseCommand, CommandError

from apps.environment.services import SatelliteIngestionError, ingest_landsat_observations
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Import an exported Landsat 8/9 observation table into the environmental tables."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", required=True, help="CSV exported from Earth Engine")
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--grid-version", default=None)
        parser.add_argument("--processing-version", default="landsat-c2l2-v1")
        parser.add_argument("--min-valid-fraction", type=float, default=0.5)

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc
        try:
            result = ingest_landsat_observations(
                area,
                options["dataset"],
                grid_version=options["grid_version"],
                processing_version=options["processing_version"],
                min_valid_pixel_fraction=options["min_valid_fraction"],
            )
        except SatelliteIngestionError as exc:
            raise CommandError(f"Satellite ingestion failed: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Landsat observations: {result['written']} written "
                f"(fetched={result['fetched']}, skipped={result['skipped']}, scenes={result['scenes']}, "
                f"grid={result['grid_version']})"
            )
        )
