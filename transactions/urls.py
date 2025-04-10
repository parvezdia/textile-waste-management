from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('stats/', views.transaction_stats, name='transaction_stats'),
    path('report/', views.transaction_report, name='transaction_report'),
    path('<str:transaction_id>/', views.transaction_detail, name='transaction_detail'),
]