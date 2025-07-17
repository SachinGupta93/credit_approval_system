"""
Core models for the credit approval system.

This module defines the main database models:
- Customer: Stores customer information and credit limits
- Loan: Stores loan information and payment history

These models are used by the API endpoints to manage customer data
and loan applications.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class Customer(models.Model):
    """
    Customer model to store customer information.
    
    This model stores all customer-related data including:
    - Personal information (name, age, phone)
    - Financial information (monthly income, approved credit limit)
    - Current debt status
    
    The approved_limit is calculated as 36 times the monthly salary.
    """
    
    # Personal Information
    first_name = models.CharField(
        max_length=100,
        help_text="Customer's first name"
    )
    last_name = models.CharField(
        max_length=100,
        help_text="Customer's last name"
    )
    age = models.IntegerField(
        validators=[MinValueValidator(18), MaxValueValidator(100)],
        help_text="Customer's age (must be 18 or older)"
    )
    phone_number = models.BigIntegerField(
        unique=True,
        help_text="Customer's phone number (must be unique)"
    )
    
    # Financial Information
    monthly_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Customer's monthly income"
    )
    approved_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Approved credit limit (36 * monthly_income, rounded to nearest lakh)"
    )
    current_debt = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current outstanding debt amount"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the customer was registered"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the customer information was last updated"
    )
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.id})"
    
    @property
    def full_name(self):
        """Return the customer's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def credit_utilization(self):
        """Calculate current credit utilization percentage."""
        if self.approved_limit == 0:
            return 0
        return (self.current_debt / self.approved_limit) * 100
    
    def update_current_debt(self):
        """Update current debt based on active loans."""
        from django.db.models import Sum
        total_debt = self.loans.filter(
            loan_approved=True
        ).aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0.00')
        
        self.current_debt = total_debt
        self.save(update_fields=['current_debt', 'updated_at'])
        return self.current_debt


class Loan(models.Model):
    """
    Loan model to store loan information and payment history.
    
    This model stores:
    - Loan details (amount, tenure, interest rate)
    - Payment information (monthly installment, EMIs paid)
    - Loan status and approval information
    - Start and end dates
    """
    
    # Loan Identification
    loan_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Unique identifier for the loan"
    )
    
    # Legacy loan ID from Excel data (for data import)
    legacy_loan_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        help_text="Legacy loan ID from imported data"
    )
    
    # Customer Relationship
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='loans',
        help_text="Customer who applied for this loan"
    )
    
    # Loan Details
    loan_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1000.00'))],
        help_text="Amount of the loan"
    )
    tenure = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text="Loan tenure in months"
    )
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('50.00'))],
        help_text="Annual interest rate percentage"
    )
    
    # Payment Information
    monthly_repayment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monthly installment amount"
    )
    emis_paid_on_time = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of EMIs paid on time"
    )
    
    # Loan Status
    loan_approved = models.BooleanField(
        default=False,
        help_text="Whether the loan is approved"
    )
    
    # Dates
    start_date = models.DateField(
        help_text="Loan start date"
    )
    end_date = models.DateField(
        help_text="Loan end date"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the loan was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the loan was last updated"
    )
    
    class Meta:
        db_table = 'loans'
        verbose_name = 'Loan'
        verbose_name_plural = 'Loans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'loan_approved']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"Loan {self.loan_id} - {self.customer.full_name}"
    
    @property
    def repayments_left(self):
        """Calculate number of repayments left."""
        return max(0, self.tenure - self.emis_paid_on_time)
    
    @property
    def is_active(self):
        """Check if loan is currently active."""
        today = timezone.now().date()
        return (
            self.loan_approved and
            self.start_date <= today <= self.end_date and
            self.repayments_left > 0
        )
    
    @property
    def payment_completion_rate(self):
        """Calculate payment completion rate as percentage."""
        if self.tenure == 0:
            return 0
        return (self.emis_paid_on_time / self.tenure) * 100
    
    def calculate_monthly_installment(self):
        """
        Calculate monthly installment using compound interest formula.
        
        Formula: EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        Where:
        - P = Principal amount (loan_amount)
        - r = Monthly interest rate (annual_rate / 12 / 100)
        - n = Number of months (tenure)
        """
        principal = float(self.loan_amount)
        annual_rate = float(self.interest_rate)
        months = self.tenure
        
        # Convert annual rate to monthly decimal rate
        monthly_rate = annual_rate / 12 / 100
        
        if monthly_rate == 0:  # Handle 0% interest rate
            return Decimal(str(principal / months))
        
        # Calculate EMI using compound interest formula
        emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        
        return Decimal(str(round(emi, 2)))
    
    def save(self, *args, **kwargs):
        """
        Override save method to automatically calculate monthly installment
        and update customer's current debt.
        """
        # Calculate monthly installment if not set
        if not self.monthly_repayment:
            self.monthly_repayment = self.calculate_monthly_installment()
        
        # Set end date based on start date and tenure
        if self.start_date and self.tenure:
            from dateutil.relativedelta import relativedelta
            self.end_date = self.start_date + relativedelta(months=self.tenure)
        
        super().save(*args, **kwargs)
        
        # Update customer's current debt after saving
        self.customer.update_current_debt()


class CreditScore(models.Model):
    """
    Model to store calculated credit scores for customers.
    
    This model caches credit score calculations to avoid
    recalculating them on every request.
    """
    
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='credit_score',
        help_text="Customer for whom the score is calculated"
    )
    
    # Score Components
    score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Overall credit score (0-100)"
    )
    past_loans_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Score component for past loan performance"
    )
    loan_volume_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Score component for loan volume"
    )
    current_year_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Score component for current year activity"
    )
    credit_utilization_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Score component for credit utilization"
    )
    
    # Metadata
    calculated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the score was last calculated"
    )
    
    class Meta:
        db_table = 'credit_scores'
        verbose_name = 'Credit Score'
        verbose_name_plural = 'Credit Scores'
    
    def __str__(self):
        return f"Credit Score {self.score} - {self.customer.full_name}"
    
    @property
    def score_grade(self):
        """Return score grade based on score value."""
        if self.score >= 50:
            return 'Excellent'
        elif self.score >= 30:
            return 'Good'
        elif self.score >= 10:
            return 'Fair'
        else:
            return 'Poor'