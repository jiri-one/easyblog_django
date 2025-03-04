# Generated by Django 4.1 on 2022-09-13 08:37

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("jiri_one", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="pub_time",
            field=models.DateTimeField(
                default=django.utils.timezone.now,
                editable=False,
                verbose_name="Fist release time",
            ),
        ),
    ]
