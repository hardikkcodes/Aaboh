from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.air_quality.services import AirQualityIngestionError, ingest_cpcb


class Command(BaseCommand):
    help = "Ingest CPCB station measurements via data.gov.in. Requires CPCB_API_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--max-pages", type=int, default=5)
        parser.add_argument(
            "--city",
            action="append",
            default=None,
            help=(
                "Restrict to one city using the source's city filter. Repeat for more "
                "cities. Defaults to CPCB_CITIES (Kolkata,Howrah) when set."
            ),
        )
        parser.add_argument(
            "--all-cities",
            action="store_true",
            help="Do not apply a city filter. This ingests the national station feed.",
        )

    def handle(self, *args, **options):
        if options["all_cities"]:
            cities: list[str] = []
        elif options["city"]:
            cities = options["city"]
        else:
            cities = list(getattr(settings, "CPCB_CITIES", []) or [])
        try:
            result = ingest_cpcb(max_pages=options["max_pages"], cities=cities)
        except AirQualityIngestionError as exc:
            raise CommandError(str(exc)) from exc
        scope = ", ".join(result["cities"]) if result["cities"] else "all cities"
        self.stdout.write(
            self.style.SUCCESS(
                f"CPCB ({scope}): {result['written']} measurements written from "
                f"{result['rows']} rows ({result['stations_created']} new stations)"
            )
        )
        for warning in result["warnings"][:10]:
            self.stdout.write(self.style.WARNING(warning))
