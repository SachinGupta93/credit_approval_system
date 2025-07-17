"""
Main URL configuration for credit_system project.

This file defines the URL patterns for the credit approval system.
It includes the main API endpoints and admin interface.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    """
    Simple health check endpoint to verify the service is running.
    Used by Docker and load balancers to check service status.
    """
    return JsonResponse({'status': 'healthy', 'service': 'credit_approval_system'})

urlpatterns = [
    # Admin interface for managing data
    path('admin/', admin.site.urls),
    
    # Health check endpoint
    path('health/', health_check, name='health_check'),
    
    # API endpoints - all credit approval system APIs
    path('', include('credit_system.api.urls')),
]