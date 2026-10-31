import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.locations.models import Area, GridCell


class Command(BaseCommand):
    help = (
        "Export a generated analytical grid as an EPSG:4326 GeoJSON FeatureCollection. "
        "The output can be uploaded to Google Earth Engine as the table asset required "
        "by the Landsat export pipeline."
    )

    def add_arguments(self, parser):
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--grid-version", default=None, help="Grid version; defaults to the newest")
        parser.add_argument("--output", required=True, help="Destination .geojson path")
        parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc

        definitions = area.grid_definitions.all()
        definition = (
            definitions.filter(version=options["grid_version"]).first()
            if options["grid_version"]
            else definitions.first()
        )
        if definition is None:
            raise CommandError(f"No analytical grid exists for area '{area.slug}'.")

        output = Path(options["output"])
        if output.exists() and not options["force"]:
            raise CommandError(f"Output already exists: {output}. Pass --force to overwrite.")

        cells = GridCell.objects.filter(definition=definition).order_by("row", "col")
        features = [
            {
                "type": "Feature",
                "geometry": cell.geometry,
                "properties": {
                    "cell_code": cell.code,
                    "row": cell.row,
                    "col": cell.col,
                    "coverage_fraction": cell.coverage_fraction,
                    "area_km2": cell.area_km2,
                    "centroid_lat": cell.centroid_lat,
                    "centroid_lon": cell.centroid_lon,
                },
            }
            for cell in cells
        ]
        if not features:
            raise CommandError(f"Grid {definition.version} has no cells to export.")

        collection = {
            "type": "FeatureCollection",
            "name": f"{area.slug}-{definition.version}",
            "metadata": {
                "area": area.slug,
                "version": definition.version,
                "cell_size_m": definition.cell_size_m,
                "crs": "EPSG:4326",
                "source_crs": definition.crs,
                "cell_count": len(features),
                "note": (
                    "Analytical aggregation grid, not an official ward boundary. "
                    "Grid geometry is clipped to the area boundary."
                ),
            },
            "features": features,
        }

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {len(features)} cells from {definition.version} to {output}"
            )
        )
