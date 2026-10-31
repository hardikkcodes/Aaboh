from django.db import migrations


def rename(apps, schema_editor):
    source = apps.get_model("core", "DataSource")
    source.objects.filter(name="Civic Climate community reports").update(name="Aaboh community reports")


class Migration(migrations.Migration):
    dependencies = [("core", "0004_seed_air_forecast_source")]

    operations = [migrations.RunPython(rename, migrations.RunPython.noop)]
