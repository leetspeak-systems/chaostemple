# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-03-02 19:59
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('althingi', '0031_auto_20180224_1443'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='speech',
            unique_together=set([]),
        ),
    ]
