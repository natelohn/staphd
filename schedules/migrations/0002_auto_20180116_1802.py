# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-01-17 02:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shift',
            name='test',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='stapher',
            name='test',
            field=models.TextField(default=''),
        ),
    ]
