# Generated by Django 5.1.7 on 2025-04-17 19:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_alter_textilewaste_options_textilewaste_batch_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='textilewaste',
            name='status',
            field=models.CharField(choices=[('AVAILABLE', 'Available'), ('RESERVED', 'Reserved'), ('USED', 'Used'), ('RECYCLED', 'Recycled'), ('EXPIRED', 'Expired'), ('PENDING_REVIEW', 'Pending Review')], default='PENDING_REVIEW', max_length=20),
        ),
        migrations.AlterField(
            model_name='wastehistory',
            name='status',
            field=models.CharField(choices=[('AVAILABLE', 'Available'), ('RESERVED', 'Reserved'), ('USED', 'Used'), ('RECYCLED', 'Recycled'), ('EXPIRED', 'Expired'), ('PENDING_REVIEW', 'Pending Review')], max_length=20),
        ),
    ]
