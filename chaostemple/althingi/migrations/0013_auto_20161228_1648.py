# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-28 16:48
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('althingi', '0012_issue_time_published'),
    ]

    operations = [
        migrations.AddField(
            model_name='parliament',
            name='era',
            field=models.CharField(default='', max_length=9),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='parliament',
            name='timing_end',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='parliament',
            name='timing_start',
            field=models.DateTimeField(default=datetime.datetime(1970, 1, 1, 0, 0)),
            preserve_default=False,
        ),
    ]