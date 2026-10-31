from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

STEPS = [
    ("fetch_alerts", []),
    ("fetch_cyclones", []),
    ("fetch_weather", ["--all-areas"]),
    ("fetch_rain_outlook", []),
    ("fetch_cpcb", []),
    ("fetch_air_forecast", ["--all-areas"]),
]


class Command(BaseCommand):
    help = "Refresh all live data once. One failed source doesn't stop the rest."

    def handle(self, *args, **options):
        for name, arguments in STEPS:
            try:
                call_command(name, *arguments, stdout=self.stdout, stderr=self.stderr)
            except (CommandError, OSError) as exc:
                self.stderr.write(f"{name} failed: {exc}")
