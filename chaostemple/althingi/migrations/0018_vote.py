# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-16 08:37
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('althingi', '0017_votecasting'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vote_response', models.CharField(choices=[('j\xe1', 'j\xe1'), ('nei', 'nei'), ('fjarverandi', 'fjarverandi'), ('bo\xf0a\xf0i fjarvist', 'bo\xf0a\xf0i fjarvist')], max_length=20)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='althingi.Person')),
                ('vote_casting', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='althingi.VoteCasting')),
            ],
        ),
    ]
