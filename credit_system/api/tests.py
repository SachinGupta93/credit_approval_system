"""
Test suite for the credit approval system API.

This module contains comprehensive tests for all API endpoints:
- Customer registration
- Loan eligibility checking
- Loan creation
- Loan viewing
- Credit scoring functionality

Tests include both positive and negative scenarios with proper
data validation and error handling verification.
"""

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
import json

from credit_system.core.models import Customer, Loan, CreditScore
from credit_system.api.credit_scoring import CreditScoreCalculator, LoanEligibilityEvaluator


class CustomerRegistrationAPITest(APITestCase):
    """
    Test cases for customer registration endpoint.
    
    Tests the /register endpoint with various scenarios including:
    - Valid customer registration
    - Invalid data validation
    - Duplicate phone number handling
    - Approved limit calculation
    """
    
    def test_valid_customer_registration(self):
        """Test successful customer registration with valid data."""
        url = reverse('register_customer')
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': 9876543210
        }
        
        response = self.client.post(url, data, format='json')
        
        # Check response status and format
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)
        self.assertIn('name', response.data)
        self.assertIn('approved_limit', response.data)
        
        # Verify customer was created in database
        customer = Customer.objects.get(phone_number=9876543210)
        self.assertEqual(customer.first_name, 'John')
        self.assertEqual(customer.last_name, 'Doe')
        self.assertEqual(customer.age, 30)
        self.assertEqual(customer.monthly_income, Decimal('50000'))
        
        # Verify approved limit calculation (36 * monthly_income, rounded to nearest lakh)
        expected_limit = round((50000 * 36) / 100000) * 100000
        self.assertEqual(customer.approved_limit, Decimal(str(expected_limit)))
    
    def test_invalid_age_registration(self):
        """Test customer registration with invalid age."""
        url = reverse('register_customer')
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 17,  # Below minimum age
            'monthly_income': 50000,
            'phone_number': 9876543210
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_duplicate_phone_number_registration(self):
        """Test customer registration with duplicate phone number."""
        # Create first customer
        Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            age=25,
            phone_number=9876543210,
            monthly_income=Decimal('40000'),
            approved_limit=Decimal('1440000')
        )
        
        # Try to create second customer with same phone number
        url = reverse('register_customer')
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'age': 30,
            'monthly_income': 50000,
            'phone_number': 9876543210  # Duplicate
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data['details'])
    
    def test_missing_required_fields_registration(self):
        """Test customer registration with missing required fields."""
        url = reverse('register_customer')
        data = {
            'first_name': 'John',
            # Missing last_name, age, monthly_income, phone_number
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)


