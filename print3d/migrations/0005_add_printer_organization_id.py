from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('print3d', '0004_merge_20260730_0700'),
    ]

    operations = [
        migrations.AddField(
            model_name='printer',
            name='organization',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='printers',
                to='core.organization',
                verbose_name='Organization',
            ),
        ),
    ]