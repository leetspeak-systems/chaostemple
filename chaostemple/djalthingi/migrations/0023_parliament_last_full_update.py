# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-12 16:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0022_auto_20171110_0829"),
    ]

    operations = [
        migrations.AddField(
            model_name="parliament",
            name="last_full_update",
            field=models.DateTimeField(default=None, null=True),
        ),
    ]
