# Generated by Django 2.0.10 on 2019-01-17 21:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_auto_20190117_2121"),
    ]

    operations = [
        migrations.AlterField(
            model_name="issuebookmark",
            name="issue",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="issue_monitors",
                to="djalthingi.Issue",
            ),
        ),
        migrations.AlterField(
            model_name="issuebookmark",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="issue_monitors",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
