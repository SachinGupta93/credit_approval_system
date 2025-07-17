# 🚀 Credit Approval System - Complete API Testing Guide

## 📋 Base URL
```
http://localhost:8000
```

## 🔗 All Available Routes

### **1. Health Check Endpoints**

#### GET `/health/`
**Purpose**: Basic health check
**Response**:
```json
{
    "status": "healthy",
    "service": "credit_approval_system"
}
```

#### GET `/status`
**Purpose**: Detailed API status with database info
**Response**:
```json
{
    "status": "healthy",
    "timestamp": "2025-01-17T17:19:47.112800+00:00",
    "version": "1.0.0",
    "database": "connected",
    "services": {
        "customers": 50,
        "loans": 159,
        "credit_scores": 0
    }
}
```

---

### **2. Customer Registration**

#### POST `/register`
**Purpose**: Register a new customer
**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
    "first_name": "John",
    "last_name": "Doe",
    "age": 30,
    "monthly_income": 50000,
    "phone_number": 9876543210
}
```

**Response (201 Created)**:
```json
{
    "customer_id": 82,
    "name": "John Doe",
    "age": 30,
    "monthly_income": "50000.00",
    "approved_limit": "1800000.00",
    "phone_number": 9876543210
}
```

**Business Logic**: 
- `approved_limit = 36 × monthly_income` (rounded to nearest lakh)
- Phone number must be unique
- Age must be 18+

---

### **3. Loan Eligibility Check**

#### POST `/check-eligibility`
**Purpose**: Check if customer is eligible for a loan
**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
    "customer_id": 82,
    "loan_amount": 100000,
    "interest_rate": 10.5,
    "tenure": 24
}
```

**Response (200 OK)**:
```json
{
    "customer_id": 82,
    "approval": true,
    "interest_rate": "10.50",
    "corrected_interest_rate": "12.00",
    "tenure": 24,
    "monthly_installment": "4707.35"
}
```

**Credit Scoring Logic**:
- Score > 50: Approve with requested rate
- 30-50: Approve with min 12% rate
- 10-30: Approve with min 16% rate
- < 10: Reject loan
- EMI > 50% salary: Reject

---

### **4. Loan Creation**

#### POST `/create-loan`
**Purpose**: Create a new loan after eligibility check
**Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
    "customer_id": 82,
    "loan_amount": 100000,
    "interest_rate": 12.0,
    "tenure": 24
}
```

**Response (201 Created)**:
```json
{
    "loan_id": "f78555f2-c811-4d6e-80f5-f2c65b480caf",
    "customer_id": 82,
    "loan_approved": true,
    "message": "Loan approved successfully",
    "monthly_installment": "4707.35"
}
```

**Note**: Use the `corrected_interest_rate` from eligibility check

---

### **5. View Loan Details**

#### GET `/view-loan/{loan_id}`
**Purpose**: Get detailed information about a specific loan
**Example**: `/view-loan/f78555f2-c811-4d6e-80f5-f2c65b480caf`

**Response (200 OK)**:
```json
{
    "loan_id": "f78555f2-c811-4d6e-80f5-f2c65b480caf",
    "customer": {
        "id": 82,
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": 9876543210,
        "age": 30
    },
    "loan_amount": "100000.00",
    "interest_rate": "12.00",
    "tenure": 24,
    "monthly_installment": "4707.35"
}
```

---

### **6. View Customer Loans**

#### GET `/view-loans/{customer_id}`
**Purpose**: Get all loans for a specific customer
**Example**: `/view-loans/82`

**Response (200 OK)**:
```json
[
    {
        "loan_id": "f78555f2-c811-4d6e-80f5-f2c65b480caf",
        "loan_amount": "100000.00",
        "interest_rate": "12.00",
        "repayments_left": 24,
        "monthly_installment": "4707.35"
    }
]
```

---

### **7. Customer Credit Score (Bonus)**

#### GET `/customer/{customer_id}/credit-score`
**Purpose**: Get detailed credit score breakdown
**Example**: `/customer/82/credit-score`

**Response (200 OK)**:
```json
{
    "customer_id": 82,
    "credit_score": 75,
    "score_breakdown": {
        "past_loans_performance": 30.0,
        "loan_volume": 20.0,
        "current_year_activity": 15.0,
        "credit_utilization": 10.0
    },
    "calculated_at": "2025-01-17T17:30:00Z"
}
```

---

## 🧪 **POSTMAN COLLECTION SETUP**

### **Collection Variables**:
```
base_url: http://localhost:8000
customer_id: 82 (update after registration)
loan_id: (update after loan creation)
```

### **Test Sequence**:
1. **Health Check** → GET `{{base_url}}/health/`
2. **API Status** → GET `{{base_url}}/status`
3. **Register Customer** → POST `{{base_url}}/register`
4. **Check Eligibility** → POST `{{base_url}}/check-eligibility`
5. **Create Loan** → POST `{{base_url}}/create-loan`
6. **View Loan** → GET `{{base_url}}/view-loan/{{loan_id}}`
7. **View Customer Loans** → GET `{{base_url}}/view-loans/{{customer_id}}`
8. **Credit Score** → GET `{{base_url}}/customer/{{customer_id}}/credit-score`

---

## 🔧 **CURL COMMANDS FOR TESTING**

### **1. Health Check**
```bash
curl -X GET http://localhost:8000/health/
```

### **2. Register Customer**
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe", 
    "age": 30,
    "monthly_income": 50000,
    "phone_number": 9876543210
  }'
```

