from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("partners", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="partner",
            name="moa_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="moa_link",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="moa_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="partner",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updated_partners",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
