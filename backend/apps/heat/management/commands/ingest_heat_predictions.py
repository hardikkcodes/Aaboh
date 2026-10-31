from django.core.management.base import BaseCommand, CommandError

from apps.heat.models import ModelVersion
from apps.heat.services import HeatModelError, ingest_predictions
from apps.locations.models import Area


class Command(BaseCommand):
    help = "Import cell-level LST predictions produced by ml/src/heat/predict.py."

    def add_arguments(self, parser):
        parser.add_argument("--predictions", required=True, help="CSV from ml/src/heat/predict.py")
        parser.add_argument("--area", default="kolkata")
        parser.add_argument("--model-id", default=None, help="ModelVersion UUID")
        parser.add_argument("--model-version", default=None, help="ModelVersion version string")
        parser.add_argument("--grid-version", default=None)

    def handle(self, *args, **options):
        try:
            area = Area.objects.get(slug=options["area"], is_active=True)
        except Area.DoesNotExist as exc:
            raise CommandError(f"Unknown area: {options['area']}") from exc

        models = ModelVersion.objects.filter(task="lst_estimation")
        if options["model_id"]:
            model = models.filter(id=options["model_id"]).first()
        elif options["model_version"]:
            model = models.filter(version=options["model_version"]).order_by("-created_at").first()
        else:
            model = models.filter(is_active=True).first() or models.order_by("-created_at").first()
        if model is None:
            raise CommandError("No registered LST model found. Run register_heat_model first.")

        try:
            run = ingest_predictions(
                area,
                model,
                options["predictions"],
                grid_version=options["grid_version"],
            )
        except HeatModelError as exc:
            raise CommandError(f"Prediction ingestion failed: {exc}") from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Prediction run {run.id} complete: {run.metadata.get('written')} cells "
                f"({run.metadata.get('skipped')} skipped) using {model.name} {model.version}"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "These are model estimates of land-surface temperature, not air temperature "
                "or an official heat warning."
            )
        )
