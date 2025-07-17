"""
Serializers for the credit approval system API.

This module contains Django REST Framework serializers that handle:
- Data validation for incoming requests
- Data transformation for outgoing responses
- Business logic validation
- Error handling and messaging

Each serializer corresponds to specific API endpoints and provides
proper validation and formatting for the data.
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from credit_system.core.models import Customer, Loan, CreditScore


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for customer registration endpoint.
    
    Validates customer data and automatically calculates approved_limit
    based on monthly income (36 * monthly_income, rounded to nearest lakh).
    """
    
    # Custom field for monthly_income to handle the input name
    monthly_income = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text="Customer's monthly income"
    )
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'age', 'phone_number', 'monthly_income'
        ]
        
    def validate_age(self, value):
        """Validate customer age is at least 18."""
        if value < 18:
            raise serializers.ValidationError("Customer must be at least 18 years old.")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format and uniqueness."""
        if len(str(value)) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        
        # Check if phone number already exists
        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Customer with this phone number already exists.")
        
        return value
    
    def validate_monthly_income(self, value):
        """Validate monthly income is positive."""
        if value <= 0:
            raise serializers.ValidationError("Monthly income must be positive.")
        return value
    
    def create(self, validated_data):
        """
        Create customer with automatically calculated approved_limit.
        
        Formula: approved_limit = 36 * monthly_income (rounded to nearest lakh)
        """
        monthly_income = validated_data['monthly_income']
        
        # Calculate approved limit (36 * monthly_income, rounded to nearest lakh)
        approved_limit = monthly_income * 36
        # Round to nearest lakh (100,000)
        approved_limit = round(approved_limit / 100000) * 100000
        
        validated_data['approved_limit'] = approved_limit
        return super().create(validated_data)


class CustomerRegistrationResponseSerializer(serializers.ModelSerializer):
    """
    Response serializer for customer registration.
    
    Returns formatted customer data after successful registration.
    """
    
    customer_id = serializers.IntegerField(source='id')
    name = serializers.CharField(source='full_name')
    
    class Meta:
        model = Customer
        fields = [
            'customer_id', 'name', 'age', 'monthly_income', 
            'approved_limit', 'phone_number'
        ]


class LoanEligibilityRequestSerializer(serializers.Serializer):
    """
    Serializer for loan eligibility check request.
    
    Validates loan eligibility request parameters and ensures
    all required fields are present and valid.
    """
    
    customer_id = serializers.IntegerField(
        min_value=1,
        help_text="ID of the customer applying for loan"
    )
    loan_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('1000.00'),
        help_text="Requested loan amount"
    )
    interest_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal('0.01'),
        max_value=Decimal('50.00'),
        help_text="Requested annual interest rate"
    )
    tenure = serializers.IntegerField(
        min_value=1,
        max_value=120,
        help_text="Loan tenure in months"
    )
    
    def validate_customer_id(self, value):
        """Validate customer exists."""
        try:
            Customer.objects.get(id=value)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer not found.")
        return value


class LoanEligibilityResponseSerializer(serializers.Serializer):
    """
    Serializer for loan eligibility check response.
    
    Returns loan eligibility result with approval status,
    corrected interest rate, and monthly installment.
    """
    
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2)
    message = serializers.CharField(required=False)


class LoanCreationRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for loan creation request.
    
    Validates loan creation parameters and ensures eligibility
    has been checked before creating the loan.
    """
    
    customer_id = serializers.IntegerField(
        min_value=1,
        help_text="ID of the customer applying for loan"
    )
    
    class Meta:
        model = Loan
        fields = ['customer_id', 'loan_amount', 'interest_rate', 'tenure']
        
    def validate_customer_id(self, value):
        """Validate customer exists."""
        try:
            self.customer = Customer.objects.get(id=value)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer not found.")
        return value
    
    def validate_loan_amount(self, value):
        """Validate loan amount is positive and reasonable."""
        if value <= 0:
            raise serializers.ValidationError("Loan amount must be positive.")
        return value
    
    def validate_interest_rate(self, value):
        """Validate interest rate is within reasonable range."""
        if value <= 0 or value > 50:
            raise serializers.ValidationError("Interest rate must be between 0.01% and 50%.")
        return value
    
    def validate_tenure(self, value):
        """Validate tenure is within acceptable range."""
        if value < 1 or value > 120:
            raise serializers.ValidationError("Tenure must be between 1 and 120 months.")
        return value


class LoanCreationResponseSerializer(serializers.Serializer):
    """
    Serializer for loan creation response.
    
    Returns loan creation result with loan ID and approval status.
    """
    
    loan_id = serializers.UUIDField()
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.DecimalField(max_digits=12, decimal_places=2)


class LoanDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for loan details view.
    
    Returns comprehensive loan information including customer details.
    """
    
    loan_id = serializers.UUIDField()
    customer = CustomerRegistrationResponseSerializer(read_only=True)
    
    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer', 'loan_amount', 'interest_rate',
            'monthly_repayment', 'tenure'
        ]
        
    def to_representation(self, instance):
        """
        Convert loan instance to dictionary representation.
        
        Customizes the output format to match API requirements.
        """
        data = super().to_representation(instance)
        
        # Rename monthly_repayment to monthly_installment for consistency
        data['monthly_installment'] = data.pop('monthly_repayment')
        
        # Format customer data
        customer_data = data['customer']
        data['customer'] = {
            'id': customer_data['customer_id'],
            'first_name': instance.customer.first_name,
            'last_name': instance.customer.last_name,
            'phone_number': customer_data['phone_number'],
            'age': customer_data['age']
        }
        
        return data


class CustomerLoansSerializer(serializers.ModelSerializer):
    """
    Serializer for customer loans list view.
    
    Returns simplified loan information for a customer's loan history.
    """
    
    loan_id = serializers.UUIDField()
    repayments_left = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Loan
        fields = [
            'loan_id', 'loan_amount', 'interest_rate',
            'monthly_repayment', 'repayments_left'
        ]
        
    def to_representation(self, instance):
        """
        Convert loan instance to dictionary representation.
        
        Customizes the output format for customer loans list.
        """
        data = super().to_representation(instance)
        
        # Rename monthly_repayment to monthly_installment for consistency
        data['monthly_installment'] = data.pop('monthly_repayment')
        
        return data


class CreditScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for credit score information.
    
    Used internally for credit score calculations and responses.
    """
    
    class Meta:
        model = CreditScore
        fields = [
            'score', 'past_loans_score', 'loan_volume_score',
            'current_year_score', 'credit_utilization_score',
            'calculated_at'
        ]
        
    def to_representation(self, instance):
        """Add score grade to representation."""
        data = super().to_representation(instance)
        data['score_grade'] = instance.score_grade
        return data


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response serializer.
    
    Provides consistent error response format across all endpoints.
    """
    
    error = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)
    
    
class SuccessResponseSerializer(serializers.Serializer):
    """
    Standard success response serializer.
    
    Provides consistent success response format across all endpoints.
    """
    
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = serializers.DictField(required=False)