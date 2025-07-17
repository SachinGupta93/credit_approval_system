"""
Django management command to update credit scores for all customers.

This command recalculates credit scores for all customers based on their
current loan history and payment patterns.

Usage:
    python manage.py update_credit_scores
    python manage.py update_credit_scores --customer-id 123
    python manage.py update_credit_scores --async
"""

from django.core.management.base import BaseCommand, CommandError
from credit_system.core.models import Customer, CreditScore
from credit_system.api.credit_scoring import CreditScoreCalculator
from credit_system.api.tasks import recalculate_all_credit_scores
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to update credit scores.
    
    This command provides options to:
    - Update credit scores for all customers
    - Update credit score for a specific customer
    - Run updates asynchronously using Celery
    """
    
    help = 'Update credit scores for customers'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--customer-id',
            type=int,
            help='Update credit score for specific customer ID'
        )
        
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run credit score updates asynchronously using Celery'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Display detailed progress information'
        )
    
    def handle(self, *args, **options):
        """
        Main command handler.
        
        This method orchestrates the credit score update process based on
        the provided command line arguments.
        """
        self.stdout.write(self.style.SUCCESS('Starting credit score update process...'))
        
        # Update specific customer if ID provided
        if options['customer_id']:
            self._update_single_customer(options['customer_id'], options)
        else:
            # Update all customers
            self._update_all_customers(options)
        
        self.stdout.write(self.style.SUCCESS('Credit score update process completed!'))
    
    def _update_single_customer(self, customer_id, options):
        """
        Update credit score for a single customer.
        
        Args:
            customer_id: ID of the customer to update
            options: Command line options dictionary
        """
        try:
            # Get the customer
            customer = Customer.objects.get(id=customer_id)
            
            self.stdout.write(f'Updating credit score for customer: {customer.full_name}')
            
            # Calculate new credit score
            calculator = CreditScoreCalculator(customer)
            score_data = calculator.calculate_credit_score()
            
            # Save the score
            credit_score = calculator.save_credit_score(score_data)
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f'Credit score updated: {credit_score.score} ({credit_score.score_grade})'
                )
            )
            
            if options['verbose']:
                self._display_score_details(credit_score)
            
        except Customer.DoesNotExist:
            raise CommandError(f'Customer with ID {customer_id} not found')
        except Exception as e:
            raise CommandError(f'Error updating credit score: {str(e)}')
    
    def _update_all_customers(self, options):
        """
        Update credit scores for all customers.
        
        Args:
            options: Command line options dictionary
        """
        try:
            # Get total customer count
            total_customers = Customer.objects.count()
            
            if total_customers == 0:
                self.stdout.write(
                    self.style.WARNING('No customers found in database.')
                )
                return
            
            self.stdout.write(f'Updating credit scores for {total_customers} customers...')
            
            # Run asynchronously if requested
            if options['async']:
                task = recalculate_all_credit_scores.delay()
                self.stdout.write(f'Credit score update task queued: {task.id}')
                return
            
            # Run synchronously
            updated_count = 0
            error_count = 0
            
            for customer in Customer.objects.all():
                try:
                    # Calculate new credit score
                    calculator = CreditScoreCalculator(customer)
                    score_data = calculator.calculate_credit_score()
                    
                    # Save the score
                    credit_score = calculator.save_credit_score(score_data)
                    updated_count += 1
                    
                    if options['verbose']:
                        self.stdout.write(
                            f'Updated {customer.full_name}: {credit_score.score} ({credit_score.score_grade})'
                        )
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error updating {customer.full_name}: {str(e)}'
                        )
                    )
            
            # Display summary
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {updated_count} credit scores'
                )
            )
            
            if error_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Encountered {error_count} errors')
                )
            
        except Exception as e:
            raise CommandError(f'Error updating credit scores: {str(e)}')
    
    def _display_score_details(self, credit_score):
        """
        Display detailed credit score information.
        
        Args:
            credit_score: CreditScore instance
        """
        self.stdout.write('  Score Components:')
        self.stdout.write(f'    Past Loans Performance: {credit_score.past_loans_score}')
        self.stdout.write(f'    Loan Volume: {credit_score.loan_volume_score}')
        self.stdout.write(f'    Current Year Activity: {credit_score.current_year_score}')
        self.stdout.write(f'    Credit Utilization: {credit_score.credit_utilization_score}')
        self.stdout.write(f'    Last Updated: {credit_score.calculated_at}')
    
    def _get_score_statistics(self):
        """
        Get overall credit score statistics.
        
        Returns:
            dict: Statistics about credit scores
        """
        scores = CreditScore.objects.all()
        
        if not scores.exists():
            return {
                'total': 0,
                'average': 0,
                'excellent': 0,
                'good': 0,
                'fair': 0,
                'poor': 0
            }
        
        total = scores.count()
        average = scores.aggregate(avg=models.Avg('score'))['avg'] or 0
        
        excellent = scores.filter(score__gte=50).count()
        good = scores.filter(score__gte=30, score__lt=50).count()
        fair = scores.filter(score__gte=10, score__lt=30).count()
        poor = scores.filter(score__lt=10).count()
        
        return {
            'total': total,
            'average': round(average, 2),
            'excellent': excellent,
            'good': good,
            'fair': fair,
            'poor': poor
        }


# Import for models reference
from django.db import models