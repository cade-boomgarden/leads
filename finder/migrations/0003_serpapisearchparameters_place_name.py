# Generated by Django 5.2 on 2025-04-17 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finder', '0002_remove_apollocontactsearchparams_contact_search_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='serpapisearchparameters',
            name='place_name',
            field=models.CharField(blank=True, help_text='Location component', null=True),
        ),
    ]
