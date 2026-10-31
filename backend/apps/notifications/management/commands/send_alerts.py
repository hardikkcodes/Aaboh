from django.core.management.base import BaseCommand

from apps.notifications.services import evaluate_alerts


class Command(BaseCommand):
    help = "Create personal alerts from forecasts, official warnings and resident reports."

    def handle(self, *args, **options):
        result = evaluate_alerts()
        self.stdout.write(
            self.style.SUCCESS(f"{result['created']} notifications created for {result['users']} users")
        )
