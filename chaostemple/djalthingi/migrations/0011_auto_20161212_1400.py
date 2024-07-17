# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-12 14:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0010_auto_20161212_1319"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="special_inquisitor",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="issues_special_inquisited",
                to="djalthingi.Person",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="special_inquisitor_description",
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="issue",
            name="special_responder",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="issues_special_responded",
                to="djalthingi.Person",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="special_responder_description",
            field=models.CharField(max_length=50, null=True),
        ),
    ]
