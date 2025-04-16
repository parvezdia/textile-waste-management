import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, F, Q
from django.contrib.auth import get_user_model

from accounts.models import FactoryPartner
from designs.models import Design
from inventory.models import TextileWaste
from orders.models import Order, PaymentInfo, DeliveryInfo

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates analytics data for charts and tables in the admin dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--orders',
            type=int,
            default=30,
            help='Number of orders to generate'
        )
        parser.add_argument(
            '--months',
            type=int,
            default=6,
            help='Number of months to generate data for'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to generate analytics data...'))
        
        num_orders = options['orders']
        num_months = options['months']
        
        try:
            with transaction.atomic():
                # Generate orders with different statuses for charts
                self.stdout.write(f'Generating {num_orders} orders across {num_months} months...')
                self._generate_orders(num_orders, num_months)
                
                # Update waste materials distribution
                self.stdout.write('Updating waste material distribution...')
                self._update_waste_distribution()
                
                # Update design statuses to ensure good distribution
                self.stdout.write('Updating design status distribution...')
                self._update_design_statuses()
                
                self.stdout.write(self.style.SUCCESS('Successfully generated analytics data!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating analytics data: {str(e)}'))
            raise e
    
    def _generate_orders(self, count, months):
        """Generate orders spread across several months with different statuses"""
        
        # Get available designs and buyers
        designs = list(Design.objects.filter(status='PUBLISHED'))
        buyers = list(User.objects.filter(user_type='BUYER'))
        
        if not designs or not buyers:
            self.stdout.write(self.style.WARNING('No published designs or buyers found. Run generate_dummy_data first.'))
            return
        
        # Define possible order statuses and their weights
        statuses = ['PENDING', 'CONFIRMED', 'IN_PRODUCTION', 'READY_FOR_DELIVERY', 'SHIPPED', 'DELIVERED', 'CANCELED']
        status_weights = [0.1, 0.15, 0.15, 0.1, 0.2, 0.2, 0.1]  # Weighted probabilities
        
        # Set base date to several months ago
        now = timezone.now()
        start_date = now - timedelta(days=30 * months)
        
        # Check if orders already exist and clean them up
        existing_orders = Order.objects.all().count()
        if existing_orders > 0:
            self.stdout.write(f'Deleting {existing_orders} existing orders...')
            Order.objects.all().delete()
        
        # Clean up related models
        PaymentInfo.objects.all().delete()
        DeliveryInfo.objects.all().delete()
        
        # Create orders spread across months
        import uuid
        
        for i in range(count):
            # Pick a random buyer and design
            try:
                buyer = random.choice(buyers).buyer
            except (AttributeError, IndexError):
                self.stdout.write(self.style.WARNING('No buyers found with buyer profiles. Run generate_dummy_data first.'))
                return
                
            try:
                design = random.choice(designs)
            except IndexError:
                self.stdout.write(self.style.WARNING('No published designs found. Run generate_dummy_data first.'))
                return
            
            # Create a random date within the specified months range
            days_offset = random.randint(0, 30 * months)
            order_date = start_date + timedelta(days=days_offset)
            
            # Generate a random order status based on date
            days_since_order = (now - order_date).days
            if days_since_order < 7:
                # Recent orders more likely PENDING or CONFIRMED
                statuses_subset = statuses[:3]
                weights_subset = [0.4, 0.4, 0.2]
                status = random.choices(statuses_subset, weights=weights_subset, k=1)[0]
            elif days_since_order < 14:
                # Older orders more likely IN_PRODUCTION or READY_FOR_DELIVERY
                statuses_subset = statuses[1:5]
                weights_subset = [0.2, 0.3, 0.3, 0.2]
                status = random.choices(statuses_subset, weights=weights_subset, k=1)[0]
            else:
                # Much older orders more likely SHIPPED, DELIVERED or CANCELED
                statuses_subset = statuses[4:]
                weights_subset = [0.3, 0.5, 0.2]
                status = random.choices(statuses_subset, weights=weights_subset, k=1)[0]
            
            # Generate a random quantity between 1 and 3
            quantity = random.randint(1, 3)
            
            # Calculate total price based on design price and quantity
            total_price = design.price * quantity
            
            # Create payment info
            payment_info = PaymentInfo.objects.create(
                payment_id=f"PAY-{uuid.uuid4().hex[:10]}",
                method=random.choice(["CREDIT_CARD", "BANK_TRANSFER", "DIGITAL_WALLET"]),
                amount=total_price,
                status="COMPLETED" if status in ["SHIPPED", "DELIVERED"] else "PENDING",
                transaction_date=order_date
            )
            
            # Create delivery info
            delivery_date = order_date + timedelta(days=random.randint(3, 14))
            delivery_info = DeliveryInfo.objects.create(
                tracking_number=f"TRK{random.randint(10000, 99999)}",
                carrier=random.choice(["FedEx", "UPS", "DHL"]),
                address=f"Shipping Address for {buyer.user.get_full_name()}, City, Country",
                estimated_delivery_date=delivery_date,
                actual_delivery_date=delivery_date if status == "DELIVERED" else None,
                status="DELIVERED" if status == "DELIVERED" else ("IN_TRANSIT" if status == "SHIPPED" else "PROCESSING")
            )
            
            # Create the order
            order = Order.objects.create(
                order_id=f"ORD-{uuid.uuid4().hex[:10]}",
                buyer=buyer,
                design=design,
                quantity=quantity,
                status=status,
                total_price=total_price,
                payment_info=payment_info,
                delivery_info=delivery_info,
                date_ordered=order_date,
                customizations={}  # No customization for demo data
            )
            
            self.stdout.write(f'  Created order #{order.id} from {order_date.strftime("%Y-%m-%d")} with status {status}')
            
        self.stdout.write(self.style.SUCCESS(f'Created {count} orders across {months} months'))
    
    def _update_waste_distribution(self):
        """Ensure waste materials have a good distribution for charts"""
        waste_items = TextileWaste.objects.all()
        
        if not waste_items:
            self.stdout.write(self.style.WARNING('No waste items found. Run generate_dummy_data first.'))
            return
            
        # Get current material distribution
        material_count = {}
        for waste in waste_items:
            material = waste.material
            if material in material_count:
                material_count[material] += 1
            else:
                material_count[material] = 1
        
        # Identify materials with low counts
        if material_count:
            avg_count = sum(material_count.values()) / len(material_count)
            low_materials = [m for m, c in material_count.items() if c < avg_count * 0.5]
            high_materials = [m for m, c in material_count.items() if c > avg_count * 1.5]
            
            # Balance out the distribution by updating some waste items
            if low_materials and high_materials:
                # Update some waste items from high count materials to low count materials
                items_to_update = waste_items.filter(material__in=high_materials)[:len(low_materials)*2]
                
                for i, item in enumerate(items_to_update):
                    low_material = low_materials[i % len(low_materials)]
                    item.material = low_material
                    item.save()
                    self.stdout.write(f'  Updated waste item #{item.id} material to {low_material}')
            
            # Update waste quantities to ensure they're large enough for the charts
            for waste in waste_items:
                if waste.quantity < 2:
                    waste.quantity = random.uniform(2, 10)
                    waste.save()
                    
            self.stdout.write(f'Updated material distribution for {len(waste_items)} waste items')
    
    def _update_design_statuses(self):
        """Ensure design statuses have a good distribution for charts"""
        designs = Design.objects.all()
        
        if not designs:
            self.stdout.write(self.style.WARNING('No designs found. Run generate_dummy_data first.'))
            return
            
        # Define target distribution in percents
        status_distribution = {
            'DRAFT': 20,
            'PUBLISHED': 60,
            'PENDING_REVIEW': 20,
        }
        
        # Get current counts
        current_counts = {
            status: designs.filter(status=status).count() 
            for status in status_distribution.keys()
        }
        
        total_designs = designs.count()
        target_counts = {
            status: int(total_designs * pct / 100)
            for status, pct in status_distribution.items()
        }
        
        # Adjust to reach target distribution
        for status, target in target_counts.items():
            current = current_counts.get(status, 0)
            diff = target - current
            
            if diff > 0:
                # Need to add more of this status
                # Find designs with other statuses
                other_designs = designs.exclude(status=status)
                
                # Update some designs to this status
                for design in other_designs[:diff]:
                    design.status = status
                    design.save()
                    self.stdout.write(f'  Updated design #{design.id} status to {status}')
            
        self.stdout.write(f'Updated status distribution for {designs.count()} designs')