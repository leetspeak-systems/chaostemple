# Generated by Django 2.2.2 on 2019-06-17 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0040_auto_20181204_1544"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="from_government",
            field=models.BooleanField(default=False),
        ),
    ]
