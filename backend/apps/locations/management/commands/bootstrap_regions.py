import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from shapely.geometry import box

from apps.core.geometry import geometry_to_json, parse_geometry
from apps.core.models import DataSource
from apps.locations.models import Area, AreaLevel, Neighbourhood

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
# North and South Kolkata have no official boundary. This common-use split runs near
# Park Street, is documented as approximate, and can be changed here.
KOLKATA_ZONE_SPLIT_LATITUDE = 22.55
KOLKATA_TERMS = ["kolkata", "calcutta"]
DISTRICTS = [
    {
        "slug": "north-24-parganas",
        "file": "north_24_parganas",
        "forecast_point": [22.7229, 88.4810],  # Barasat, the district headquarters
        "alert_terms": ["north 24 parganas", "north 24-parganas", "north twenty four parganas", "uttar 24"],
    },
    {
        "slug": "south-24-parganas",
        "file": "south_24_parganas",
        "forecast_point": [22.3589, 88.4315],  # Baruipur, near most of the population
        "alert_terms": ["south 24 parganas", "south 24-parganas", "south twenty four parganas", "dakshin 24"],
    },
]


class Command(BaseCommand):
    help = "Add North and South Kolkata zones and the 24 Parganas districts from stored OSM data."

    @transaction.atomic
    def handle(self, *args, **options):
        osm = DataSource.objects.filter(slug="osm").first()
        kolkata = Area.objects.filter(slug="kolkata").first()
        if osm is None or kolkata is None:
            raise CommandError("Run migrate and bootstrap_kolkata first.")

        kolkata.metadata = {**kolkata.metadata, "alert_terms": KOLKATA_TERMS}
        kolkata.save()

        boundary = parse_geometry(kolkata.boundary)
        west, south, east, north = boundary.bounds
        zones = {
            "north-kolkata": ("North Kolkata", box(west, KOLKATA_ZONE_SPLIT_LATITUDE, east, north)),
            "south-kolkata": ("South Kolkata", box(west, south, east, KOLKATA_ZONE_SPLIT_LATITUDE)),
        }
        for slug, (name, part) in zones.items():
            Area.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "level": AreaLevel.ZONE,
                    "parent": kolkata,
                    "boundary": geometry_to_json(boundary.intersection(part)),
                    "source": osm,
                    "source_ref": f"Derived from {kolkata.source_ref}",
                    "is_active": True,
                    "metadata": {
                        "alert_terms": KOLKATA_TERMS,
                        "note": f"Approximate split at latitude {KOLKATA_ZONE_SPLIT_LATITUDE}. Not an official boundary.",
                    },
                },
            )

        for district in DISTRICTS:
            area = self._import_district(district, osm)
            self.stdout.write(self.style.SUCCESS(f"{area.name}: {area.neighbourhoods.count()} localities"))
        self.stdout.write(self.style.SUCCESS("Regions ready."))

    def _import_district(self, district: dict, osm: DataSource) -> Area:
        feature = json.loads((DATA_DIR / f"{district['file']}_boundary.geojson").read_text(encoding="utf-8"))
        properties = feature["properties"]
        area, _ = Area.objects.update_or_create(
            slug=district["slug"],
            defaults={
                "name": properties["name"],
                "level": AreaLevel.DISTRICT,
                "boundary": feature["geometry"],
                "source": osm,
                "source_ref": properties["source_ref"],
                "is_active": True,
                "metadata": {
                    "source_url": properties["source_url"],
                    "license": properties["license"],
                    "forecast_point": district["forecast_point"],
                    "alert_terms": district["alert_terms"],
                },
            },
        )
        localities = json.loads((DATA_DIR / f"{district['file']}_localities.geojson").read_text(encoding="utf-8"))
        taken = set(Neighbourhood.objects.filter(area=area).values_list("slug", flat=True))
        for feature in localities["features"]:
            props = feature["properties"]
            longitude, latitude = feature["geometry"]["coordinates"]
            source_ref = f"OSM node {props['osm_id']}"
            existing = Neighbourhood.objects.filter(area=area, source_ref=source_ref).first()
            slug = existing.slug if existing else slugify(props["name"])[:100] or f"locality-{props['osm_id']}"
            if not existing and slug in taken:
                slug = f"{slug}-{props['osm_id']}"[:120]
            taken.add(slug)
            Neighbourhood.objects.update_or_create(
                area=area,
                slug=slug,
                defaults={
                    "name": props["name"],
                    "point": feature["geometry"],
                    "latitude": latitude,
                    "longitude": longitude,
                    "source": osm,
                    "source_ref": source_ref,
                    "is_active": True,
                    "metadata": {"place": props["place"], "wikidata": props["wikidata"]},
                },
            )
        return area
