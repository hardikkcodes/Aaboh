from django.core.management.base import BaseCommand, CommandError

from apps.alerts.services import (
    AlertIngestionError,
    ingest_imd_alerts,
    ingest_sachet_alerts,
)


class Command(BaseCommand):
    help = (
        "Ingest official warnings. Defaults to the key-free SACHET/NDMA feed; "
        "use --provider imd when IMD_API_KEY is configured."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            choices=["sachet", "imd"],
            default="sachet",
            help="Official alert provider to ingest (default: sachet).",
        )
        parser.add_argument("--district-id", default=None, help="IMD district id (IMD only).")
        parser.add_argument(
            "--scope-term",
            action="append",
            default=None,
            help=(
                "Override the Kolkata scope terms for SACHET matching. Repeat to add terms. "
                "All fetched alerts are still stored; this only affects the in-scope count."
            ),
        )

    def handle(self, *args, **options):
        provider = options["provider"]
        try:
            if provider == "imd":
                result = ingest_imd_alerts(district_id=options.get("district_id"))
                self.stdout.write(
                    self.style.SUCCESS(
                        f"IMD alerts: {result['fetched']} fetched, {result['written']} new, "
                        f"{result['updated']} updated"
                    )
                )
                return
            result = ingest_sachet_alerts(scope_terms=options.get("scope_term"))
        except AlertIngestionError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"SACHET alerts: {result['fetched']} fetched, {result['written']} new, "
                f"{result['updated']} updated, {result['in_scope']} in Kolkata scope"
            )
        )
        if not result["in_scope"]:
            self.stdout.write(
                "No active SACHET alert matches the Kolkata scope right now. The feed is "
                "reachable, so this is a valid 'no active warning' result."
            )
