from django.db import migrations

def add_inventory_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    TextileWaste = apps.get_model('inventory', 'TextileWaste')

    # Get content type for TextileWaste model
    content_type = ContentType.objects.get_for_model(TextileWaste)

    # Create new permissions
    Permission.objects.get_or_create(
        codename='can_view_analytics',
        name='Can view inventory analytics',
        content_type=content_type,
    )

    Permission.objects.get_or_create(
        codename='can_generate_reports',
        name='Can generate inventory reports',
        content_type=content_type,
    )

    Permission.objects.get_or_create(
        codename='can_manage_inventory',
        name='Can manage inventory items',
        content_type=content_type,
    )

def remove_inventory_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(
        codename__in=[
            'can_view_analytics',
            'can_generate_reports',
            'can_manage_inventory'
        ]
    ).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(
            add_inventory_permissions,
            remove_inventory_permissions
        ),
    ]