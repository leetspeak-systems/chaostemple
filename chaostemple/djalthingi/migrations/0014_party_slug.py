# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-29 15:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0013_auto_20161228_1648"),
    ]

    operations = [
        migrations.AddField(
            model_name="party",
            name="slug",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
    ]