class LoanEligibilityAPITest(APITestCase):
    """
    Test cases for loan eligibility checking endpoint.
    
    Tests the /check-eligibility endpoint with various credit scenarios.
    """
    
    def setUp(self):
        """Set up test data for loan eligibility tests."""
        # Create test customer
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            age=30,
            phone_number=9876543210,
            monthly_income=Decimal('50000'),
            approved_limit=Decimal('1800000'),
            current_debt=Decimal('0')
        )
        
        # Create some historical loans for credit score calculation
        self.create_test_loans()
    
    def create_test_loans(self):
        """Create test loans for credit scoring."""
        # Create a good payment history loan
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('200000'),
            tenure=12,
            interest_rate=Decimal('10.0'),
            monthly_repayment=Decimal('17540.25'),
            emis_paid_on_time=12,  # All EMIs paid on time
            start_date=timezone.now().date() - timedelta(days=365),
            end_date=timezone.now().date() - timedelta(days=30),
            loan_approved=True
        )
    
    def test_valid_eligibility_check(self):
        """Test loan eligibility check with valid data."""
        url = reverse('check_loan_eligibility')
        data = {
            'customer_id': self.customer.id,
            'loan_amount': 200000,
            'interest_rate': 10.0,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('customer_id', response.data)
        self.assertIn('approval', response.data)
        self.assertIn('interest_rate', response.data)
        self.assertIn('corrected_interest_rate', response.data)
        self.assertIn('tenure', response.data)
        self.assertIn('monthly_installment', response.data)
    
    def test_eligibility_check_nonexistent_customer(self):
        """Test loan eligibility check for non-existent customer."""
        url = reverse('check_loan_eligibility')
        data = {
            'customer_id': 99999,  # Non-existent customer
            'loan_amount': 200000,
            'interest_rate': 10.0,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_eligibility_check_invalid_loan_amount(self):
        """Test loan eligibility check with invalid loan amount."""
        url = reverse('check_loan_eligibility')
        data = {
            'customer_id': self.customer.id,
            'loan_amount': -1000,  # Negative amount
            'interest_rate': 10.0,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)


class LoanCreationAPITest(APITestCase):
    """
    Test cases for loan creation endpoint.
    
    Tests the /create-loan endpoint with various scenarios.
    """
    
    def setUp(self):
        """Set up test data for loan creation tests."""
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            age=30,
            phone_number=9876543210,
            monthly_income=Decimal('50000'),
            approved_limit=Decimal('1800000'),
            current_debt=Decimal('0')
        )
    
    def test_valid_loan_creation(self):
        """Test successful loan creation."""
        url = reverse('create_loan')
        data = {
            'customer_id': self.customer.id,
            'loan_amount': 200000,
            'interest_rate': 12.0,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('loan_id', response.data)
        self.assertIn('customer_id', response.data)
        self.assertIn('loan_approved', response.data)
        self.assertIn('message', response.data)
        self.assertIn('monthly_installment', response.data)
        
        # Verify loan was created in database
        loan = Loan.objects.get(loan_id=response.data['loan_id'])
        self.assertEqual(loan.customer, self.customer)
        self.assertEqual(loan.loan_amount, Decimal('200000'))
    
    def test_loan_creation_nonexistent_customer(self):
        """Test loan creation for non-existent customer."""
        url = reverse('create_loan')
        data = {
            'customer_id': 99999,  # Non-existent customer
            'loan_amount': 200000,
            'interest_rate': 12.0,
            'tenure': 12
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class LoanViewAPITest(APITestCase):
    """
    Test cases for loan viewing endpoints.
    
    Tests both single loan view and customer loans list endpoints.
    """
    
    def setUp(self):
        """Set up test data for loan viewing tests."""
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            age=30,
            phone_number=9876543210,
            monthly_income=Decimal('50000'),
            approved_limit=Decimal('1800000'),
            current_debt=Decimal('0')
        )
        
        self.loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('200000'),
            tenure=12,
            interest_rate=Decimal('12.0'),
            monthly_repayment=Decimal('17540.25'),
            emis_paid_on_time=5,
            start_date=timezone.now().date(),
            loan_approved=True
        )
    
    def test_view_loan_details(self):
        """Test viewing details of a specific loan."""
        url = reverse('view_loan', kwargs={'loan_id': self.loan.loan_id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('loan_id', response.data)
        self.assertIn('customer', response.data)
        self.assertIn('loan_amount', response.data)
        self.assertIn('interest_rate', response.data)
        self.assertIn('monthly_installment', response.data)
        self.assertIn('tenure', response.data)
        
        # Verify customer information is included
        self.assertIn('id', response.data['customer'])
        self.assertIn('first_name', response.data['customer'])
        self.assertIn('last_name', response.data['customer'])
    
    def test_view_nonexistent_loan(self):
        """Test viewing details of a non-existent loan."""
        from uuid import uuid4
        fake_uuid = uuid4()
        url = reverse('view_loan', kwargs={'loan_id': fake_uuid})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_view_customer_loans(self):
        """Test viewing all loans for a customer."""
        # Create additional loan
        Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal('300000'),
            tenure=24,
            interest_rate=Decimal('15.0'),
            monthly_repayment=Decimal('14500.00'),
            emis_paid_on_time=10,
            start_date=timezone.now().date(),
            loan_approved=True
        )
        
        url = reverse('view_customer_loans', kwargs={'customer_id': self.customer.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 2)  # Two loans
        
        # Verify loan data structure
        for loan_data in response.data:
            self.assertIn('loan_id', loan_data)
            self.assertIn('loan_amount', loan_data)
            self.assertIn('interest_rate', loan_data)
            self.assertIn('monthly_installment', loan_data)
            self.assertIn('repayments_left', loan_data)
    
    def test_view_loans_nonexistent_customer(self):
        """Test viewing loans for a non-existent customer."""
        url = reverse('view_customer_loans', kwargs={'customer_id': 99999})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)


class CreditScoringTest(TestCase):
    """
    Test cases for credit scoring functionality.
    
    Tests the credit score calculation algorithm and its components.
    """
    
    def setUp(self):
        """Set up test data for credit scoring tests."""
        self.customer = Customer.objects.create(
            first_name='Test',
            last_name='Customer',
            age=30,
            phone_number=9876543210,
            monthly_income=Decimal('50000'),
            approved_limit=Decimal('1800000'),
            current_debt=Decimal('0')
        )
    
    def test_credit_score_calculation_new_customer(self):
        """Test credit score calculation for a new customer with no loans."""
        calculator = CreditScoreCalculator(self.customer)
        score_data = calculator.calculate_credit_score()
        
        self.assertIn('overall_score', score_data)
        self.assertIn('past_loans_score', score_data)
        self.assertIn('loan_volume_score', score_data)
        self.assertIn('current_year_score', score_data)
        self.assertIn('credit_utilization_score', score_data)
        
        # New customer should have moderate scores
        self.assertGreaterEqual(score_data['overall_score'], 0)
        self.assertLessEqual(score_data['overall_score'], 100)
    
    def test_credit_score_calculation_with_good_history(self):
        """Test credit score calculation for customer with good payment history."""
        # Create loans with good payment history
        for i in range(3):
            Loan.objects.create(
                customer=self.customer,
                loan_amount=Decimal('100000'),
                tenure=12,
                interest_rate=Decimal('10.0'),
                monthly_repayment=Decimal('8792.45'),
                emis_paid_on_time=12,  # All EMIs paid on time
                start_date=timezone.now().date() - timedelta(days=400 + i*100),
                end_date=timezone.now().date() - timedelta(days=35 + i*100),
                loan_approved=True
            )
        
        calculator = CreditScoreCalculator(self.customer)
        score_data = calculator.calculate_credit_score()
        
        # Customer with good history should have higher score
        self.assertGreater(score_data['overall_score'], 50)
        self.assertGreater(score_data['past_loans_score'], 70)
    
    def test_loan_eligibility_evaluation(self):
        """Test loan eligibility evaluation logic."""
        evaluator = LoanEligibilityEvaluator(
            customer=self.customer,
            loan_amount=200000,
            interest_rate=10.0,
            tenure=12
        )
        
        result = evaluator.evaluate_eligibility()
        
        self.assertIn('approved', result)
        self.assertIn('credit_score', result)
        self.assertIn('corrected_interest_rate', result)
        self.assertIn('monthly_installment', result)
        self.assertIn('message', result)
        
        # Verify EMI calculation
        self.assertGreater(result['monthly_installment'], Decimal('0'))
    
    def test_emi_calculation(self):
        """Test EMI calculation accuracy."""
        evaluator = LoanEligibilityEvaluator(
            customer=self.customer,
            loan_amount=100000,
            interest_rate=12.0,
            tenure=12
        )
        
        emi = evaluator._calculate_emi(Decimal('12.0'))
        
        # Verify EMI is reasonable (should be around 8884 for these parameters)
        self.assertGreater(emi, Decimal('8800'))
        self.assertLess(emi, Decimal('8900'))


class APIStatusTest(APITestCase):
    """
    Test cases for API status and health check endpoints.
    """
    
    def test_api_status_endpoint(self):
        """Test API status endpoint."""
        url = reverse('api_status')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('database', response.data)
        self.assertIn('services', response.data)
        
        self.assertEqual(response.data['status'], 'healthy')


class ModelTest(TestCase):
    """
    Test cases for model functionality.
    
    Tests model methods, properties, and business logic.
    """
    
    def test_customer_model_properties(self):
        """Test Customer model properties and methods."""
        customer = Customer.objects.create(
            first_name='John',
            last_name='Doe',
            age=30,
            phone_number=9876543210,
            monthly_income=Decimal('50000'),
            approved_limit=Decimal('1800000'),
            current_debt=Decimal('360000')
        )
        
        # Test full_name property
        self.assertEqual(customer.full_name, 'John Doe')
        
        # Test credit_utilization property
        expected_utilization = (360000 / 1800000) * 100
        self.assertEqual(customer.credit_utilization, expected_utilization)
    
    def test_loan_model_properties(self):
        """Test Loan model properties and methods."""
        customer = Customer.objects.create(
            first_name='Jane',
            last_name='Smith',
            age=25,
            phone_number=9876543211,
            monthly_income=Decimal('40000'),
            approved_limit=Decimal('1440000'),
            current_debt=Decimal('0')
        )
        
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=Decimal('200000'),
            tenure=12,
            interest_rate=Decimal('10.0'),
            emis_paid_on_time=5,
            start_date=timezone.now().date(),
            loan_approved=True
        )
        
        # Test repayments_left property
        self.assertEqual(loan.repayments_left, 7)  # 12 - 5
        
        # Test payment_completion_rate property
        expected_rate = (5 / 12) * 100
        self.assertAlmostEqual(loan.payment_completion_rate, expected_rate, places=2)
        
        # Test is_active property
        self.assertTrue(loan.is_active)
    
    def test_loan_emi_calculation(self):
        """Test automatic EMI calculation in Loan model."""
        customer = Customer.objects.create(
            first_name='Test',
            last_name='User',
            age=28,
            phone_number=9876543212,
            monthly_income=Decimal('60000'),
            approved_limit=Decimal('2160000'),
            current_debt=Decimal('0')
        )
        
        loan = Loan(
            customer=customer,
            loan_amount=Decimal('100000'),
            tenure=12,
            interest_rate=Decimal('12.0'),
            start_date=timezone.now().date(),
            loan_approved=True
        )
        
        # EMI should be calculated automatically
        calculated_emi = loan.calculate_monthly_installment()
        self.assertGreater(calculated_emi, Decimal('0'))
        
        # Save and verify EMI is set
        loan.save()
        self.assertEqual(loan.monthly_repayment, calculated_emi)