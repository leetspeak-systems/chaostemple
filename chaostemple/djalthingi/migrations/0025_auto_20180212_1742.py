# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-12 17:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djalthingi', '0024_auto_20171204_1745'),
    ]

    operations = [
        migrations.CreateModel(
            name='Speech',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('timing_start', models.DateTimeField()),
                ('timing_end', models.DateTimeField()),
                ('seconds', models.IntegerField()),
                ('speech_type', models.CharField(max_length=30)),
                ('iteration', models.CharField(max_length=3, null=True)),
                ('order_in_issue', models.IntegerField(null=True)),
                ('html_remote_path', models.CharField(max_length=500, null=True)),
                ('sgml_remote_path', models.CharField(max_length=500, null=True)),
                ('xml_remote_path', models.CharField(max_length=500, null=True)),
                ('text_remote_path', models.CharField(max_length=500, null=True)),
                ('sound_remote_path', models.CharField(max_length=500, null=True)),
                ('issue', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='speeches', to='djalthingi.Issue')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='speeches', to='djalthingi.Person')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='speeches', to='djalthingi.Session')),
            ],
            options={
                'ordering': ['timing_start'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='speech',
            unique_together=set([('order_in_issue', 'issue')]),
        ),
    ]