from django.db import migrations

def fix_factory_user_types(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    # Fix any users with 'FACTORY PARTNER' to use 'FACTORY'
    User.objects.filter(user_type='FACTORY PARTNER').update(user_type='FACTORY')

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_alter_factorydetails_factory_name_and_more'),
    ]

    operations = [
        migrations.RunPython(fix_factory_user_types),
    ]