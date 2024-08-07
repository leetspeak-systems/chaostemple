# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-10 08:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djalthingi", "0021_rapporteur"),
    ]

    operations = [
        migrations.AlterField(
            model_name="committee",
            name="committee_xml_id",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="committeeagenda",
            name="committee_agenda_xml_id",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="constituency",
            name="constituency_xml_id",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="party",
            name="party_xml_id",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="person",
            name="person_xml_id",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name="votecasting",
            name="vote_casting_xml_id",
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterUniqueTogether(
            name="committeeagendaitem",
            unique_together=set([("committee_agenda", "order")]),
        ),
        migrations.AlterUniqueTogether(
            name="document",
            unique_together=set([("issue", "doc_num")]),
        ),
        migrations.AlterUniqueTogether(
            name="issue",
            unique_together=set([("parliament", "issue_num", "issue_group")]),
        ),
        migrations.AlterUniqueTogether(
            name="proposer",
            unique_together=set([("issue", "person", "committee", "order")]),
        ),
        migrations.AlterUniqueTogether(
            name="rapporteur",
            unique_together=set([("issue", "person")]),
        ),
        migrations.AlterUniqueTogether(
            name="review",
            unique_together=set([("issue", "log_num")]),
        ),
        migrations.AlterUniqueTogether(
            name="session",
            unique_together=set([("parliament", "session_num")]),
        ),
        migrations.AlterUniqueTogether(
            name="sessionagendaitem",
            unique_together=set([("session", "order")]),
        ),
        migrations.AlterUniqueTogether(
            name="vote",
            unique_together=set([("vote_casting", "person")]),
        ),
    ]
