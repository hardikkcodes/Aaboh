from django.core.management.base import BaseCommand, CommandError

from apps.air_quality.services import AirQualityIngestionError, ingest_cpcb


class Command(BaseCommand):
    help = "Ingest CPCB station measurements via data.gov.in. Requires CPCB_API_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--max-pages", type=int, default=5)

    def handle(self, *args, **options):
        try:
            result = ingest_cpcb(max_pages=options["max_pages"])
        except AirQualityIngestionError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"CPCB: {result['written']} measurements written from {result['rows']} rows "
                f"({result['stations_created']} new stations)"
            )
        )
        for warning in result["warnings"][:10]:
            self.stdout.write(self.style.WARNING(warning))
