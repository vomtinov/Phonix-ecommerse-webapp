# Generated by Django 5.1.6 on 2025-02-17 12:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0012_brand_updated_at_category_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='category',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='product',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='product',
            name='updated_at',
        ),
    ]
