# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-06-06 18:07
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0005_auto_20180606_1106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='excel_updated',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='schedule',
            name='updated_on',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
