"""
Celery tasks for background processing.

This module contains Celery tasks for:
- Data ingestion from Excel files
- Credit score recalculation
- Data cleanup and maintenance
- Batch processing operations

These tasks run in the background to avoid blocking the API.
"""

import os
import pandas as pd
from celery import shared_task
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from credit_system.core.models import Customer, Loan, CreditScore
from credit_system.api.credit_scoring import CreditScoreCalculator
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def load_customer_data(self, file_path=None):
    """
    Load customer data from Excel file.
    
    This task reads customer data from customer_data.xlsx and creates
    Customer records in the database. It handles data validation and
    error reporting.
    
    Args:
        file_path: Path to the Excel file (optional)
        
    Returns:
        dict: Task result with statistics
    """
    try:
        # Use default file path if not provided
        if file_path is None:
            file_path = os.path.join(settings.BASE_DIR, 'data', 'customer_data.xlsx')
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"Customer data file not found: {file_path}")
            return {
                'success': False,
                'error': 'Customer data file not found',
                'file_path': file_path
            }
        
        # Read Excel file
        logger.info(f"Loading customer data from: {file_path}")
        df = pd.read_excel(file_path)
        
        # Validate required columns
        required_columns = [
            'customer_id', 'first_name', 'last_name', 'phone_number',
            'monthly_salary', 'approved_limit', 'current_debt'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return {
                'success': False,
                'error': f'Missing required columns: {missing_columns}',
                'file_path': file_path
            }
        
        # Process data
        created_count = 0
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Extract data from row
                    customer_data = {
                        'first_name': str(row['first_name']).strip(),
                        'last_name': str(row['last_name']).strip(),
                        'phone_number': int(row['phone_number']),
                        'monthly_income': Decimal(str(row['monthly_salary'])),
                        'approved_limit': Decimal(str(row['approved_limit'])),
                        'current_debt': Decimal(str(row['current_debt'])),
                        'age': int(row.get('age', 25))  # Default age if not provided
                    }
                    
                    # Create or update customer
                    customer, created = Customer.objects.update_or_create(
                        phone_number=customer_data['phone_number'],
                        defaults=customer_data
                    )
                    
                    if created:
                        created_count += 1
                        logger.info(f"Created customer: {customer.full_name}")
                    else:
                        updated_count += 1
                        logger.info(f"Updated customer: {customer.full_name}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing row {index}: {str(e)}")
                    continue
        
        logger.info(f"Customer data loading completed: {created_count} created, {updated_count} updated, {error_count} errors")
        
        return {
            'success': True,
            'created_count': created_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'total_rows': len(df),
            'file_path': file_path
        }
        
    except Exception as e:
        logger.error(f"Error loading customer data: {str(e)}")
        # Retry the task if it fails
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task in 60 seconds (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=60, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'file_path': file_path
        }


@shared_task(bind=True, max_retries=3)
def load_loan_data(self, file_path=None):
    """
    Load loan data from Excel file.
    
    This task reads loan data from loan_data.xlsx and creates
    Loan records in the database. It handles data validation and
    links loans to existing customers.
    
    Args:
        file_path: Path to the Excel file (optional)
        
    Returns:
        dict: Task result with statistics
    """
    try:
        # Use default file path if not provided
        if file_path is None:
            file_path = os.path.join(settings.BASE_DIR, 'data', 'loan_data.xlsx')
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"Loan data file not found: {file_path}")
            return {
                'success': False,
                'error': 'Loan data file not found',
                'file_path': file_path
            }
        
        # Read Excel file
        logger.info(f"Loading loan data from: {file_path}")
        df = pd.read_excel(file_path)
        
        # Validate required columns
        required_columns = [
            'customer_id', 'loan_id', 'loan_amount', 'tenure',
            'interest_rate', 'monthly_repayment', 'EMIs_paid_on_time',
            'start_date', 'end_date'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return {
                'success': False,
                'error': f'Missing required columns: {missing_columns}',
                'file_path': file_path
            }
        
        # Process data
        created_count = 0
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    # Find customer by ID (assuming customer_id from Excel matches phone_number)
                    customer = None
                    try:
                        customer = Customer.objects.get(phone_number=int(row['customer_id']))
                    except Customer.DoesNotExist:
                        logger.warning(f"Customer not found for ID: {row['customer_id']}")
                        error_count += 1
                        continue
                    
                    # Parse dates
                    start_date = pd.to_datetime(row['start_date']).date()
                    end_date = pd.to_datetime(row['end_date']).date()
                    
                    # Extract loan data
                    loan_data = {
                        'customer': customer,
                        'legacy_loan_id': str(row['loan_id']),
                        'loan_amount': Decimal(str(row['loan_amount'])),
                        'tenure': int(row['tenure']),
                        'interest_rate': Decimal(str(row['interest_rate'])),
                        'monthly_repayment': Decimal(str(row['monthly_repayment'])),
                        'emis_paid_on_time': int(row['EMIs_paid_on_time']),
                        'start_date': start_date,
                        'end_date': end_date,
                        'loan_approved': True  # Historical data is assumed approved
                    }
                    
                    # Create or update loan using legacy_loan_id
                    loan, created = Loan.objects.update_or_create(
                        legacy_loan_id=str(row['loan_id']),
                        defaults=loan_data
                    )
                    
                    if created:
                        created_count += 1
                        logger.info(f"Created loan: {loan.loan_id} for {customer.full_name}")
                    else:
                        updated_count += 1
                        logger.info(f"Updated loan: {loan.loan_id} for {customer.full_name}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing loan row {index}: {str(e)}")
                    continue
        
        logger.info(f"Loan data loading completed: {created_count} created, {updated_count} updated, {error_count} errors")
        
        # Update customer debt amounts after loading loans
        update_all_customer_debts.delay()
        
        return {
            'success': True,
            'created_count': created_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'total_rows': len(df),
            'file_path': file_path
        }
        
    except Exception as e:
        logger.error(f"Error loading loan data: {str(e)}")
        # Retry the task if it fails
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task in 60 seconds (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=60, exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'file_path': file_path
        }


@shared_task
def load_initial_data():
    """
    Load both customer and loan data sequentially.
    
    This task coordinates the loading of both Excel files and ensures
    proper sequencing (customers first, then loans).
    
    Returns:
        dict: Combined task result
    """
    logger.info("Starting initial data load...")
    
    # Load customer data first
    customer_result = load_customer_data.apply()
    
    if not customer_result.get('success', False):
        logger.error("Failed to load customer data, aborting loan data load")
        return {
            'success': False,
            'error': 'Customer data load failed',
            'customer_result': customer_result
        }
    
    # Load loan data second
    loan_result = load_loan_data.apply()
    
    logger.info("Initial data load completed")
    
    return {
        'success': True,
        'customer_result': customer_result,
        'loan_result': loan_result
    }


@shared_task
def update_all_customer_debts():
    """
    Update current debt for all customers.
    
    This task recalculates the current debt for all customers
    based on their active loans.
    
    Returns:
        dict: Task result with statistics
    """
    logger.info("Updating all customer debts...")
    
    updated_count = 0
    error_count = 0
    
    for customer in Customer.objects.all():
        try:
            old_debt = customer.current_debt
            new_debt = customer.update_current_debt()
            
            if old_debt != new_debt:
                updated_count += 1
                logger.info(f"Updated debt for {customer.full_name}: {old_debt} -> {new_debt}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error updating debt for customer {customer.id}: {str(e)}")
    
    logger.info(f"Customer debt update completed: {updated_count} updated, {error_count} errors")
    
    return {
        'success': True,
        'updated_count': updated_count,
        'error_count': error_count,
        'total_customers': Customer.objects.count()
    }


@shared_task
def recalculate_all_credit_scores():
    """
    Recalculate credit scores for all customers.
    
    This task recalculates and updates credit scores for all customers.
    It's useful for batch updates and periodic recalculation.
    
    Returns:
        dict: Task result with statistics
    """
    logger.info("Recalculating all credit scores...")
    
    updated_count = 0
    error_count = 0
    
    for customer in Customer.objects.all():
        try:
            calculator = CreditScoreCalculator(customer)
            score_data = calculator.calculate_credit_score()
            calculator.save_credit_score(score_data)
            
            updated_count += 1
            logger.info(f"Updated credit score for {customer.full_name}: {score_data['overall_score']}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error calculating credit score for customer {customer.id}: {str(e)}")
    
    logger.info(f"Credit score recalculation completed: {updated_count} updated, {error_count} errors")
    
    return {
        'success': True,
        'updated_count': updated_count,
        'error_count': error_count,
        'total_customers': Customer.objects.count()
    }


@shared_task
def cleanup_old_data():
    """
    Clean up old data and perform maintenance tasks.
    
    This task performs periodic cleanup operations like:
    - Removing old credit score records
    - Cleaning up expired sessions
    - Optimizing database
    
    Returns:
        dict: Task result with statistics
    """
    logger.info("Starting data cleanup...")
    
    cleaned_count = 0
    
    try:
        # Clean up old credit scores (older than 30 days)
        old_scores_cutoff = timezone.now() - timedelta(days=30)
        old_scores = CreditScore.objects.filter(calculated_at__lt=old_scores_cutoff)
        
        # Keep only the latest score for each customer
        customers_with_old_scores = old_scores.values_list('customer_id', flat=True).distinct()
        
        for customer_id in customers_with_old_scores:
            # Keep only the latest score for this customer
            latest_score = CreditScore.objects.filter(
                customer_id=customer_id
            ).order_by('-calculated_at').first()
            
            if latest_score:
                # Delete all other scores for this customer
                deleted_count = CreditScore.objects.filter(
                    customer_id=customer_id
                ).exclude(id=latest_score.id).delete()[0]
                
                cleaned_count += deleted_count
        
        logger.info(f"Data cleanup completed: {cleaned_count} old records removed")
        
        return {
            'success': True,
            'cleaned_count': cleaned_count
        }
        
    except Exception as e:
        logger.error(f"Error during data cleanup: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_test_data(num_customers=10, num_loans_per_customer=3):
    """
    Generate test data for development and testing.
    
    This task creates sample customers and loans for testing purposes.
    
    Args:
        num_customers: Number of customers to create
        num_loans_per_customer: Number of loans per customer
        
    Returns:
        dict: Task result with statistics
    """
    logger.info(f"Generating test data: {num_customers} customers, {num_loans_per_customer} loans each")
    
    import random
    from faker import Faker
    
    fake = Faker()
    created_customers = 0
    created_loans = 0
    
    try:
        with transaction.atomic():
            for i in range(num_customers):
                # Create customer
                customer = Customer.objects.create(
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    age=random.randint(18, 65),
                    phone_number=fake.unique.random_number(digits=10),
                    monthly_income=Decimal(random.randint(25000, 100000)),
                    approved_limit=Decimal(random.randint(500000, 3600000)),
                    current_debt=Decimal(0)
                )
                created_customers += 1
                
                # Create loans for customer
                for j in range(num_loans_per_customer):
                    start_date = fake.date_between(start_date='-2y', end_date='today')
                    tenure = random.randint(6, 60)
                    
                    loan = Loan.objects.create(
                        customer=customer,
                        loan_amount=Decimal(random.randint(50000, 500000)),
                        tenure=tenure,
                        interest_rate=Decimal(random.uniform(8.0, 18.0)),
                        emis_paid_on_time=random.randint(0, tenure),
                        start_date=start_date,
                        loan_approved=True
                    )
                    created_loans += 1
                
                # Update customer debt
                customer.update_current_debt()
        
        logger.info(f"Test data generation completed: {created_customers} customers, {created_loans} loans")
        
        return {
            'success': True,
            'created_customers': created_customers,
            'created_loans': created_loans
        }
        
    except Exception as e:
        logger.error(f"Error generating test data: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }