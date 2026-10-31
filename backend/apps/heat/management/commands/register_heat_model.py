from django.core.management.base import BaseCommand, CommandError

from apps.heat.services import HeatModelError, register_artifact


class Command(BaseCommand):
    help = "Register a trained, evaluated heat model artefact in the model registry."

    def add_arguments(self, parser):
        parser.add_argument("--artifact", required=True, help="Artifact directory from ml/src/heat/train.py")
        parser.add_argument(
            "--operational",
            action="store_true",
            help="Mark the model operational. Only use after reviewing metrics and limitations.",
        )
        parser.add_argument("--activate", action="store_true", help="Make this the active LST model")

    def handle(self, *args, **options):
        try:
            model = register_artifact(
                options["artifact"],
                operational=options["operational"],
                activate=options["activate"],
            )
        except HeatModelError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Registered {model.name} {model.version} "
                f"(operational={model.is_operational}, active={model.is_active}, "
                f"metrics={model.metrics.get('mae_c')} °C MAE)"
            )
        )
        if not model.is_operational:
            self.stdout.write(
                self.style.WARNING(
                    "Model is registered but not operational. Pass --operational only after review."
                )
            )
