# Generated by Django 2.2.6 on 2019-11-14 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0044_auto_20191031_1704"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="committee_agenda_item_count",
            field=models.IntegerField(default=0),
        ),
    ]
