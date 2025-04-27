from django.test import TestCase
from unittest.mock import patch
from django.utils import timezone
from orders.utils import check_order_cancellable

# Create your tests here.

class OrderModelUnitTest(TestCase):

    def setUp(self):
        from decimal import Decimal
        from django.contrib.auth import get_user_model
        from orders.models import Order, PaymentInfo, DeliveryInfo
        from accounts.models import Buyer, BuyerPreferences, Designer
        from designs.models import Design
        import uuid
        import datetime
        # Create user, buyer, designer, design, preferences
        User = get_user_model()
        user = User.objects.create_user(username="buyer", email="buyer@example.com", password="testpass123")
        designer_user = User.objects.create_user(username="designer", email="designer@example.com", password="testpass123")
        prefs = BuyerPreferences.objects.create()
        buyer = Buyer.objects.create(user=user, preferences=prefs)
        designer = Designer.objects.create(user=designer_user)
        design = Design.objects.create(design_id=f"DSG-{uuid.uuid4().hex[:8].upper()}", name="Test Design", description="desc", designer=designer, price=Decimal('100.00'))
        # Create PaymentInfo and DeliveryInfo
        payment_info = PaymentInfo.objects.create(
            payment_id=f"PAY-{uuid.uuid4().hex[:8].upper()}",
            method="CREDIT_CARD",
            amount=Decimal('100.00'),
            status="COMPLETED"
        )
        delivery_info = DeliveryInfo.objects.create(
            tracking_number=f"TRK-{uuid.uuid4().hex[:8].upper()}",
            carrier="TestCarrier",
            address="123 Test St",
            estimated_delivery_date=datetime.date.today() + datetime.timedelta(days=7),
            status="PROCESSING"
        )
        # Create order
        self.order = Order.objects.create(
            order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            buyer=buyer,
            design=design,
            quantity=1,
            customizations={},
            status="PENDING",
            date_ordered=timezone.now(),
            total_price=Decimal('100.00'),
            payment_info=payment_info,
            delivery_info=delivery_info
        )
        # Create PaymentInfo and DeliveryInfo for old order
        payment_info2 = PaymentInfo.objects.create(
            payment_id=f"PAY-{uuid.uuid4().hex[:8].upper()}",
            method="CREDIT_CARD",
            amount=Decimal('100.00'),
            status="COMPLETED"
        )
        delivery_info2 = DeliveryInfo.objects.create(
            tracking_number=f"TRK-{uuid.uuid4().hex[:8].upper()}",
            carrier="TestCarrier",
            address="123 Test St",
            estimated_delivery_date=datetime.date.today() + datetime.timedelta(days=7),
            status="PROCESSING"
        )
        # Create old pending order
        self.old_pending_order = Order.objects.create(
            order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            buyer=buyer,
            design=design,
            quantity=1,
            customizations={},
            status="PENDING",
            date_ordered=timezone.now() - timezone.timedelta(hours=25),
            total_price=Decimal('100.00'),
            payment_info=payment_info2,
            delivery_info=delivery_info2
        )

    @patch('notifications.models.Notification.objects.create')
    def test_cancel_order_success(self, mock_notification):
        """Test successful order cancellation"""
        result = self.order.cancel_order()
        self.assertTrue(result)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "CANCELED")
        mock_notification.assert_called_once()

    @patch('notifications.models.Notification.objects.create')
    def test_cancel_order_failure(self, mock_notification):
        """Test order cancellation failure for delivered order"""
        self.order.status = "DELIVERED"
        self.order.save()
        result = self.order.cancel_order()
        self.assertFalse(result)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "DELIVERED")
        mock_notification.assert_not_called()

    def test_check_order_cancellable_false_time(self):
        """Test order is not cancellable when older than 24 hours"""
        self.old_pending_order.date_ordered = timezone.now() - timezone.timedelta(days=2)
        self.old_pending_order.save()
        self.old_pending_order.refresh_from_db()
        print(f"DEBUG: old_pending_order.date_ordered={self.old_pending_order.date_ordered}, now={timezone.now()}")
        self.assertFalse(check_order_cancellable(self.old_pending_order))
