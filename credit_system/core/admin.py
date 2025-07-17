"""
Admin interface configuration for core models.

This module configures the Django admin interface for managing
customers, loans, and credit scores. It provides an easy way to
view and manage data through the web interface.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from .models import Customer, Loan, CreditScore


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for Customer model.
    
    Provides comprehensive view of customer data including:
    - Personal and financial information
    - Credit utilization and debt status
    - Associated loans count
    """
    
    list_display = [
        'id', 'full_name', 'age', 'phone_number',
        'monthly_income', 'approved_limit', 'current_debt',
        'credit_utilization_display', 'loans_count', 'created_at'
    ]
    
    list_filter = [
        'age', 'created_at', 'updated_at'
    ]
    
    search_fields = [
        'first_name', 'last_name', 'phone_number'
    ]
    
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'credit_utilization_display'
    ]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'age', 'phone_number')
        }),
        ('Financial Information', {
            'fields': ('monthly_income', 'approved_limit', 'current_debt', 'credit_utilization_display')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def credit_utilization_display(self, obj):
        """Display credit utilization with color coding."""
        utilization = obj.credit_utilization
        if utilization >= 80:
            color = 'red'
        elif utilization >= 60:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {}">{:.2f}%</span>',
            color, utilization
        )
    credit_utilization_display.short_description = 'Credit Utilization'
    
    def loans_count(self, obj):
        """Display count of loans for this customer."""
        return obj.loans.count()
    loans_count.short_description = 'Loans Count'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch_related."""
        return super().get_queryset(request).prefetch_related('loans')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    """
    Admin interface for Loan model.
    
    Provides comprehensive view of loan data including:
    - Loan details and payment information
    - Customer information
    - Loan status and approval details
    """
    
    list_display = [
        'loan_id', 'customer_name', 'loan_amount', 'interest_rate',
        'tenure', 'monthly_repayment', 'loan_approved_display',
        'repayments_left', 'start_date', 'end_date'
    ]
    
    list_filter = [
        'loan_approved', 'start_date', 'end_date', 'created_at'
    ]
    
    search_fields = [
        'loan_id', 'customer__first_name', 'customer__last_name',
        'customer__phone_number'
    ]
    
    readonly_fields = [
        'loan_id', 'monthly_repayment', 'repayments_left',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Loan Information', {
            'fields': ('loan_id', 'customer', 'loan_amount', 'tenure', 'interest_rate')
        }),
        ('Payment Details', {
            'fields': ('monthly_repayment', 'emis_paid_on_time', 'repayments_left')
        }),
        ('Loan Status', {
            'fields': ('loan_approved', 'start_date', 'end_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def customer_name(self, obj):
        """Display customer name with link."""
        return format_html(
            '<a href="/admin/core/customer/{}/change/">{}</a>',
            obj.customer.id, obj.customer.full_name
        )
    customer_name.short_description = 'Customer'
    
    def loan_approved_display(self, obj):
        """Display loan approval status with color coding."""
        if obj.loan_approved:
            return format_html(
                '<span style="color: green;">✓ Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Not Approved</span>'
            )
    loan_approved_display.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('customer')


@admin.register(CreditScore)
class CreditScoreAdmin(admin.ModelAdmin):
    """
    Admin interface for CreditScore model.
    
    Provides view of credit score calculations and components.
    """
    
    list_display = [
        'customer_name', 'score', 'score_grade_display',
        'past_loans_score', 'loan_volume_score',
        'current_year_score', 'credit_utilization_score',
        'calculated_at'
    ]
    
    list_filter = [
        'score', 'calculated_at'
    ]
    
    search_fields = [
        'customer__first_name', 'customer__last_name',
        'customer__phone_number'
    ]
    
    readonly_fields = [
        'customer', 'score', 'past_loans_score', 'loan_volume_score',
        'current_year_score', 'credit_utilization_score', 'calculated_at'
    ]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Credit Score', {
            'fields': ('score', 'score_grade_display')
        }),
        ('Score Components', {
            'fields': (
                'past_loans_score', 'loan_volume_score',
                'current_year_score', 'credit_utilization_score'
            )
        }),
        ('Metadata', {
            'fields': ('calculated_at',)
        })
    )
    
    def customer_name(self, obj):
        """Display customer name with link."""
        return format_html(
            '<a href="/admin/core/customer/{}/change/">{}</a>',
            obj.customer.id, obj.customer.full_name
        )
    customer_name.short_description = 'Customer'
    
    def score_grade_display(self, obj):
        """Display score grade with color coding."""
        grade = obj.score_grade
        colors = {
            'Excellent': 'green',
            'Good': 'blue',
            'Fair': 'orange',
            'Poor': 'red'
        }
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(grade, 'black'), grade
        )
    score_grade_display.short_description = 'Grade'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('customer')


# Custom admin site configuration
admin.site.site_header = 'Credit Approval System Administration'
admin.site.site_title = 'Credit Approval Admin'
admin.site.index_title = 'Welcome to Credit Approval System Administration'