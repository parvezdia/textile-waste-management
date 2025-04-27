from django.test import TestCase
from unittest.mock import patch, MagicMock

from orders.models import Order


class OrderNotificationIntegrationTest(TestCase):
    """Integration tests for order and notification interactions"""
    
    @patch('notifications.models.Notification.objects.create')
    def test_order_status_update_triggers_notification(self, mock_notification_create):
        """Test that updating an order's status triggers a notification"""
        # Create mock objects
        mock_order = MagicMock(spec=Order)
        mock_buyer = MagicMock()
        mock_buyer.user = MagicMock()
        mock_order.buyer = mock_buyer
        mock_order.order_id = "TEST123"
        
        # Call the update_status method with a mocked Order instance
        Order.update_status(mock_order, "CONFIRMED")
        
        # Verify notification creation was called with the right parameters
        mock_notification_create.assert_called_once()
        args, kwargs = mock_notification_create.call_args
        self.assertEqual(kwargs['recipient'], mock_buyer.user)
        self.assertEqual(kwargs['type'], "ORDER_UPDATE")
        self.assertIn("CONFIRMED", kwargs['message'])
    
    @patch('notifications.models.Notification.objects.create')
    def test_order_cancellation_triggers_notification(self, mock_notification_create):
        """Test that cancelling an order triggers a notification"""
        # Create mock objects
        mock_order = MagicMock(spec=Order)
        mock_buyer = MagicMock()
        mock_buyer.user = MagicMock()
        mock_order.buyer = mock_buyer
        mock_order.status = "PENDING"
        mock_order.order_id = "TEST123"
        
        # Call the cancel_order method with a mocked Order instance
        result = Order.cancel_order(mock_order)
        
        # Verify the result and notification
        self.assertTrue(result)
        mock_notification_create.assert_called_once()
        args, kwargs = mock_notification_create.call_args
        self.assertEqual(kwargs['recipient'], mock_buyer.user)
        self.assertEqual(kwargs['type'], "ORDER_UPDATE")
        self.assertIn("cancelled", kwargs['message'])
    
    @patch('notifications.models.Notification.objects.create')
    def test_multiple_order_status_updates_create_multiple_notifications(self, mock_notification_create):
        """Test that multiple status updates create multiple notifications"""
        # Create mock objects
        mock_order = MagicMock(spec=Order)
        mock_buyer = MagicMock()
        mock_buyer.user = MagicMock()
        mock_order.buyer = mock_buyer
        mock_order.order_id = "TEST123"
        
        # Update status multiple times
        statuses = ["CONFIRMED", "IN_PRODUCTION", "READY_FOR_DELIVERY", "SHIPPED"]
        for status in statuses:
            Order.update_status(mock_order, status)
        
        # Verify notification was called for each status update
        self.assertEqual(mock_notification_create.call_count, len(statuses))
        
        # Check that each status was used in a notification
        calls = mock_notification_create.call_args_list
        for i, status in enumerate(statuses):
            args, kwargs = calls[i]
            self.assertEqual(kwargs['recipient'], mock_buyer.user)
            self.assertEqual(kwargs['type'], "ORDER_UPDATE")
            self.assertIn(status, kwargs['message'])