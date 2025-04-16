from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Truncates all tables in the database while preserving their structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input', 
            action='store_true',
            dest='no_input',
            help='Do not prompt for confirmation'
        )

    def handle(self, *args, **options):
        db_name = settings.DATABASES['default']['NAME']
        
        if not options.get('no_input'):
            self.stdout.write(
                self.style.WARNING(
                    f"You're about to TRUNCATE ALL DATA in the database '{db_name}'.\n"
                    "This will permanently remove all data while keeping the table structure.\n"
                    "Are you sure you want to do this?\n\n"
                    "Type 'yes' to continue, or 'no' to cancel: "
                )
            )
            if input().lower() != 'yes':
                self.stdout.write(self.style.SUCCESS("Operation cancelled."))
                return

        with connection.cursor() as cursor:
            # Disable foreign key constraints temporarily
            cursor.execute("SET session_replication_role = 'replica';")
            
            # Get all tables in the public schema (excluding Django migrations table)
            cursor.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename != 'django_migrations';
                """
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            # Truncate all tables
            for table in tables:
                self.stdout.write(f"Truncating table: {table}")
                # TRUNCATE with CASCADE to handle all relationships
                cursor.execute(f'TRUNCATE TABLE "{table}" CASCADE;')
            
            # Re-enable foreign key constraints
            cursor.execute("SET session_replication_role = 'origin';")
            
        self.stdout.write(self.style.SUCCESS(f"Successfully truncated all tables in database '{db_name}'."))