"""
URL configuration for the credit approval system API.

This module defines all the API endpoints and their corresponding views:
- /register - Register new customer
- /check-eligibility - Check loan eligibility
- /create-loan - Create new loan
- /view-loan/<uuid:loan_id> - View loan details
- /view-loans/<int:customer_id> - View customer loans
- /status - API health status
- /customer/<int:customer_id>/credit-score - Get customer credit score (bonus)
"""

from django.urls import path
from . import views

# API URL patterns
urlpatterns = [
    # Welcome/root endpoint
    path('', views.welcome, name='welcome'),
    
    # Main API endpoints as per requirements
    path('register', views.register_customer, name='register_customer'),
    path('check-eligibility', views.check_loan_eligibility, name='check_loan_eligibility'),
    path('create-loan', views.create_loan, name='create_loan'),
    path('view-loan/<uuid:loan_id>', views.view_loan, name='view_loan'),
    path('view-loans/<int:customer_id>', views.view_customer_loans, name='view_customer_loans'),
    
    # Additional utility endpoints
    path('status', views.api_status, name='api_status'),
    path('customer/<int:customer_id>/credit-score', views.customer_credit_score, name='customer_credit_score'),
]