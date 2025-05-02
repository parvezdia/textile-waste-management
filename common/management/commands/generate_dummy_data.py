import random
import uuid
from datetime import datetime, timedelta
import os
import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    User, ContactInfo, FactoryDetails, FactoryPartner, 
    Designer, BuyerPreferences, Buyer
)
from designs.models import Design, CustomizationOption
from inventory.models import TextileWaste, Dimensions, WasteHistory
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Generates dummy data for the Textile Fabric Waste Management System'

    def add_arguments(self, parser):
        parser.add_argument(
            '--factories',
            type=int,
            default=5,
            help='Number of factory partners to create'
        )
        parser.add_argument(
            '--designers',
            type=int,
            default=10,
            help='Number of designers to create'
        )
        parser.add_argument(
            '--buyers',
            type=int,
            default=15,
            help='Number of buyers to create'
        )
        parser.add_argument(
            '--waste-items',
            type=int,
            default=50,
            help='Number of waste items to create'
        )
        parser.add_argument(
            '--designs',
            type=int,
            default=30,
            help='Number of designs to create'
        )
        
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to generate dummy data...'))
        
        num_factories = options['factories']
        num_designers = options['designers']
        num_buyers = options['buyers']
        num_waste_items = options['waste_items']
        num_designs = options['designs']
        
        # Store references to created objects for relationships
        factories = []
        designers = []
        buyers = []
        waste_items = []
        
        try:
            with transaction.atomic():
                # First remove any existing data that might conflict
                self._clear_existing_data()
                
                # Generate Factory Partners
                self.stdout.write(f'Creating {num_factories} factory partners...')
                factories = self._create_factories(num_factories)
                
                # Generate Designers
                self.stdout.write(f'Creating {num_designers} designers...')
                designers = self._create_designers(num_designers)
                
                # Generate Buyers
                self.stdout.write(f'Creating {num_buyers} buyers...')
                buyers = self._create_buyers(num_buyers)
                
                # Generate Waste Items
                self.stdout.write(f'Creating {num_waste_items} waste items...')
                waste_items = self._create_waste_items(num_waste_items, factories)
                
                # Generate Designs
                self.stdout.write(f'Creating {num_designs} designs...')
                designs = self._create_designs(num_designs, designers, waste_items)
                
                self.stdout.write(self.style.SUCCESS('Successfully generated dummy data!'))
                
                # Print summary
                self.stdout.write(self.style.SUCCESS(f'Created {len(factories)} factory partners'))
                self.stdout.write(self.style.SUCCESS(f'Created {len(designers)} designers'))
                self.stdout.write(self.style.SUCCESS(f'Created {len(buyers)} buyers'))
                self.stdout.write(self.style.SUCCESS(f'Created {len(waste_items)} waste items'))
                self.stdout.write(self.style.SUCCESS(f'Created {len(designs)} designs'))
                # Save test user credentials for Locust
                self._save_test_user_credentials(factories, designers, buyers)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating dummy data: {str(e)}'))
            raise e
    
    def _clear_existing_data(self):
        """Clear existing dummy data"""
        self.stdout.write("Clearing existing data...")
        
        # Clear all data (instead of trying to filter)
        User.objects.all().delete()
        ContactInfo.objects.all().delete()
        FactoryDetails.objects.all().delete()
        BuyerPreferences.objects.all().delete()
        Design.objects.all().delete()
        CustomizationOption.objects.all().delete()
        TextileWaste.objects.all().delete()
        Dimensions.objects.all().delete()

    def _create_factories(self, count):
        factories = []
        factory_names = [
            "EcoTextile Solutions", "GreenFabric Industries", "SustainThread Co.", 
            "RecycleFiber Manufacturing", "EnviroCloth Partners", "CircularTextile Corp", 
            "ReWeavers Ltd.", "FabricReborn Industries", "EcoThread Solutions", 
            "GreenSpun Textiles"
        ]
        
        locations = [
            "123 Industrial Park, City A, Country", 
            "456 Manufacturing Zone, City B, Country",
            "789 Production District, City C, Country",
            "321 Factory Complex, City D, Country",
            "654 Industrial Estate, City E, Country",
            "987 Manufacturing Hub, City F, Country",
            "246 Production Area, City G, Country",
            "135 Industrial Area, City H, Country",
            "579 Factory Park, City I, Country",
            "864 Manufacturing District, City J, Country"
        ]
        
        certifications = [
            "ISO9001", "ISO14001", "SA8000", "GOTS", "OEKO-TEX", "WRAP", "GRS"
        ]
        
        for i in range(count):
            name = f"{random.choice(factory_names)} #{i+1}"
            location = random.choice(locations)
            
            # Create user with contact info
            contact_info = ContactInfo.objects.create(
                address=f"Factory Address {i+1}, Industrial Area, City",
                phone=f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                alternate_email=f"factory{i+1}.contact@example.com"
            )
            
            user = User.objects.create_user(
                username=f"factory{i+1}",
                email=f"factory{i+1}@example.com",
                password="password123",
                first_name=f"Factory",
                last_name=f"Partner {i+1}",
                user_type="FACTORY",
                contact_info=contact_info
            )
            
            # Check if factory_partner was already created by signals
            try:
                factory_partner = FactoryPartner.objects.get(user=user)
                # If the factory_partner exists but factory_details doesn't, create it
                if not hasattr(factory_partner, 'factory_details') or not factory_partner.factory_details:
                    factory_details = FactoryDetails.objects.create(
                        factory_name=name,
                        location=location,
                        certifications=random.sample(certifications, random.randint(1, 3)),
                        production_capacity=random.randint(1000, 5000)
                    )
                    factory_partner.factory_details = factory_details
                    factory_partner.save()
                else:
                    # Update existing factory details
                    factory_details = factory_partner.factory_details
                    factory_details.factory_name = name
                    factory_details.location = location
                    factory_details.certifications = random.sample(certifications, random.randint(1, 3))
                    factory_details.production_capacity = random.randint(1000, 5000)
                    factory_details.save()
            except FactoryPartner.DoesNotExist:
                # Create factory details and partner if they don't exist
                factory_details = FactoryDetails.objects.create(
                    factory_name=name,
                    location=location,
                    certifications=random.sample(certifications, random.randint(1, 3)),
                    production_capacity=random.randint(1000, 5000)
                )
                
                factory_partner = FactoryPartner.objects.create(
                    user=user,
                    factory_details=factory_details
                )
            
            factories.append(factory_partner)
            self.stdout.write(f'  Created factory: {name}')
            
        return factories
    
    def _create_designers(self, count):
        designers_list = []
        first_names = ["Alex", "Jamie", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Avery", "Dakota"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson"]
        
        for i in range(count):
            # Create contact info
            contact_info = ContactInfo.objects.create(
                address=f"Designer Studio {i+1}, Design District, City",
                phone=f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                alternate_email=f"designer{i+1}.contact@example.com"
            )
            
            # Create user
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            user = User.objects.create_user(
                username=f"designer{i+1}",
                email=f"designer{i+1}@example.com",
                password="password123",
                first_name=first_name,
                last_name=last_name,
                user_type="DESIGNER",
                contact_info=contact_info
            )
            
            # Try to get existing designer created by signals, or create new one
            try:
                designer = Designer.objects.get(user=user)
                # Update existing designer with random approval status
                is_approved = random.choice([True, True, True, False])  # 75% chance of being approved
                status = "APPROVED" if is_approved else "PENDING"
                designer.design_stats = {
                    "total_designs": 0,
                    "published_designs": 0,
                    "total_sales": 0,
                    "sustainability_score": random.randint(60, 95)
                }
                designer.is_approved = is_approved
                designer.status = status
                designer.approval_date = timezone.now() - timedelta(days=random.randint(1, 60)) if is_approved else None
                designer.save()
            except Designer.DoesNotExist:
                # Create new designer with random approval status
                is_approved = random.choice([True, True, True, False])  # 75% chance of being approved
                status = "APPROVED" if is_approved else "PENDING"
                designer = Designer.objects.create(
                    user=user,
                    design_stats={
                        "total_designs": 0,
                        "published_designs": 0,
                        "total_sales": 0,
                        "sustainability_score": random.randint(60, 95)
                    },
                    is_approved=is_approved,
                    status=status,
                    approval_date=timezone.now() - timedelta(days=random.randint(1, 60)) if is_approved else None
                )
            
            designers_list.append(designer)
            approval_status = "approved" if designer.is_approved else "pending approval"
            self.stdout.write(f'  Created designer: {first_name} {last_name} ({approval_status})')
            
        return designers_list
    
    def _create_buyers(self, count):
        buyers_list = []
        first_names = ["Sam", "Chris", "Pat", "Robin", "Jordan", "Leslie", "Skyler", "Ashton", "Kennedy", "Tyler"]
        last_names = ["Anderson", "Thomas", "Jackson", "White", "Harris", "Clark", "Lewis", "Walker", "Hall", "Young"]
        materials = ["Cotton", "Linen", "Recycled Polyester", "Organic Cotton", "Hemp", "Bamboo", "Wool", "Silk"]
        styles = ["Casual", "Formal", "Bohemian", "Minimalist", "Vintage", "Street", "Athletic", "Business Casual"]
        
        for i in range(count):
            # Create contact info
            contact_info = ContactInfo.objects.create(
                address=f"Buyer Address {i+1}, Residential Area, City",
                phone=f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                alternate_email=f"buyer{i+1}.contact@example.com"
            )
            
            # Create user
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            user = User.objects.create_user(
                username=f"buyer{i+1}",
                email=f"buyer{i+1}@example.com",
                password="password123",
                first_name=first_name,
                last_name=last_name,
                user_type="BUYER",
                contact_info=contact_info
            )
            
            # Try to get existing buyer created by signals, or create new one
            try:
                buyer = Buyer.objects.get(user=user)
                # Update or create preferences for existing buyer
                if hasattr(buyer, 'preferences'):
                    preferences = buyer.preferences
                    preferences.preferred_materials = random.sample(materials, random.randint(1, 4))
                    preferences.preferred_styles = random.sample(styles, random.randint(1, 3))
                    preferences.size_preferences = {
                        "shirt": random.choice(["S", "M", "L", "XL"]),
                        "pants": random.choice(["28", "30", "32", "34", "36"])
                    }
                    preferences.max_price = random.choice([99.99, 149.99, 199.99, 249.99, 299.99])
                    preferences.save()
                else:
                    preferences = BuyerPreferences.objects.create(
                        preferred_materials=random.sample(materials, random.randint(1, 4)),
                        preferred_styles=random.sample(styles, random.randint(1, 3)),
                        size_preferences={
                            "shirt": random.choice(["S", "M", "L", "XL"]),
                            "pants": random.choice(["28", "30", "32", "34", "36"])
                        },
                        max_price=random.choice([99.99, 149.99, 199.99, 249.99, 299.99])
                    )
                    buyer.preferences = preferences
                    buyer.save()
            except Buyer.DoesNotExist:
                # Create new buyer with preferences
                preferences = BuyerPreferences.objects.create(
                    preferred_materials=random.sample(materials, random.randint(1, 4)),
                    preferred_styles=random.sample(styles, random.randint(1, 3)),
                    size_preferences={
                        "shirt": random.choice(["S", "M", "L", "XL"]),
                        "pants": random.choice(["28", "30", "32", "34", "36"])
                    },
                    max_price=random.choice([99.99, 149.99, 199.99, 249.99, 299.99])
                )
                buyer = Buyer.objects.create(
                    user=user,
                    preferences=preferences
                )
            
            buyers_list.append(buyer)
            self.stdout.write(f'  Created buyer: {first_name} {last_name}')
            
        return buyers_list
    
    def _create_waste_items(self, count, factories):
        waste_items = []
        types = ["Fabric Scraps", "Leftover Material", "Deadstock Fabric", "Cutting Waste", "End of Roll", "Sample Yardage"]
        materials = ["Cotton", "Linen", "Polyester", "Wool", "Silk", "Denim", "Canvas", "Rayon", "Nylon", "Spandex"]
        colors = ["Red", "Blue", "Green", "Yellow", "Black", "White", "Grey", "Purple", "Orange", "Pink", "Brown", "Navy"]
        statuses = ["AVAILABLE", "PENDING_REVIEW", "RESERVED", "USED"]
        status_weights = [0.2, 0.7, 0.05, 0.05]  # AVAILABLE, PENDING_REVIEW, RESERVED, USED
        quality_grades = ["EXCELLENT", "GOOD", "FAIR", "POOR"]
        quality_weights = [0.3, 0.5, 0.15, 0.05]  # Weighted probabilities
        storage_locations = ["Warehouse A", "Warehouse B", "Storage Unit 1", "Storage Unit 2", "Main Factory", "Secondary Location"]
        
        # Use a fixed 'now' for all randomizations to spread dates correctly
        now = timezone.now()
        
        for i in range(count):
            # Choose a random factory
            factory = random.choice(factories)
            
            # Generate dimensions
            dimensions = Dimensions.objects.create(
                length=random.uniform(0.5, 10.0),
                width=random.uniform(0.5, 5.0),
                unit=random.choice(["m", "yd", "ft"])
            )
            
            # Choose status with weighting
            status = random.choices(statuses, weights=status_weights, k=1)[0]
            
            # Choose quality with weighting
            quality = random.choices(quality_grades, weights=quality_weights, k=1)[0]
            
            # Create textile waste
            waste_id = f"WST-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            type_choice = random.choice(types)
            material_choice = random.choice(materials)
            quantity = round(random.uniform(0.5, 20.0), 2)
            
            # Set creation date (between 0-179 days ago, i.e., last 6 months)
            days_ago = random.randint(0, 179)
            date_added = now - timedelta(days=days_ago)
            
            # 30% chance of having an expiry date
            expiry_date = None
            if random.random() < 0.3:
                # Expiry between 30-180 days from creation
                expiry_days = random.randint(30, 180)
                expiry_date = date_added + timedelta(days=expiry_days)
            
            waste = TextileWaste.objects.create(
                waste_id=waste_id,
                type=type_choice,
                material=material_choice,
                quantity=quantity,
                unit=random.choice(["kg", "g", "lb"]),
                color=random.choice(colors),
                dimensions=dimensions,
                quality_grade=quality,
                date_added=date_added,
                last_updated=date_added,
                expiry_date=expiry_date,
                status=status,
                factory=factory,
                description=f"Sample {material_choice} {type_choice.lower()} in {random.choice(colors).lower()} color with {quality.lower()} quality.",
                sustainability_score=random.randint(50, 100),
                storage_location=random.choice(storage_locations),
                batch_number=f"BATCH-{random.randint(1000, 9999)}"
            )
            
            # Create waste history entry
            WasteHistory.objects.create(
                waste_item=waste,
                status=status,
                timestamp=date_added,
                changed_by=factory.user,
                notes=f"Initial inventory addition of {material_choice} {type_choice.lower()}"
            )
            
            # If status is not PENDING_REVIEW, add another history entry for the status change
            if status != "PENDING_REVIEW":
                status_change_date = date_added + timedelta(days=random.randint(1, min(30, days_ago)))
                WasteHistory.objects.create(
                    waste_item=waste,
                    status=status,
                    timestamp=status_change_date,
                    changed_by=factory.user,
                    notes=f"Status updated to {status}"
                )
            
            waste_items.append(waste)
            self.stdout.write(f'  Created waste item: {waste_id} - {material_choice} ({status})')
            
        return waste_items
    
    def _create_designs(self, count, designers, waste_items):
        designs = []
        
        # Only use approved designers
        approved_designers = [d for d in designers if getattr(d, 'status', None) == "APPROVED"]
        
        if not approved_designers:
            self.stdout.write(self.style.WARNING('No approved designers found. Skipping design creation.'))
            return designs
            
        design_names = [
            "Eco Chic Dress", "Sustainable Jacket", "Recycled Denim Jeans", "Upcycled Blouse", 
            "Green Fashion Skirt", "Eco-friendly Shirt", "Repurposed Coat", "Circular Scarf", 
            "Zero Waste Pants", "Sustainable Sweater"
        ]
        
        design_types = ["Dress", "Jacket", "Jeans", "Blouse", "Skirt", "Shirt", "Coat", "Scarf", "Pants", "Sweater"]
        design_styles = ["Casual", "Formal", "Bohemian", "Minimalist", "Vintage", "Street", "Athletic", "Business"]
        design_statuses = ["DRAFT", "PUBLISHED", "PENDING_REVIEW"]
        status_weights = [0.2, 0.7, 0.1]  # Weighted probabilities
        
        for i in range(count):
            designer = random.choice(approved_designers)
            
            # Set creation date (between 1-60 days ago)
            days_ago = random.randint(1, 60)
            date_created = timezone.now() - timedelta(days=days_ago)
            
            # Choose status with weighting
            status = random.choices(design_statuses, weights=status_weights, k=1)[0]
            
            # Choose design details
            design_type = random.choice(design_types)
            design_style = random.choice(design_styles)
            name = f"{random.choice(design_names)} {i+1}"
            
            # Generate a unique design ID
            design_id = f"DES_{uuid.uuid4().hex[:8]}"
            
            # Create specifications
            specifications = {
                "type": design_type,
                "style": design_style,
                "complexity": random.randint(1, 5),
                "sustainability_score": random.randint(60, 100),
                "estimated_production_time": random.randint(3, 14)
            }
            
            # Determine if design is customizable
            is_customizable = random.choice([True, False])
            
            # Create design
            design = Design.objects.create(
                design_id=design_id,
                name=name,
                designer=designer,
                description=f"A sustainable {design_style.lower()} {design_type.lower()} made from recycled materials.",
                price=random.randint(5, 30) * 10 - 0.01,  # $49.99 to $299.99
                status=status,
                specifications=specifications,
                estimated_delivery_days=random.randint(5, 21)
            )
            
            # Add material requirements (1-3 materials per design)
            materials_count = random.randint(1, 3)
            available_waste = [w for w in waste_items if w.status == "AVAILABLE"]
            
            if available_waste:
                for j in range(materials_count):
                    if available_waste:
                        waste = random.choice(available_waste)
                        # Add this waste item to the design's required materials
                        design.required_materials.add(waste)
                        # Remove this waste from available options to avoid duplicates
                        available_waste.remove(waste)
            
            # Add customization options if desired
            if is_customizable:
                options_count = random.randint(1, 3)
                option_types = ["COLOR", "SIZE", "MATERIAL", "STYLE", "FEATURE"]
                
                for j in range(options_count):
                    if not option_types:
                        break
                        
                    option_type = random.choice(option_types)
                    option_values = []
                    option_id = f"OPT_{uuid.uuid4().hex[:8]}"
                    
                    if option_type == "COLOR":
                        option_values = random.sample(["Red", "Blue", "Green", "Black", "White"], random.randint(2, 5))
                    elif option_type == "SIZE":
                        option_values = ["S", "M", "L", "XL"]
                    elif option_type == "MATERIAL":
                        option_values = random.sample(["Cotton", "Linen", "Polyester", "Wool"], random.randint(2, 4))
                    elif option_type == "STYLE":
                        option_values = ["Regular Fit", "Slim Fit", "Loose Fit", "Tailored"]
                    elif option_type == "FEATURE":
                        option_values = ["Pockets", "Collar", "Hood", "Zipper", "Buttons"]
                    
                    # Create price impact mapping
                    has_price_impact = random.choice([True, False])
                    price_impact = {
                        "has_impact": has_price_impact
                    }
                    
                    if has_price_impact:
                        for value in option_values:
                            price_impact[value] = random.randint(-5, 15)
                    
                    CustomizationOption.objects.create(
                        option_id=option_id,
                        name=option_type.title(),
                        type=option_type,
                        available_choices=option_values,
                        price_impact=price_impact,
                        design=design
                    )
                    
                    # Remove this option type from available options to avoid duplicates
                    option_types.remove(option_type)
            
            # Update designer stats
            designer_stats = designer.design_stats or {}
            designer_stats["total_designs"] = designer_stats.get("total_designs", 0) + 1
            
            if status == "PUBLISHED":
                designer_stats["published_designs"] = designer_stats.get("published_designs", 0) + 1
            
            designer.design_stats = designer_stats
            designer.save()
            
            designs.append(design)
            self.stdout.write(f'  Created design: {name} by {designer.user.get_full_name()} ({status})')
            
        return designs
    
    def _save_test_user_credentials(self, factories, designers, buyers):
        """Save generated test user credentials to a JSON file for Locust"""
        users = {
            "factories": [
                {"username": f.user.username, "password": "password123", "email": f.user.email}
                for f in factories
            ],
            "designers": [
                {"username": d.user.username, "password": "password123", "email": d.user.email}
                for d in designers
            ],
            "buyers": [
                {"username": b.user.username, "password": "password123", "email": b.user.email}
                for b in buyers
            ]
        }
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'performance_tests')
        output_dir = os.path.normpath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'test_users.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f'Saved test user credentials to {output_path}'))