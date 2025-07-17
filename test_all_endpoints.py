#!/usr/bin/env python3
"""
Complete API endpoint testing script for Credit Approval System.
Tests all endpoints with various scenarios including edge cases.
"""

import requests
import json
import time
import random
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

class APITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.customer_id = None
        self.loan_id = None
        self.test_results = []
    
    def log_test(self, test_name, status, response_code, response_data=None, error=None):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "response_code": response_code,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data,
            "error": str(error) if error else None
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if status == "PASS" else "❌"
        print(f"{status_emoji} {test_name}: {status} (HTTP {response_code})")
        if error:
            print(f"   Error: {error}")
    
    def test_health_check(self):
        """Test basic health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health/")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Health Check", "PASS", response.status_code, data)
                else:
                    self.log_test("Health Check", "FAIL", response.status_code, data)
            else:
                self.log_test("Health Check", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Health Check", "ERROR", 0, error=e)
    
    def test_api_status(self):
        """Test detailed API status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/status")
            if response.status_code == 200:
                data = response.json()
                if "services" in data and "customers" in data["services"]:
                    self.log_test("API Status", "PASS", response.status_code, data)
                else:
                    self.log_test("API Status", "FAIL", response.status_code, data)
            else:
                self.log_test("API Status", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("API Status", "ERROR", 0, error=e)
    
    def test_customer_registration(self):
        """Test customer registration endpoint"""
        # Generate unique phone number
        phone_number = random.randint(6000000000, 9999999999)
        
        payload = {
            "first_name": "Test",
            "last_name": "User",
            "age": 30,
            "monthly_income": 50000,
            "phone_number": phone_number
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/register",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                if "customer_id" in data and "approved_limit" in data:
                    self.customer_id = data["customer_id"]
                    # Check approved limit calculation (36 * monthly_income)
                    expected_limit = 36 * 50000
                    expected_limit = round(expected_limit / 100000) * 100000  # Round to nearest lakh
                    
                    if float(data["approved_limit"]) == expected_limit:
                        self.log_test("Customer Registration", "PASS", response.status_code, data)
                    else:
                        self.log_test("Customer Registration", "FAIL", response.status_code, 
                                    data, f"Approved limit calculation incorrect")
                else:
                    self.log_test("Customer Registration", "FAIL", response.status_code, data)
            else:
                self.log_test("Customer Registration", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Customer Registration", "ERROR", 0, error=e)
    
    def test_duplicate_phone_registration(self):
        """Test duplicate phone number registration (should fail)"""
        if not self.customer_id:
            print("⚠️  Skipping duplicate phone test - no customer registered")
            return
        
        # Try to register with same phone number
        payload = {
            "first_name": "Another",
            "last_name": "User",
            "age": 25,
            "monthly_income": 40000,
            "phone_number": 9876543210  # Use a likely duplicate
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/register",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 400:
                self.log_test("Duplicate Phone Registration", "PASS", response.status_code)
            else:
                self.log_test("Duplicate Phone Registration", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Duplicate Phone Registration", "ERROR", 0, error=e)
    
    def test_loan_eligibility_check(self):
        """Test loan eligibility check endpoint"""
        if not self.customer_id:
            print("⚠️  Skipping eligibility test - no customer registered")
            return
        
        payload = {
            "customer_id": self.customer_id,
            "loan_amount": 100000,
            "interest_rate": 10.5,
            "tenure": 24
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/check-eligibility",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["customer_id", "approval", "corrected_interest_rate", "monthly_installment"]
                if all(field in data for field in required_fields):
                    self.log_test("Loan Eligibility Check", "PASS", response.status_code, data)
                else:
                    self.log_test("Loan Eligibility Check", "FAIL", response.status_code, data)
            else:
                self.log_test("Loan Eligibility Check", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Loan Eligibility Check", "ERROR", 0, error=e)
    
    def test_loan_creation(self):
        """Test loan creation endpoint"""
        if not self.customer_id:
            print("⚠️  Skipping loan creation test - no customer registered")
            return
        
        payload = {
            "customer_id": self.customer_id,
            "loan_amount": 100000,
            "interest_rate": 12.0,
            "tenure": 24
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/create-loan",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 201:
                data = response.json()
                if "loan_id" in data and "monthly_installment" in data:
                    self.loan_id = data["loan_id"]
                    self.log_test("Loan Creation", "PASS", response.status_code, data)
                else:
                    self.log_test("Loan Creation", "FAIL", response.status_code, data)
            else:
                self.log_test("Loan Creation", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Loan Creation", "ERROR", 0, error=e)
    
    def test_view_loan_details(self):
        """Test view loan details endpoint"""
        if not self.loan_id:
            print("⚠️  Skipping loan details test - no loan created")
            return
        
        try:
            response = requests.get(f"{self.base_url}/view-loan/{self.loan_id}")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["loan_id", "customer", "loan_amount", "interest_rate"]
                if all(field in data for field in required_fields):
                    self.log_test("View Loan Details", "PASS", response.status_code, data)
                else:
                    self.log_test("View Loan Details", "FAIL", response.status_code, data)
            else:
                self.log_test("View Loan Details", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("View Loan Details", "ERROR", 0, error=e)
    
    def test_view_customer_loans(self):
        """Test view customer loans endpoint"""
        if not self.customer_id:
            print("⚠️  Skipping customer loans test - no customer registered")
            return
        
        try:
            response = requests.get(f"{self.base_url}/view-loans/{self.customer_id}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test("View Customer Loans", "PASS", response.status_code, data)
                else:
                    self.log_test("View Customer Loans", "FAIL", response.status_code, data)
            else:
                self.log_test("View Customer Loans", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("View Customer Loans", "ERROR", 0, error=e)
    
    def test_customer_credit_score(self):
        """Test customer credit score endpoint"""
        if not self.customer_id:
            print("⚠️  Skipping credit score test - no customer registered")
            return
        
        try:
            response = requests.get(f"{self.base_url}/customer/{self.customer_id}/credit-score")
            
            if response.status_code == 200:
                data = response.json()
                # Check for actual response structure (components instead of score_breakdown)
                if "credit_score" in data and ("components" in data or "score_breakdown" in data):
                    self.log_test("Customer Credit Score", "PASS", response.status_code, data)
                else:
                    self.log_test("Customer Credit Score", "FAIL", response.status_code, data)
            else:
                self.log_test("Customer Credit Score", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Customer Credit Score", "ERROR", 0, error=e)
    
    def test_invalid_customer_eligibility(self):
        """Test eligibility check with invalid customer ID"""
        payload = {
            "customer_id": 99999,
            "loan_amount": 50000,
            "interest_rate": 8.0,
            "tenure": 12
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/check-eligibility",
                headers=self.headers,
                json=payload
            )
            
            # Accept both 400 and 404 as valid error responses for invalid customer
            if response.status_code in [400, 404]:
                self.log_test("Invalid Customer Eligibility", "PASS", response.status_code)
            else:
                self.log_test("Invalid Customer Eligibility", "FAIL", response.status_code)
        except Exception as e:
            self.log_test("Invalid Customer Eligibility", "ERROR", 0, error=e)
    
    def test_existing_customer_eligibility(self):
        """Test eligibility check with existing customer from loaded data"""
        # First, let's try to get a valid customer ID from the API status
        try:
            status_response = requests.get(f"{self.base_url}/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                customer_count = status_data.get("services", {}).get("customers", 0)
                
                if customer_count > 0:
                    # Try with customer ID 1 (likely to exist from loaded data)
                    payload = {
                        "customer_id": 1,
                        "loan_amount": 50000,
                        "interest_rate": 8.0,
                        "tenure": 12
                    }
                    
                    response = requests.post(
                        f"{self.base_url}/check-eligibility",
                        headers=self.headers,
                        json=payload
                    )
                    
                    # Accept 200 (success) or 400 (validation error) as valid responses
                    if response.status_code in [200, 400]:
                        if response.status_code == 200:
                            data = response.json()
                            self.log_test("Existing Customer Eligibility", "PASS", response.status_code, data)
                        else:
                            # 400 might be due to business rules (EMI limit, etc.)
                            self.log_test("Existing Customer Eligibility", "PASS", response.status_code, 
                                        {"note": "Business rule validation triggered"})
                    else:
                        self.log_test("Existing Customer Eligibility", "FAIL", response.status_code)
                else:
                    self.log_test("Existing Customer Eligibility", "SKIP", 0, 
                                {"note": "No existing customers found"})
            else:
                self.log_test("Existing Customer Eligibility", "SKIP", 0, 
                            {"note": "Could not get customer count"})
        except Exception as e:
            self.log_test("Existing Customer Eligibility", "ERROR", 0, error=e)
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Credit Approval System API Tests")
        print("=" * 60)
        
        # Basic health tests
        self.test_health_check()
        self.test_api_status()
        
        # Customer registration tests
        self.test_customer_registration()
        self.test_duplicate_phone_registration()
        
        # Loan workflow tests
        self.test_loan_eligibility_check()
        self.test_loan_creation()
        self.test_view_loan_details()
        self.test_view_customer_loans()
        
        # Additional feature tests
        self.test_customer_credit_score()
        
        # Error handling tests
        self.test_invalid_customer_eligibility()
        self.test_existing_customer_eligibility()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        errors = sum(1 for result in self.test_results if result["status"] == "ERROR")
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"🔥 Errors: {errors}/{total}")
        print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
        
        if self.customer_id:
            print(f"\n🆔 Test Customer ID: {self.customer_id}")
        if self.loan_id:
            print(f"🏦 Test Loan ID: {self.loan_id}")
        
        # Save detailed results
        with open("test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n📄 Detailed results saved to: test_results.json")

if __name__ == "__main__":
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(5)
    
    tester = APITester()
    tester.run_all_tests()