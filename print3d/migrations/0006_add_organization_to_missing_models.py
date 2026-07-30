# Generated manually to fix missing organization_id columns on production DB
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('print3d', '0005_add_printer_organization_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialtype',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='material_types',
                to='core.organization',
                verbose_name='Organization',
            ),
        ),
        migrations.AddField(
            model_name='filamentbrand',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='filament_brands',
                to='core.organization',
                verbose_name='Organization',
            ),
        ),
        migrations.AddField(
            model_name='customorder',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='custom_orders',
                to='core.organization',
                verbose_name='Organization',
            ),
        ),
    ]