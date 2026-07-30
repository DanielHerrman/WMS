# Generated manually — fix NULL organization_id on pre-existing records
from django.db import migrations


def fix_null_organization_ids(apps, schema_editor):
    Organization = apps.get_model('core', 'Organization')
    org = Organization.objects.first()
    if org is None:
        return

    models_to_fix = [
        ('MaterialType', 'material_types'),
        ('FilamentBrand', 'filament_brands'),
        ('CustomOrder', 'custom_orders'),
        ('Printer', 'printers'),
    ]

    for model_name, _ in models_to_fix:
        Model = apps.get_model('print3d', model_name)
        updated = Model.objects.filter(organization__isnull=True).update(organization=org)
        if updated:
            print(f'  {model_name}: fixed {updated} NULL organization(s) → {org.name}')


def reverse_fix(apps, schema_editor):
    # Reverse is a no-op — we don't set these back to NULL
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('print3d', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fix_null_organization_ids, reverse_fix),
    ]