# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-03-15 23:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Master',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='NAME OF MASTER', max_length=100)),
                ('template', models.CharField(default='TEMPLATE', max_length=100)),
                ('flags', models.ManyToManyField(to='schedules.Flag')),
            ],
        ),
    ]
