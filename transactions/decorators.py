from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import Transaction

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_staff or hasattr(request.user, 'admin')):
            messages.error(request, "Access denied. Administrator privileges required.")
            return redirect('transactions:transaction_list')
        return view_func(request, *args, **kwargs)
    return wrapper

def can_view_transaction(view_func):
    @wraps(view_func)
    def wrapper(request, transaction_id=None, *args, **kwargs):
        if transaction_id:
            transaction = Transaction.objects.filter(transaction_id=transaction_id).first()
            if not transaction:
                messages.error(request, "Transaction not found.")
                return redirect('transactions:transaction_list')
            
            # Allow admin access
            is_admin = request.user.is_staff or hasattr(request.user, 'admin')
            # Allow buyer access to their own transactions
            is_buyer = (hasattr(request.user, 'buyer') and 
                       transaction.order and 
                       transaction.order.buyer == request.user.buyer)
            
            if not (is_admin or is_buyer):
                messages.error(request, "Access denied. You don't have permission to view this transaction.")
                return redirect('transactions:transaction_list')
        
        return view_func(request, transaction_id, *args, **kwargs)
    return wrapper

def can_manage_transaction(view_func):
    @wraps(view_func)
    def wrapper(request, transaction_id=None, *args, **kwargs):
        # Only admins can manage transactions
        if not (request.user.is_staff or hasattr(request.user, 'admin')):
            messages.error(request, "Access denied. Administrator privileges required.")
            return redirect('transactions:transaction_list')
            
        if transaction_id:
            transaction = Transaction.objects.filter(transaction_id=transaction_id).first()
            if not transaction:
                messages.error(request, "Transaction not found.")
                return redirect('transactions:transaction_list')
        
        return view_func(request, transaction_id, *args, **kwargs)
    return wrapper

def can_generate_reports(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Only admins can generate financial reports
        if not (request.user.is_staff or hasattr(request.user, 'admin')):
            messages.error(request, "Access denied. Administrator privileges required.")
            return redirect('transactions:transaction_list')
        return view_func(request, *args, **kwargs)
    return wrapper