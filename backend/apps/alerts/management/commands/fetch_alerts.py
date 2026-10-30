from django.core.management.base import BaseCommand, CommandError

from apps.alerts.services import AlertIngestionError, ingest_imd_alerts


class Command(BaseCommand):
    help = "Ingest official IMD district warnings. Requires IMD_API_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--district-id", default=None)

    def handle(self, *args, **options):
        try:
            result = ingest_imd_alerts(district_id=options.get("district_id"))
        except AlertIngestionError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"IMD alerts: {result['written']} new records"))
