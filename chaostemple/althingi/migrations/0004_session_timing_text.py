# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-10-15 18:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('althingi', '0003_auto_20161015_1815'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='timing_text',
            field=models.CharField(max_length=200, null=True),
        ),
    ]
