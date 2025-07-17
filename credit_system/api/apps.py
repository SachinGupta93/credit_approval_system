"""
API application configuration.

This module contains the Django app configuration for the REST API
application that handles all external API endpoints.
"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """
    Configuration for the API application.
    
    This app contains the REST API endpoints, serializers,
    and business logic for the credit approval system.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'credit_system.api'
    verbose_name = 'REST API'
    
    def ready(self):
        """
        Called when the app is ready.
        
        This method is called when Django starts up and can be used
        to register signals, initialize background tasks, etc.
        """
        # Import and register any signals
        # from . import signals
        pass