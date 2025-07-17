"""
Celery configuration for credit_system project.

This file configures Celery for handling background tasks like:
- Data ingestion from Excel files
- Credit score calculations
- Loan processing tasks
- Periodic data cleanup

Celery is used to handle time-consuming operations without blocking the API.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_system.settings')

# Create Celery application instance
app = Celery('credit_system')

# Configure Celery using Django settings
# namespace='CELERY' means all celery-related configuration keys should have a `CELERY_` prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()

# Celery beat schedule for periodic tasks (if needed)
app.conf.beat_schedule = {
    # Example: Clean up old data every day at midnight
    'cleanup-old-data': {
        'task': 'credit_system.api.tasks.cleanup_old_data',
        'schedule': 60.0 * 60.0 * 24.0,  # Every 24 hours
    },
    # Example: Recalculate credit scores every hour
    'recalculate-credit-scores': {
        'task': 'credit_system.api.tasks.recalculate_all_credit_scores',
        'schedule': 60.0 * 60.0,  # Every hour
    },
}

# Set timezone for Celery beat
app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    """
    Debug task to test if Celery is working properly.
    Can be called to verify the Celery worker is running.
    """
    print(f'Request: {self.request!r}')