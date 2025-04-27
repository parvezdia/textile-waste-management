from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import get_template as original_get_template
from unittest.mock import patch, Mock
from decimal import Decimal
import uuid

from .models import Transaction
from orders.models import Order, PaymentInfo, DeliveryInfo
from accounts.models import Buyer, BuyerPreferences
from designs.models import Design
from accounts.models import Designer

User = get_user_model()

def mock_get_template(template_name, *args, **kwargs):
    """Mock template loader that returns a Mock with a render method"""
    mock_template = Mock()
    mock_template.render.return_value = "Mocked template rendering"
    return mock_template

class TransactionViewsModuleTest(TestCase):
    def setUp(self):
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin', 
            email='admin@example.com',
            password='adminpassword',
            is_staff=True
        )
        
        # Create regular user (non-admin)
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com', 
            password='userpassword'
        )
        
        # Create buyer preferences (required by Buyer model)
        self.buyer_preferences = BuyerPreferences.objects.create(
            preferred_materials=["cotton", "linen"],
            preferred_styles=["casual", "formal"],
            size_preferences={"shirt": "M", "pants": "32"},
            max_price=Decimal('500.00')
        )
        
        # Create a buyer with preferences
        self.buyer = Buyer.objects.create(
            user=self.regular_user,
            preferences=self.buyer_preferences
        )
        
        # Create a designer
        self.designer_user = User.objects.create_user(
            username='designer',
            email='designer@example.com',
            password='designerpassword'
        )
        
        self.designer = Designer.objects.create(
            user=self.designer_user,
            is_approved=True
        )
        
        # Create a design
        self.design = Design.objects.create(
            design_id="TEST-DSG-001",
            name="Test Design",
            description="This is a test design",
            designer=self.designer,
            price=Decimal('100.00'),
            status="PUBLISHED"
        )
        
        # Create payment info
        self.payment_info = PaymentInfo.objects.create(
            payment_id="PAY-TEST-001",
            method="CREDIT_CARD",
            amount=Decimal('150.00'),
            status="COMPLETED"
        )
        
        # Create delivery info
        self.delivery_info = DeliveryInfo.objects.create(
            tracking_number="TRK-TEST-001",
            carrier="Test Carrier",
            address="123 Test Street, Test City",
            estimated_delivery_date=timezone.now().date(),
            status="PROCESSING"
        )
        
        # Create test data - order with all required fields
        self.order = Order.objects.create(
            order_id='ORD123456',
            buyer=self.buyer,
            design=self.design,
            quantity=1,
            customizations={},
            status="PENDING",
            total_price=Decimal('150.00'),
            payment_info=self.payment_info,
            delivery_info=self.delivery_info
        )
        
        # Create transaction
        self.transaction = Transaction.objects.create(
            transaction_id='TRX123456',
            order=self.order,
            amount=Decimal('100.00'),
            type='SALE',
            status='COMPLETED',
            date=timezone.now()
        )
        
        # Setup client
        self.client = Client()
    
    @patch('django.template.loader.get_template', side_effect=mock_get_template)
    def test_transaction_list_view_admin_access(self, mock_get_template):
        """Test admin can access transaction list view"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('transactions:transaction_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_list_view_unauthorized(self):
        """Test unauthorized users cannot access transaction list"""
        # No login
        response = self.client.get(reverse('transactions:transaction_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Regular user login (non-admin)
        self.client.login(username='user', password='userpassword')
        response = self.client.get(reverse('transactions:transaction_list'))
        self.assertEqual(response.status_code, 302)  # Should be redirected
    
    @patch('django.template.loader.get_template', side_effect=mock_get_template)
    def test_transaction_detail_view_admin_access(self, mock_get_template):
        """Test admin can access transaction detail view"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(
            reverse('transactions:transaction_detail', 
                   kwargs={'transaction_id': self.transaction.transaction_id})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_transaction_detail_view_unauthorized(self):
        """Test unauthorized users cannot access transaction detail"""
        # No login
        response = self.client.get(
            reverse('transactions:transaction_detail', 
                   kwargs={'transaction_id': self.transaction.transaction_id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Regular user login (non-admin)
        self.client.login(username='user', password='userpassword')
        response = self.client.get(
            reverse('transactions:transaction_detail', 
                   kwargs={'transaction_id': self.transaction.transaction_id})
        )
        self.assertEqual(response.status_code, 302)  # Should be redirected
    
    @patch('django.template.loader.get_template', side_effect=mock_get_template)
    def test_transaction_stats_view(self, mock_get_template):
        """Test transaction stats view with admin access"""
        self.client.login(username='admin', password='adminpassword')
        
        # Set X-Requested-With header for AJAX request
        response = self.client.get(
            reverse('transactions:transaction_stats'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    @patch('django.template.loader.get_template', side_effect=mock_get_template)
    def test_transaction_report_view(self, mock_get_template):
        """Test transaction report view with admin access"""
        self.client.login(username='admin', password='adminpassword')
        
        # Test with AJAX request
        response = self.client.get(
            reverse('transactions:transaction_report'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
