from django.core.management.base import BaseCommand, CommandError

from apps.environment.terrain import ingest_terrain
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Store cell terrain exported by ml/src/waterlogging/terrain_export.py."

    def add_arguments(self, parser):
        parser.add_argument("--dataset", required=True)
        parser.add_argument("--area", default="kolkata")

    def handle(self, *args, **options):
        area = Area.objects.filter(slug=options["area"]).first()
        if area is None:
            raise CommandError("Area not found.")
        self.stdout.write(f"Terrain cells: {ingest_terrain(area, options['dataset'])} written")
