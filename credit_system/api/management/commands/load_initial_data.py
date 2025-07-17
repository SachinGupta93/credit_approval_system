"""
Django management command to load initial data from Excel files.

This command loads customer and loan data from Excel files located in the data/ directory.
It can be run manually or automatically during container startup.

Usage:
    python manage.py load_initial_data
    python manage.py load_initial_data --customers-only
    python manage.py load_initial_data --loans-only
    python manage.py load_initial_data --generate-test-data
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from credit_system.api.tasks import load_customer_data, load_loan_data, generate_test_data
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to load initial data from Excel files.
    
    This command provides various options for loading data:
    - Load customer data only
    - Load loan data only  
    - Load both customer and loan data
    - Generate test data for development
    """
    
    help = 'Load initial data from Excel files or generate test data'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--customers-only',
            action='store_true',
            help='Load only customer data from Excel file'
        )
        
        parser.add_argument(
            '--loans-only',
            action='store_true',
            help='Load only loan data from Excel file'
        )
        
        parser.add_argument(
            '--generate-test-data',
            action='store_true',
            help='Generate test data instead of loading from Excel files'
        )
        
        parser.add_argument(
            '--num-customers',
            type=int,
            default=10,
            help='Number of test customers to generate (default: 10)'
        )
        
        parser.add_argument(
            '--num-loans',
            type=int,
            default=3,
            help='Number of loans per customer for test data (default: 3)'
        )
        
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run data loading tasks asynchronously using Celery'
        )
    
    def handle(self, *args, **options):
        """
        Main command handler.
        
        This method orchestrates the data loading process based on the
        provided command line arguments.
        """
        self.stdout.write(self.style.SUCCESS('Starting data loading process...'))
        
        # Generate test data if requested
        if options['generate_test_data']:
            self._generate_test_data(options)
            return
        
        # Load data from Excel files
        if options['customers_only']:
            self._load_customers(options)
        elif options['loans_only']:
            self._load_loans(options)
        else:
            # Load both customers and loans
            self._load_customers(options)
            self._load_loans(options)
        
        self.stdout.write(self.style.SUCCESS('Data loading process completed!'))
    
    def _load_customers(self, options):
        """
        Load customer data from Excel file.
        
        Args:
            options: Command line options dictionary
        """
        self.stdout.write('Loading customer data...')
        
        # Define file path
        file_path = os.path.join(settings.BASE_DIR, 'data', 'customer_data.xlsx')
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.WARNING(f'Customer data file not found: {file_path}')
            )
            self.stdout.write(
                self.style.WARNING('Skipping customer data loading.')
            )
            return
        
        try:
            # Run task synchronously or asynchronously
            if options['async']:
                # Run asynchronously using Celery
                task = load_customer_data.delay(file_path)
                self.stdout.write(f'Customer data loading task queued: {task.id}')
            else:
                # Run synchronously
                result = load_customer_data.apply(args=[file_path])
                self._display_result('Customer data', result)
                
        except Exception as e:
            raise CommandError(f'Error loading customer data: {str(e)}')
    
    def _load_loans(self, options):
        """
        Load loan data from Excel file.
        
        Args:
            options: Command line options dictionary
        """
        self.stdout.write('Loading loan data...')
        
        # Define file path
        file_path = os.path.join(settings.BASE_DIR, 'data', 'loan_data.xlsx')
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.WARNING(f'Loan data file not found: {file_path}')
            )
            self.stdout.write(
                self.style.WARNING('Skipping loan data loading.')
            )
            return
        
        try:
            # Run task synchronously or asynchronously
            if options['async']:
                # Run asynchronously using Celery
                task = load_loan_data.delay(file_path)
                self.stdout.write(f'Loan data loading task queued: {task.id}')
            else:
                # Run synchronously
                result = load_loan_data.apply(args=[file_path])
                self._display_result('Loan data', result)
                
        except Exception as e:
            raise CommandError(f'Error loading loan data: {str(e)}')
    
    def _generate_test_data(self, options):
        """
        Generate test data for development.
        
        Args:
            options: Command line options dictionary
        """
        self.stdout.write('Generating test data...')
        
        num_customers = options['num_customers']
        num_loans = options['num_loans']
        
        self.stdout.write(f'Creating {num_customers} customers with {num_loans} loans each...')
        
        try:
            # Run task synchronously or asynchronously
            if options['async']:
                # Run asynchronously using Celery
                task = generate_test_data.delay(num_customers, num_loans)
                self.stdout.write(f'Test data generation task queued: {task.id}')
            else:
                # Run synchronously
                result = generate_test_data.apply(args=[num_customers, num_loans])
                self._display_result('Test data generation', result)
                
        except Exception as e:
            raise CommandError(f'Error generating test data: {str(e)}')
    
    def _display_result(self, operation, result):
        """
        Display the result of a data loading operation.
        
        Args:
            operation: Name of the operation
            result: Result dictionary from the task
        """
        if result.get('success', False):
            self.stdout.write(
                self.style.SUCCESS(f'{operation} completed successfully!')
            )
            
            # Display statistics
            if 'created_count' in result:
                self.stdout.write(f'  Created: {result["created_count"]} records')
            if 'updated_count' in result:
                self.stdout.write(f'  Updated: {result["updated_count"]} records')
            if 'error_count' in result:
                self.stdout.write(f'  Errors: {result["error_count"]} records')
            if 'total_rows' in result:
                self.stdout.write(f'  Total processed: {result["total_rows"]} rows')
            
        else:
            self.stdout.write(
                self.style.ERROR(f'{operation} failed!')
            )
            if 'error' in result:
                self.stdout.write(f'  Error: {result["error"]}')
    
    def _check_dependencies(self):
        """
        Check if all required dependencies are available.
        
        Returns:
            bool: True if all dependencies are available
        """
        try:
            import pandas
            import openpyxl
            return True
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'Missing required dependency: {str(e)}')
            )
            self.stdout.write(
                'Please install required packages: pip install pandas openpyxl'
            )
            return False