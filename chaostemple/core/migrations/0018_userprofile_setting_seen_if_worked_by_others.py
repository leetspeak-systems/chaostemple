# Generated by Django 2.2.6 on 2020-06-01 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_document_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='setting_seen_if_worked_by_others',
            field=models.BooleanField(default=True),
        ),
    ]