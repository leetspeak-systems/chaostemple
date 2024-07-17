# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-22 17:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0027_auto_20180219_2334"),
    ]

    operations = [
        migrations.CreateModel(
            name="President",
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
                ("name", models.CharField(max_length=100)),
                ("abbreviation", models.CharField(max_length=30)),
                ("president_type", models.CharField(max_length=3)),
                ("is_main", models.BooleanField(default=False)),
                ("order", models.IntegerField(null=True)),
                ("president_xml_id", models.IntegerField(unique=True)),
                (
                    "parliaments",
                    models.ManyToManyField(
                        related_name="presidents", to="djalthingi.Parliament"
                    ),
                ),
            ],
            options={
                "ordering": ["president_type", "order"],
            },
        ),
        migrations.CreateModel(
            name="PresidentSeat",
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
                ("timing_in", models.DateTimeField()),
                ("timing_out", models.DateTimeField(null=True)),
                (
                    "parliament",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="president_seats",
                        to="djalthingi.Parliament",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="president_seats",
                        to="djalthingi.Person",
                    ),
                ),
                (
                    "president",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="president_seats",
                        to="djalthingi.President",
                    ),
                ),
            ],
            options={
                "ordering": ["president__order", "timing_in"],
            },
        ),
    ]
