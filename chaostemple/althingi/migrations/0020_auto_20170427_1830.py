# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-27 18:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('althingi', '0019_auto_20170427_1758'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='parliament',
            options={'ordering': ['-parliament_num']},
        ),
    ]