# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-29 16:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0014_party_slug"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="party",
            options={"ordering": ["special", "name"]},
        ),
        migrations.AddField(
            model_name="party",
            name="special",
            field=models.BooleanField(default=False),
        ),
    ]
