# Generated by Django 2.2.5 on 2019-10-08 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djalthingi', '0041_issue_from_government'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='pending_deletion',
            field=models.BooleanField(default=False),
        ),
    ]