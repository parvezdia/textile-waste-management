# Generated by Django 5.1.7 on 2025-03-21 19:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('designs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='design',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='designs/'),
        ),
    ]
