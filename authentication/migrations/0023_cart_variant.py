# Generated by Django 5.1.6 on 2025-02-25 09:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0022_order_orderitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='authentication.variant'),
        ),
    ]
