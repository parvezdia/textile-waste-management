import uuid
from datetime import datetime, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from .models import Transaction

def generate_transaction_id(prefix='TXN'):
    """Generate a unique transaction ID"""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

def calculate_period_revenue(start_date=None, end_date=None):
    """Calculate revenue for a given period"""
    transactions = Transaction.objects.filter(type='SALE')
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    
    return {
        'total_revenue': transactions.filter(status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0,
        'pending_revenue': transactions.filter(status='PENDING').aggregate(Sum('amount'))['amount__sum'] or 0,
        'transaction_count': transactions.count()
    }

def generate_daily_report(days=30):
    """Generate daily transaction report"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    daily_transactions = (
        Transaction.objects
        .filter(date__range=(start_date, end_date))
        .annotate(day=TruncDate('date'))
        .values('day', 'type')
        .annotate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        .order_by('day', 'type')
    )
    
    return daily_transactions

def calculate_refund_rate():
    """Calculate refund rate statistics"""
    total_sales = Transaction.objects.filter(type='SALE').count()
    total_refunds = Transaction.objects.filter(type='REFUND').count()
    
    return {
        'total_sales': total_sales,
        'total_refunds': total_refunds,
        'refund_rate': (total_refunds / total_sales * 100) if total_sales > 0 else 0
    }

def validate_transaction_amount(amount):
    """Validate transaction amount"""
    try:
        amount = float(amount)
        return amount > 0
    except (TypeError, ValueError):
        return False

def get_transaction_summary(transaction_id):
    """Get detailed summary of a transaction"""
    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
        return {
            'transaction_id': transaction.transaction_id,
            'order_id': transaction.order.order_id,
            'buyer': transaction.order.buyer.user.username,
            'amount': transaction.amount,
            'type': transaction.type,
            'status': transaction.status,
            'date': transaction.date,
            'design': transaction.order.design.name
        }
    except Transaction.DoesNotExist:
        return None