import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.core.models import DataSource
from apps.locations.models import Area, AreaLevel, Neighbourhood
from apps.locations.services.grid import DEFAULT_GRID_VERSION, generate_grid

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class Command(BaseCommand):
    help = "Import the Kolkata boundary and OSM localities, then build the deterministic 1 km grid."

    def add_arguments(self, parser):
        parser.add_argument("--skip-grid", action="store_true")
        parser.add_argument("--skip-localities", action="store_true")
        parser.add_argument("--grid-version", default=DEFAULT_GRID_VERSION)
        parser.add_argument("--boundary", default=str(DATA_DIR / "kolkata_boundary.geojson"))
        parser.add_argument("--localities", default=str(DATA_DIR / "kolkata_localities.geojson"))

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            osm = DataSource.objects.get(slug="osm")
        except DataSource.DoesNotExist as exc:
            raise CommandError("Data source 'osm' is missing. Run migrations first.") from exc

        boundary_path = Path(options["boundary"])
        if not boundary_path.exists():
            raise CommandError(f"Boundary file not found: {boundary_path}")
        boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
        properties = boundary.get("properties", {})

        area, _ = Area.objects.update_or_create(
            slug="kolkata",
            defaults={
                "name": properties.get("name", "Kolkata Municipal Corporation"),
                "level": AreaLevel.CITY,
                "boundary": boundary,
                "source": osm,
                "source_ref": properties.get("source_ref", "OSM relation 9381363"),
                "is_active": True,
                "metadata": {
                    "source_url": properties.get("source_url"),
                    "license": properties.get("license", "ODbL-1.0"),
                    "wikidata": properties.get("wikidata", "Q1348"),
                    "note": (
                        "Community-maintained OSM administrative boundary for Kolkata "
                        "(admin_level=8). Replace with an official KMC boundary when available."
                    ),
                },
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Area: {area.name} ({area.area_km2:.2f} km2)"))

        if not options["skip_localities"]:
            localities_path = Path(options["localities"])
            if not localities_path.exists():
                self.stdout.write(self.style.WARNING(f"Localities file not found: {localities_path}"))
            else:
                collection = json.loads(localities_path.read_text(encoding="utf-8"))
                created = updated = 0
                for feature in collection.get("features", []):
                    props = feature.get("properties", {})
                    name = (props.get("name") or "").strip()
                    lon, lat = feature["geometry"]["coordinates"][:2]
                    if not name:
                        continue
                    base_slug = slugify(name)[:100] or f"locality-{props.get('osm_id', 'x')}"
                    slug = base_slug
                    existing = Neighbourhood.objects.filter(area=area, slug=slug).first()
                    if existing and existing.source_ref != f"OSM node {props.get('osm_id')}":
                        slug = f"{base_slug}-{props.get('osm_id', 'x')}"[:120]
                    _, was_created = Neighbourhood.objects.update_or_create(
                        area=area,
                        slug=slug,
                        defaults={
                            "name": name,
                            "point": {"type": "Point", "coordinates": [lon, lat]},
                            "latitude": lat,
                            "longitude": lon,
                            "source": osm,
                            "source_ref": f"OSM node {props.get('osm_id')}",
                            "is_active": True,
                            "metadata": {
                                "place": props.get("place"),
                                "wikidata": props.get("wikidata", ""),
                                "note": "Point locality, not an official ward boundary.",
                            },
                        },
                    )
                    created += int(was_created)
                    updated += int(not was_created)
                self.stdout.write(
                    self.style.SUCCESS(f"Localities: {created} created, {updated} updated")
                )

        if not options["skip_grid"]:
            result = generate_grid(area, version=options["grid_version"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Grid {result.definition.version}: {result.cells_created} cells "
                    f"({result.cells_considered} considered, {result.definition.cell_size_m} m)"
                )
            )

        self.stdout.write(self.style.SUCCESS("Kolkata bootstrap complete."))
