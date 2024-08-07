# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-23 22:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0020_auto_20170427_1830"),
    ]

    operations = [
        migrations.CreateModel(
            name="Rapporteur",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rapporteurs",
                        to="djalthingi.Issue",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rapporteurs",
                        to="djalthingi.Person",
                    ),
                ),
            ],
        ),
    ]
