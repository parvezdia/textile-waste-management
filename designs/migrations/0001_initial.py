# Generated by Django 5.1.7 on 2025-03-11 20:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomizationOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_id', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(choices=[('COLOR', 'Color'), ('SIZE', 'Size'), ('MATERIAL', 'Material'), ('STYLE', 'Style'), ('FEATURE', 'Feature')], max_length=20)),
                ('available_choices', models.JSONField(help_text='List of available choices')),
                ('price_impact', models.JSONField(help_text='Map of choice to price impact')),
            ],
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_id', models.CharField(max_length=100, unique=True)),
                ('filename', models.CharField(max_length=255)),
                ('path', models.CharField(max_length=255)),
                ('size', models.IntegerField()),
                ('resolution', models.CharField(max_length=50)),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Design',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('design_id', models.CharField(max_length=100, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PUBLISHED', 'Published'), ('ARCHIVED', 'Archived'), ('DELETED', 'Deleted')], default='DRAFT', max_length=20)),
                ('customization_options', models.ManyToManyField(to='designs.customizationoption')),
                ('designer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='designs', to='accounts.designer')),
                ('required_materials', models.ManyToManyField(to='inventory.textilewaste')),
                ('images', models.ManyToManyField(to='designs.image')),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
    ]
