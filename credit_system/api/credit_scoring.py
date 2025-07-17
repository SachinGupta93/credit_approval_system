"""
Credit scoring system for loan eligibility evaluation.

This module contains the core business logic for calculating credit scores
and determining loan eligibility based on various factors:

1. Past loan performance (40% weight)
2. Loan volume (25% weight)
3. Current year activity (20% weight)
4. Credit utilization (15% weight)

The scoring algorithm evaluates these factors and returns a score between 0-100.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.conf import settings
from credit_system.core.models import Customer, Loan, CreditScore


class CreditScoreCalculator:
    """
    Main class for calculating credit scores.
    
    This class implements the credit scoring algorithm based on:
    - Historical loan performance
    - Loan volume and frequency
    - Recent activity patterns
    - Credit utilization ratios
    """
    
    def __init__(self, customer):
        """
        Initialize calculator for a specific customer.
        
        Args:
            customer: Customer instance to calculate score for
        """
        self.customer = customer
        self.weights = settings.CREDIT_SCORE_WEIGHTS
        self.current_year = timezone.now().year
        
    def calculate_credit_score(self):
        """
        Calculate overall credit score for the customer.
        
        Returns:
            dict: Contains overall score and component scores
        """
        # Get all loans for the customer
        loans = Loan.objects.filter(customer=self.customer)
        
        # Calculate individual components
        past_loans_score = self._calculate_past_loans_performance(loans)
        loan_volume_score = self._calculate_loan_volume_score(loans)
        current_year_score = self._calculate_current_year_activity(loans)
        credit_utilization_score = self._calculate_credit_utilization_score()
        
        # Calculate weighted overall score
        overall_score = (
            past_loans_score * self.weights['PAST_LOANS_PERFORMANCE'] +
            loan_volume_score * self.weights['LOAN_VOLUME'] +
            current_year_score * self.weights['CURRENT_YEAR_ACTIVITY'] +
            credit_utilization_score * self.weights['CREDIT_UTILIZATION']
        )
        
        # Ensure score is within 0-100 range
        overall_score = max(0, min(100, int(overall_score)))
        
        return {
            'overall_score': overall_score,
            'past_loans_score': float(past_loans_score),
            'loan_volume_score': float(loan_volume_score),
            'current_year_score': float(current_year_score),
            'credit_utilization_score': float(credit_utilization_score)
        }
    
    def _calculate_past_loans_performance(self, loans):
        """
        Calculate score based on past loan payment performance.
        
        Factors considered:
        - Number of loans paid on time
        - Payment completion percentage
        - Recent payment behavior
        
        Args:
            loans: QuerySet of customer's loans
            
        Returns:
            float: Score component (0-100)
        """
        if not loans.exists():
            return 50.0  # Neutral score for new customers
        
        # Get completed loans only
        completed_loans = loans.filter(
            Q(emis_paid_on_time__gte=models.F('tenure')) |
            Q(end_date__lt=timezone.now().date())
        )
        
        if not completed_loans.exists():
            # For ongoing loans, check payment ratio
            ongoing_loans = loans.filter(loan_approved=True)
            if ongoing_loans.exists():
                avg_payment_ratio = ongoing_loans.aggregate(
                    avg_ratio=Avg(
                        models.F('emis_paid_on_time') * 100.0 / models.F('tenure')
                    )
                )['avg_ratio'] or 0
                return min(100, max(0, avg_payment_ratio))
            return 50.0
        
        # Calculate performance metrics
        total_loans = completed_loans.count()
        good_loans = completed_loans.filter(
            emis_paid_on_time__gte=models.F('tenure') * 0.8  # 80% payment threshold
        ).count()
        
        # Calculate percentage of good loans
        good_loan_percentage = (good_loans / total_loans) * 100
        
        # Bonus for excellent payment history
        excellent_loans = completed_loans.filter(
            emis_paid_on_time=models.F('tenure')  # 100% payment
        ).count()
        
        excellence_bonus = (excellent_loans / total_loans) * 20
        
        # Recent payment behavior (last 2 years)
        recent_cutoff = timezone.now().date() - timedelta(days=730)
        recent_loans = completed_loans.filter(start_date__gte=recent_cutoff)
        
        recent_performance = 0
        if recent_loans.exists():
            recent_good = recent_loans.filter(
                emis_paid_on_time__gte=models.F('tenure') * 0.8
            ).count()
            recent_performance = (recent_good / recent_loans.count()) * 100
        
        # Weighted final score
        final_score = (
            good_loan_percentage * 0.6 +
            excellence_bonus * 0.2 +
            recent_performance * 0.2
        )
        
        return min(100, max(0, final_score))
    
    def _calculate_loan_volume_score(self, loans):
        """
        Calculate score based on loan volume and frequency.
        
        Factors considered:
        - Total number of loans
        - Total approved amount
        - Loan frequency over time
        
        Args:
            loans: QuerySet of customer's loans
            
        Returns:
            float: Score component (0-100)
        """
        approved_loans = loans.filter(loan_approved=True)
        
        if not approved_loans.exists():
            return 0.0
        
        # Number of loans factor
        loan_count = approved_loans.count()
        count_score = min(100, loan_count * 10)  # 10 points per loan, max 100
        
        # Total amount factor
        total_amount = approved_loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')
        
        # Normalize amount score based on customer's approved limit
        if self.customer.approved_limit > 0:
            amount_ratio = float(total_amount) / float(self.customer.approved_limit)
            amount_score = min(100, amount_ratio * 50)  # Scale to 0-100
        else:
            amount_score = 0
        
        # Loan frequency factor (consistent borrowing is good)
        customer_age_years = (
            timezone.now().date() - self.customer.created_at.date()
        ).days / 365.25
        
        if customer_age_years > 0:
            frequency_score = min(100, (loan_count / customer_age_years) * 25)
        else:
            frequency_score = 0
        
        # Weighted final score
        final_score = (
            count_score * 0.5 +
            amount_score * 0.3 +
            frequency_score * 0.2
        )
        
        return min(100, max(0, final_score))
    
    def _calculate_current_year_activity(self, loans):
        """
        Calculate score based on current year loan activity.
        
        Factors considered:
        - Number of loans in current year
        - Payment behavior in current year
        - Recent loan approval rate
        
        Args:
            loans: QuerySet of customer's loans
            
        Returns:
            float: Score component (0-100)
        """
        current_year_start = datetime(self.current_year, 1, 1).date()
        current_year_loans = loans.filter(start_date__gte=current_year_start)
        
        if not current_year_loans.exists():
            return 30.0  # Neutral score for no current year activity
        
        # Current year loan count
        current_count = current_year_loans.count()
        count_score = min(100, current_count * 25)  # 25 points per loan
        
        # Current year approval rate
        approved_current = current_year_loans.filter(loan_approved=True).count()
        if current_count > 0:
            approval_rate = (approved_current / current_count) * 100
        else:
            approval_rate = 0
        
        # Payment performance in current year
        performance_score = 0
        approved_current_loans = current_year_loans.filter(loan_approved=True)
        if approved_current_loans.exists():
            avg_payment_ratio = approved_current_loans.aggregate(
                avg_ratio=Avg(
                    models.F('emis_paid_on_time') * 100.0 / models.F('tenure')
                )
            )['avg_ratio'] or 0
            performance_score = min(100, avg_payment_ratio)
        
        # Weighted final score
        final_score = (
            count_score * 0.4 +
            approval_rate * 0.3 +
            performance_score * 0.3
        )
        
        return min(100, max(0, final_score))
    
    def _calculate_credit_utilization_score(self):
        """
        Calculate score based on credit utilization.
        
        Factors considered:
        - Current debt vs approved limit
        - Debt-to-income ratio
        - Available credit
        
        Returns:
            float: Score component (0-100)
        """
        if self.customer.approved_limit <= 0:
            return 0.0
        
        # Current utilization ratio
        utilization_ratio = float(self.customer.current_debt) / float(self.customer.approved_limit)
        
        # Score inversely proportional to utilization
        if utilization_ratio >= 1.0:
            utilization_score = 0  # Over limit
        elif utilization_ratio >= 0.8:
            utilization_score = 20  # Very high utilization
        elif utilization_ratio >= 0.6:
            utilization_score = 40  # High utilization
        elif utilization_ratio >= 0.4:
            utilization_score = 60  # Moderate utilization
        elif utilization_ratio >= 0.2:
            utilization_score = 80  # Low utilization
        else:
            utilization_score = 100  # Very low utilization
        
        # Debt-to-income ratio
        monthly_debt_payment = 0
        active_loans = Loan.objects.filter(
            customer=self.customer,
            loan_approved=True
        ).filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        )
        
        if active_loans.exists():
            monthly_debt_payment = active_loans.aggregate(
                total=Sum('monthly_repayment')
            )['total'] or Decimal('0')
        
        if self.customer.monthly_income > 0:
            debt_to_income_ratio = float(monthly_debt_payment) / float(self.customer.monthly_income)
            
            if debt_to_income_ratio >= 0.5:
                income_score = 0  # Too high debt
            elif debt_to_income_ratio >= 0.4:
                income_score = 20
            elif debt_to_income_ratio >= 0.3:
                income_score = 40
            elif debt_to_income_ratio >= 0.2:
                income_score = 60
            elif debt_to_income_ratio >= 0.1:
                income_score = 80
            else:
                income_score = 100
        else:
            income_score = 0
        
        # Available credit score
        available_credit = float(self.customer.approved_limit) - float(self.customer.current_debt)
        if available_credit > 0:
            availability_score = min(100, (available_credit / float(self.customer.approved_limit)) * 100)
        else:
            availability_score = 0
        
        # Weighted final score
        final_score = (
            utilization_score * 0.5 +
            income_score * 0.3 +
            availability_score * 0.2
        )
        
        return min(100, max(0, final_score))
    
    def save_credit_score(self, score_data):
        """
        Save or update credit score in database.
        
        Args:
            score_data: Dictionary containing score components
        """
        credit_score, created = CreditScore.objects.update_or_create(
            customer=self.customer,
            defaults={
                'score': score_data['overall_score'],
                'past_loans_score': Decimal(str(score_data['past_loans_score'])),
                'loan_volume_score': Decimal(str(score_data['loan_volume_score'])),
                'current_year_score': Decimal(str(score_data['current_year_score'])),
                'credit_utilization_score': Decimal(str(score_data['credit_utilization_score'])),
            }
        )
        return credit_score


class LoanEligibilityEvaluator:
    """
    Class for evaluating loan eligibility based on credit score and business rules.
    
    This class implements the loan approval logic based on:
    - Credit score thresholds
    - EMI to salary ratio limits
    - Credit limit restrictions
    """
    
    def __init__(self, customer, loan_amount, interest_rate, tenure):
        """
        Initialize evaluator for a specific loan request.
        
        Args:
            customer: Customer instance
            loan_amount: Requested loan amount
            interest_rate: Requested interest rate
            tenure: Loan tenure in months
        """
        self.customer = customer
        self.loan_amount = Decimal(str(loan_amount))
        self.interest_rate = Decimal(str(interest_rate))
        self.tenure = int(tenure)
        self.approval_rules = settings.LOAN_APPROVAL_RULES
        
    def evaluate_eligibility(self):
        """
        Evaluate loan eligibility and return decision.
        
        Returns:
            dict: Contains approval decision, corrected interest rate, and EMI
        """
        # Step 1: Calculate credit score
        calculator = CreditScoreCalculator(self.customer)
        score_data = calculator.calculate_credit_score()
        credit_score = score_data['overall_score']
        
        # Save credit score
        calculator.save_credit_score(score_data)
        
        # Step 2: Check credit limit
        if self.customer.current_debt > self.customer.approved_limit:
            return {
                'approved': False,
                'credit_score': 0,  # Override score to 0 for over-limit
                'corrected_interest_rate': self.interest_rate,
                'monthly_installment': Decimal('0'),
                'message': 'Loan rejected: Current debt exceeds approved limit'
            }
        
        # Step 3: Apply credit score based approval rules
        approval_decision = self._get_approval_decision(credit_score)
        
        if not approval_decision['approved']:
            return {
                'approved': False,
                'credit_score': credit_score,
                'corrected_interest_rate': self.interest_rate,
                'monthly_installment': Decimal('0'),
                'message': f'Loan rejected: Credit score {credit_score} is below minimum threshold'
            }
        
        # Step 4: Calculate EMI with corrected interest rate
        corrected_rate = approval_decision['interest_rate']
        monthly_installment = self._calculate_emi(corrected_rate)
        
        # Step 5: Check EMI to salary ratio
        emi_check = self._check_emi_to_salary_ratio(monthly_installment)
        
        if not emi_check['approved']:
            return {
                'approved': False,
                'credit_score': credit_score,
                'corrected_interest_rate': corrected_rate,
                'monthly_installment': monthly_installment,
                'message': emi_check['message']
            }
        
        # Step 6: Final approval
        return {
            'approved': True,
            'credit_score': credit_score,
            'corrected_interest_rate': corrected_rate,
            'monthly_installment': monthly_installment,
            'message': 'Loan approved successfully'
        }
    
    def _get_approval_decision(self, credit_score):
        """
        Get approval decision based on credit score.
        
        Args:
            credit_score: Customer's credit score
            
        Returns:
            dict: Approval decision with interest rate
        """
        # Check each approval rule
        for rule_name, rule in self.approval_rules.items():
            if rule['min_score'] <= credit_score <= rule['max_score']:
                if rule['interest_rate'] is None:
                    # Use requested rate (excellent credit)
                    return {
                        'approved': True,
                        'interest_rate': self.interest_rate,
                        'rule': rule_name
                    }
                else:
                    # Use minimum required rate
                    corrected_rate = max(self.interest_rate, Decimal(str(rule['interest_rate'])))
                    return {
                        'approved': True,
                        'interest_rate': corrected_rate,
                        'rule': rule_name
                    }
        
        # If no rule matches, reject
        return {
            'approved': False,
            'interest_rate': self.interest_rate,
            'rule': 'REJECTED'
        }
    
    def _calculate_emi(self, interest_rate):
        """
        Calculate monthly EMI using compound interest formula.
        
        Formula: EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
        
        Args:
            interest_rate: Annual interest rate
            
        Returns:
            Decimal: Monthly EMI amount
        """
        principal = float(self.loan_amount)
        annual_rate = float(interest_rate)
        months = self.tenure
        
        # Convert annual rate to monthly decimal rate
        monthly_rate = annual_rate / 12 / 100
        
        if monthly_rate == 0:  # Handle 0% interest rate
            return Decimal(str(principal / months))
        
        # Calculate EMI using compound interest formula
        emi = principal * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        
        return Decimal(str(round(emi, 2)))
    
    def _check_emi_to_salary_ratio(self, monthly_installment):
        """
        Check if EMI exceeds maximum allowed percentage of salary.
        
        Args:
            monthly_installment: Calculated EMI amount
            
        Returns:
            dict: Approval decision for EMI check
        """
        max_emi_ratio = settings.MAX_EMI_TO_SALARY_RATIO
        max_allowed_emi = self.customer.monthly_income * Decimal(str(max_emi_ratio))
        
        if monthly_installment > max_allowed_emi:
            return {
                'approved': False,
                'message': f'Loan rejected: EMI ({monthly_installment}) exceeds {max_emi_ratio*100}% of monthly income'
            }
        
        return {
            'approved': True,
            'message': 'EMI within acceptable range'
        }


# Import fix for models reference
from django.db import models