# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-06-06 18:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0003_shiftset'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='shift_set',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='schedules.ShiftSet'),
        ),
        migrations.AddField(
            model_name='shift',
            name='shift_set',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='schedules.ShiftSet'),
        ),
    ]