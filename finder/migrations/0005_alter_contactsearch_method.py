# Generated by Django 5.2 on 2025-04-23 16:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finder', '0004_emailvalidationbatch'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactsearch',
            name='method',
            field=models.CharField(choices=[('apollo', 'Apollo'), ('hunter', 'Hunter'), ('scrape', 'Web Scrape')], default='hunter', max_length=10),
        ),
    ]