### **3. Check Eligibility**
```bash
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 82,
    "loan_amount": 100000,
    "interest_rate": 10.5,
    "tenure": 24
  }'
```

### **4. Create Loan**
```bash
curl -X POST http://localhost:8000/create-loan \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 82,
    "loan_amount": 100000,
    "interest_rate": 12.0,
    "tenure": 24
  }'
```

### **5. View Loan**
```bash
curl -X GET http://localhost:8000/view-loan/f78555f2-c811-4d6e-80f5-f2c65b480caf
```

### **6. View Customer Loans**
```bash
curl -X GET http://localhost:8000/view-loans/82
```

---

## 📊 **TESTING WITH EXISTING DATA**

### **Existing Customers (from Excel data)**:
You can test with existing customer IDs from the loaded data:
- Customer IDs: Check `/status` endpoint for total customers
- Use phone numbers from the loaded customer data

### **Sample Test Data**:
```json
{
  "existing_customer_test": {
    "customer_id": 1,
    "loan_amount": 50000,
    "interest_rate": 8.0,
    "tenure": 12
  }
}
```

---

## ⚠️ **Error Responses**

### **400 Bad Request**:
```json
{
    "error": "Validation failed",
    "details": {
        "age": ["Ensure this value is greater than or equal to 18."]
    }
}
```

### **404 Not Found**:
```json
{
    "error": "Customer not found",
    "customer_id": 999
}
```

### **500 Internal Server Error**:
```json
{
    "error": "Internal server error",
    "message": "Database connection failed"
}
```

---

## 🎯 **TESTING CHECKLIST**

### **✅ Basic Functionality**:
- [ ] Health check works
- [ ] Customer registration with unique phone
- [ ] Approved limit calculation (36 × salary)
- [ ] Credit score calculation
- [ ] Loan eligibility rules
- [ ] EMI calculation with compound interest
- [ ] Loan creation and storage
- [ ] Loan retrieval by ID
- [ ] Customer loans listing

### **✅ Edge Cases**:
- [ ] Duplicate phone number registration
- [ ] Invalid customer ID in eligibility check
- [ ] Loan amount exceeding approved limit
- [ ] EMI > 50% of salary rejection
- [ ] Non-existent loan ID lookup
- [ ] Invalid UUID format in loan lookup

### **✅ Business Rules**:
- [ ] Credit score > 50: Approve with requested rate
- [ ] Credit score 30-50: Min 12% interest rate
- [ ] Credit score 10-30: Min 16% interest rate  
- [ ] Credit score < 10: Loan rejection
- [ ] Current loans > approved limit: Score = 0

---

## 🚀 **QUICK START TESTING**

1. **Start the system**:
   ```bash
   cd credit_approval_system
   docker-compose up -d
   ```

2. **Wait for services** (30 seconds)

3. **Test health**:
   ```bash
   curl http://localhost:8000/health/
   ```

4. **Import Postman collection** or use the curl commands above

5. **Follow the test sequence** in order

**All endpoints are fully functional and tested!** 🎉