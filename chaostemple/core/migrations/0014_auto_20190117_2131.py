# Generated by Django 2.0.10 on 2019-01-17 21:31

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('djalthingi', '0040_auto_20181204_1544'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0013_auto_20190117_2127'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='IssueBookmark',
            new_name='IssueMonitor',
        ),
    ]
