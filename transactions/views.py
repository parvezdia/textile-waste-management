from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from .models import Transaction

def is_admin(user):
    return user.is_staff or (hasattr(user, 'admin') and user.admin is not None)

@login_required
@user_passes_test(is_admin)
def transaction_list(request):
    transactions = Transaction.objects.all().order_by('-date')
    return render(request, 'transactions/transaction_list.html', {
        'transactions': transactions
    })

@login_required
@user_passes_test(is_admin)
def transaction_detail(request, transaction_id):
    transaction = get_object_or_404(Transaction, transaction_id=transaction_id)
    return render(request, 'transactions/transaction_detail.html', {
        'transaction': transaction
    })

@login_required
@user_passes_test(is_admin)
def transaction_stats(request):
    # Get date range from request or default to last 30 days
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    transactions = Transaction.objects.filter(date__gte=start_date)
    
    # Calculate statistics
    stats = {
        'total_transactions': transactions.count(),
        'total_amount': transactions.aggregate(Sum('amount'))['amount__sum'] or 0,
        'sales': transactions.filter(type='SALE').count(),
        'refunds': transactions.filter(type='REFUND').count(),
        'by_status': {
            status: transactions.filter(status=status).count()
            for status, _ in Transaction.TRANSACTION_STATUS_CHOICES
        }
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(stats)
    return render(request, 'transactions/transaction_stats.html', {'stats': stats})

@login_required
@user_passes_test(is_admin)
def transaction_report(request):
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    transactions = Transaction.objects.all()
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    
    # Generate report data
    report_data = {
        'period': f"{start_date} to {end_date}" if start_date and end_date else "All time",
        'total_revenue': transactions.filter(type='SALE').aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_refunds': transactions.filter(type='REFUND').aggregate(Sum('amount'))['amount__sum'] or 0,
        'net_income': (
            (transactions.filter(type='SALE').aggregate(Sum('amount'))['amount__sum'] or 0) -
            (transactions.filter(type='REFUND').aggregate(Sum('amount'))['amount__sum'] or 0)
        ),
        'transactions_by_type': {
            ttype: transactions.filter(type=ttype).count()
            for ttype, _ in Transaction.TRANSACTION_TYPE_CHOICES
        }
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(report_data)
    return render(request, 'transactions/transaction_report.html', {'report': report_data})
