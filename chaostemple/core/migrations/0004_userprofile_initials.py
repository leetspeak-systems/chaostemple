# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-03 18:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20170101_1758'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='initials',
            field=models.CharField(max_length=10, null=True),
        ),
    ]