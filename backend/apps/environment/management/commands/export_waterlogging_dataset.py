import csv

from django.core.management.base import BaseCommand, CommandError

from apps.environment.terrain import DATASET_COLUMNS, waterlogging_rows
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Write the waterlogging training table from reports, terrain and historical rain."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
        parser.add_argument("--area", default="kolkata")

    def handle(self, *args, **options):
        area = Area.objects.filter(slug=options["area"]).first()
        if area is None:
            raise CommandError("Area not found.")
        rows = waterlogging_rows(area)
        with open(options["output"], "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=DATASET_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        flooded = sum(row["flooded"] for row in rows)
        self.stdout.write(f"{len(rows)} cell-days written, {flooded} with a water report")
