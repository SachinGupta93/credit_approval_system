"""
API views for the credit approval system.

This module contains all the REST API endpoints:
1. /register - Register new customer
2. /check-eligibility - Check loan eligibility
3. /create-loan - Create new loan
4. /view-loan/{loan_id} - View loan details
5. /view-loans/{customer_id} - View customer loans

Each endpoint includes proper validation, error handling, and response formatting.
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import logging

from credit_system.core.models import Customer, Loan, CreditScore
from credit_system.api.serializers import (
    CustomerRegistrationSerializer,
    CustomerRegistrationResponseSerializer,
    LoanEligibilityRequestSerializer,
    LoanEligibilityResponseSerializer,
    LoanCreationRequestSerializer,
    LoanCreationResponseSerializer,
    LoanDetailsSerializer,
    CustomerLoansSerializer,
    ErrorResponseSerializer
)
from credit_system.api.credit_scoring import LoanEligibilityEvaluator

logger = logging.getLogger(__name__)


@api_view(['POST'])
def register_customer(request):
    """
    Register a new customer.
    
    This endpoint creates a new customer record with automatically calculated
    approved credit limit based on monthly income.
    
    Request Body:
    {
        "first_name": "John",
        "last_name": "Doe",
        "age": 30,
        "monthly_income": 50000,
        "phone_number": 9876543210
    }
    
    Response:
    {
        "customer_id": 1,
        "name": "John Doe",
        "age": 30,
        "monthly_income": 50000,
        "approved_limit": 1800000,
        "phone_number": 9876543210
    }
    """
    try:
        # Validate input data
        serializer = CustomerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Invalid customer registration data: {serializer.errors}")
            return Response(
                {
                    'error': 'Validation failed',
                    'message': 'Invalid input data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create customer
        with transaction.atomic():
            customer = serializer.save()
            logger.info(f"Created new customer: {customer.full_name} (ID: {customer.id})")
        
        # Prepare response
        response_serializer = CustomerRegistrationResponseSerializer(customer)
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.error(f"Error registering customer: {str(e)}")
        return Response(
            {
                'error': 'Internal server error',
                'message': 'Failed to register customer',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def check_loan_eligibility(request):
    """
    Check loan eligibility for a customer.
    
    This endpoint evaluates loan eligibility based on credit score,
    financial criteria, and business rules.
    
    Request Body:
    {
        "customer_id": 1,
        "loan_amount": 200000,
        "interest_rate": 8.5,
        "tenure": 12
    }
    
    Response:
    {
        "customer_id": 1,
        "approval": true,
        "interest_rate": 8.5,
        "corrected_interest_rate": 12.0,
        "tenure": 12,
        "monthly_installment": 17540.25
    }
    """
    try:
        # Validate input data
        serializer = LoanEligibilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Invalid loan eligibility request: {serializer.errors}")
            return Response(
                {
                    'error': 'Validation failed',
                    'message': 'Invalid input data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get customer
        customer_id = serializer.validated_data['customer_id']
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Extract loan parameters
        loan_amount = serializer.validated_data['loan_amount']
        interest_rate = serializer.validated_data['interest_rate']
        tenure = serializer.validated_data['tenure']
        
        # Evaluate loan eligibility
        evaluator = LoanEligibilityEvaluator(customer, loan_amount, interest_rate, tenure)
        eligibility_result = evaluator.evaluate_eligibility()
        
        # Prepare response data
        response_data = {
            'customer_id': customer_id,
            'approval': eligibility_result['approved'],
            'interest_rate': float(interest_rate),
            'corrected_interest_rate': float(eligibility_result['corrected_interest_rate']),
            'tenure': tenure,
            'monthly_installment': float(eligibility_result['monthly_installment']),
        }
        
        # Add message for rejected loans
        if not eligibility_result['approved']:
            response_data['message'] = eligibility_result['message']
        
        logger.info(f"Loan eligibility check for customer {customer_id}: {eligibility_result['approved']}")
        
        # Validate response format
        response_serializer = LoanEligibilityResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
        else:
            logger.error(f"Invalid response format: {response_serializer.errors}")
            return Response(
                response_data,  # Return raw data if serializer fails
                status=status.HTTP_200_OK
            )
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found: {request.data.get('customer_id')}")
        return Response(
            {
                'error': 'Customer not found',
                'message': 'The specified customer does not exist'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error checking loan eligibility: {str(e)}")
        return Response(
            {
                'error': 'Internal server error',
                'message': 'Failed to check loan eligibility',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_loan(request):
    """
    Create a new loan.
    
    This endpoint creates a new loan after performing eligibility checks.
    
    Request Body:
    {
        "customer_id": 1,
        "loan_amount": 200000,
        "interest_rate": 12.0,
        "tenure": 12
    }
    
    Response:
    {
        "loan_id": "uuid-string",
        "customer_id": 1,
        "loan_approved": true,
        "message": "Loan approved successfully",
        "monthly_installment": 17540.25
    }
    """
    try:
        # Validate input data
        serializer = LoanCreationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Invalid loan creation request: {serializer.errors}")
            return Response(
                {
                    'error': 'Validation failed',
                    'message': 'Invalid input data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get customer
        customer_id = serializer.validated_data['customer_id']
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Extract loan parameters
        loan_amount = serializer.validated_data['loan_amount']
        interest_rate = serializer.validated_data['interest_rate']
        tenure = serializer.validated_data['tenure']
        
        # Re-check eligibility before creating loan
        evaluator = LoanEligibilityEvaluator(customer, loan_amount, interest_rate, tenure)
        eligibility_result = evaluator.evaluate_eligibility()
        
        # Create loan record
        with transaction.atomic():
            loan = Loan.objects.create(
                customer=customer,
                loan_amount=loan_amount,
                interest_rate=eligibility_result['corrected_interest_rate'],
                tenure=tenure,
                monthly_repayment=eligibility_result['monthly_installment'],
                loan_approved=eligibility_result['approved'],
                start_date=timezone.now().date(),
                emis_paid_on_time=0
            )
            
            # Update customer's current debt if approved
            if eligibility_result['approved']:
                customer.update_current_debt()
            
            logger.info(f"Created loan {loan.loan_id} for customer {customer_id}: approved={eligibility_result['approved']}")
        
        # Prepare response
        response_data = {
            'loan_id': loan.loan_id,
            'customer_id': customer_id,
            'loan_approved': eligibility_result['approved'],
            'message': eligibility_result['message'],
            'monthly_installment': float(eligibility_result['monthly_installment'])
        }
        
        # Validate response format
        response_serializer = LoanCreationResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        else:
            logger.error(f"Invalid response format: {response_serializer.errors}")
            return Response(
                response_data,  # Return raw data if serializer fails
                status=status.HTTP_201_CREATED
            )
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found: {request.data.get('customer_id')}")
        return Response(
            {
                'error': 'Customer not found',
                'message': 'The specified customer does not exist'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error creating loan: {str(e)}")
        return Response(
            {
                'error': 'Internal server error',
                'message': 'Failed to create loan',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def view_loan(request, loan_id):
    """
    View details of a specific loan.
    
    This endpoint returns comprehensive loan information including customer details.
    
    URL: /view-loan/{loan_id}
    
    Response:
    {
        "loan_id": "uuid-string",
        "customer": {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": 9876543210,
            "age": 30
        },
        "loan_amount": 200000,
        "interest_rate": 12.0,
        "monthly_installment": 17540.25,
        "tenure": 12
    }
    """
    try:
        # Get loan by ID
        loan = get_object_or_404(Loan, loan_id=loan_id)
        
        # Serialize loan data
        serializer = LoanDetailsSerializer(loan)
        
        logger.info(f"Retrieved loan details for loan {loan_id}")
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
    except Loan.DoesNotExist:
        logger.warning(f"Loan not found: {loan_id}")
        return Response(
            {
                'error': 'Loan not found',
                'message': 'The specified loan does not exist'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error retrieving loan {loan_id}: {str(e)}")
        return Response(
            {
                'error': 'Internal server error',
                'message': 'Failed to retrieve loan details',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def view_customer_loans(request, customer_id):
    """
    View all loans for a specific customer.
    
    This endpoint returns a list of all loans for a customer.
    
    URL: /view-loans/{customer_id}
    
    Response:
    [
        {
            "loan_id": "uuid-string",
            "loan_amount": 200000,
            "interest_rate": 12.0,
            "monthly_installment": 17540.25,
            "repayments_left": 8
        }
    ]
    """
    try:
        # Get customer
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Get all loans for customer
        loans = Loan.objects.filter(customer=customer, loan_approved=True)
        
        # Serialize loans data
        serializer = CustomerLoansSerializer(loans, many=True)
        
        logger.info(f"Retrieved {loans.count()} loans for customer {customer_id}")
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found: {customer_id}")
        return Response(
            {
                'error': 'Customer not found',
                'message': 'The specified customer does not exist'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error retrieving customer loans for {customer_id}: {str(e)}")
        return Response(
            {
                'error': 'Internal server error',
                'message': 'Failed to retrieve customer loans',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def api_status(request):
    """
    API status endpoint.
    
    This endpoint provides basic API health and status information.
    
    Response:
    {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "database": "connected",
        "services": {
            "customers": 150,
            "loans": 450,
            "credit_scores": 120
        }
    }
    """
    try:
        # Get database statistics
        customer_count = Customer.objects.count()
        loan_count = Loan.objects.count()
        credit_score_count = CreditScore.objects.count()
        
        # Test database connection
        try:
            Customer.objects.first()
            db_status = "connected"
        except Exception:
            db_status = "disconnected"
        
        response_data = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0',
            'database': db_status,
            'services': {
                'customers': customer_count,
                'loans': loan_count,
                'credit_scores': credit_score_count
            }
        }
        
        return Response(
            response_data,
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Error getting API status: {str(e)}")
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def customer_credit_score(request, customer_id):
    """
    Get credit score for a customer (bonus endpoint).
    
    This endpoint returns the current credit score and its components.
    
    URL: /customer/{customer_id}/credit-score
    
    Response:
    {
        "customer_id": 1,
        "credit_score": 75,
        "score_grade": "Excellent",
        "components": {
            "past_loans_score": 80.5,
            "loan_volume_score": 70.2,
            "current_year_score": 75.0,
            "credit_utilization_score": 85.3
        },
        "calculated_at": "2024-01-01T00:00:00Z"
    }
    """
    try:
        # Get customer
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Get or calculate credit score
        try:
            credit_score = CreditScore.objects.get(customer=customer)
        except CreditScore.DoesNotExist:
            # Calculate new score if not exists
            from credit_system.api.credit_scoring import CreditScoreCalculator
            calculator = CreditScoreCalculator(customer)
            score_data = calculator.calculate_credit_score()
            credit_score = calculator.save_credit_score(score_data)
        
        # Prepare response
        response_data = {
            'customer_id': customer_id,
            'credit_score': credit_score.score,
            'score_grade': credit_score.score_grade,
            'components': {
                'past_loans_score': float(credit_score.past_loans_score),
                'loan_volume_score': float(credit_score.loan_volume_score),
                'current_year_score': float(credit_score.current_year_score),
                'credit_utilization_score': float(credit_score.credit_utilization_score)
            },
            'calculated_at': credit_score.calculated_at.isoformat()
        }
        
        logger.info(f"Retrieved credit score for customer {customer_id}: {credit_score.score}")
        
        return Response(
            response_data,
            status=status.HTTP_200_OK
        )
        
    except Customer.DoesNotExist:
        logger.warning(f"Customer not found: {customer_id}")
        return Response(
            {
                'error': 'Customer not found',
                'message': 'The specified customer does not exist'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error retrieving credit score for customer {customer_id}: {str(e)}")
        return Response(
            {
                'error': 'Internal server error',
                'message': 'Failed to retrieve credit score',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )