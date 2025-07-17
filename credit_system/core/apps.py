"""
Core application configuration.

This module contains the Django app configuration for the core
business logic application.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Configuration for the core application.
    
    This app contains the main business logic, models, and
    core functionality for the credit approval system.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'credit_system.core'
    verbose_name = 'Core Business Logic'
    
    def ready(self):
        """
        Called when the app is ready.
        
        This method is called when Django starts up and can be used
        to register signals, initialize caches, etc.
        """
        # Import signals if any
        # from . import signals
        pass