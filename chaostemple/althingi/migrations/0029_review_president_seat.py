# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-22 17:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('althingi', '0028_president_presidentseat'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='president_seat',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='althingi.PresidentSeat'),
        ),
    ]
