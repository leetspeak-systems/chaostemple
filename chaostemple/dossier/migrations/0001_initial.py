# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-01 17:59
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('althingi', '0015_auto_20161229_1625'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dossier',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dossier_type', models.CharField(choices=[('document', 'Parliamentary Documents'), ('review', 'Reviews')], max_length=10)),
                ('attention', models.CharField(choices=[('none', 'None'), ('question', 'Question'), ('exclamation', 'Exclamation')], default='none', max_length=20)),
                ('knowledge', models.IntegerField(choices=[(0, 'Unread'), (1, 'Briefly examined'), (2, 'Examined'), (3, 'Thoroughly examined')], default=0)),
                ('support', models.CharField(choices=[('undefined', 'Undefined'), ('strongopposition', 'Strong Opposition'), ('oppose', 'Oppose'), ('neutral', 'Neutral'), ('support', 'Support'), ('strongsupport', 'Strong Support'), ('referral', 'Referral'), ('other', 'Other')], default='undefined', max_length=20)),
                ('proposal', models.CharField(choices=[('none', 'None'), ('minor', 'Minor'), ('some', 'Some'), ('major', 'Major')], default='none', max_length=20)),
                ('document', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='althingi.Document')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='althingi.Issue')),
                ('review', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='althingi.Review')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DossierStatistic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('has_useful_info', models.BooleanField(default=False)),
                ('document_attention_exclamation', models.IntegerField(default=0)),
                ('document_attention_question', models.IntegerField(default=0)),
                ('document_knowledge_0', models.IntegerField(default=0)),
                ('document_knowledge_1', models.IntegerField(default=0)),
                ('document_knowledge_2', models.IntegerField(default=0)),
                ('document_knowledge_3', models.IntegerField(default=0)),
                ('document_support_undefined', models.IntegerField(default=0)),
                ('document_support_strongopposition', models.IntegerField(default=0)),
                ('document_support_oppose', models.IntegerField(default=0)),
                ('document_support_neutral', models.IntegerField(default=0)),
                ('document_support_support', models.IntegerField(default=0)),
                ('document_support_strongsupport', models.IntegerField(default=0)),
                ('document_support_referral', models.IntegerField(default=0)),
                ('document_support_other', models.IntegerField(default=0)),
                ('document_proposal_minor', models.IntegerField(default=0)),
                ('document_proposal_some', models.IntegerField(default=0)),
                ('document_proposal_major', models.IntegerField(default=0)),
                ('document_count', models.IntegerField(default=0)),
                ('document_memo_count', models.IntegerField(default=0)),
                ('review_attention_exclamation', models.IntegerField(default=0)),
                ('review_attention_question', models.IntegerField(default=0)),
                ('review_knowledge_0', models.IntegerField(default=0)),
                ('review_knowledge_1', models.IntegerField(default=0)),
                ('review_knowledge_2', models.IntegerField(default=0)),
                ('review_knowledge_3', models.IntegerField(default=0)),
                ('review_support_undefined', models.IntegerField(default=0)),
                ('review_support_strongopposition', models.IntegerField(default=0)),
                ('review_support_oppose', models.IntegerField(default=0)),
                ('review_support_neutral', models.IntegerField(default=0)),
                ('review_support_support', models.IntegerField(default=0)),
                ('review_support_strongsupport', models.IntegerField(default=0)),
                ('review_support_referral', models.IntegerField(default=0)),
                ('review_support_other', models.IntegerField(default=0)),
                ('review_proposal_minor', models.IntegerField(default=0)),
                ('review_proposal_some', models.IntegerField(default=0)),
                ('review_proposal_major', models.IntegerField(default=0)),
                ('review_count', models.IntegerField(default=0)),
                ('review_memo_count', models.IntegerField(default=0)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='althingi.Issue')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossier_statistics', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Memo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(max_length=2000)),
                ('order', models.IntegerField()),
                ('dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memos', to='dossier.Dossier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memos', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['order'],
            },
        ),
    ]
