# 🏦 Credit Approval System

A comprehensive **Django REST API** for credit approval with intelligent scoring algorithms and microservices architecture.

## 🚀 **Quick Start**

### **One-Command Setup**
```bash
# Clone repository
git clone https://github.com/yourusername/credit_approval_system.git
cd credit_approval_system

# Start all services
docker-compose up -d

# System ready at http://localhost:8000
```

### **System Architecture**
- **🐳 Docker**: 4 microservices (API, Database, Redis, Celery)
- **🗄️ PostgreSQL**: Production database with persistent storage
- **📦 Redis**: Caching and message broker
- **⚙️ Celery**: Background task processing
- **🌐 Django REST**: API framework with comprehensive endpoints

---

## 📊 **API Endpoints**

### **Core Endpoints**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register` | Register new customer |
| `POST` | `/check-eligibility` | Check loan eligibility |
| `POST` | `/create-loan` | Create new loan |
| `GET` | `/view-loan/{loan_id}` | View loan details |
| `GET` | `/view-loans/{customer_id}` | View customer loans |

### **Utility Endpoints**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health/` | System health check |
| `GET` | `/status` | Detailed system status |
| `GET` | `/customer/{id}/credit-score` | Get credit score |

---

## 🎯 **Features**

### **✅ Core Features**
- **Customer Management**: Registration with validation
- **Loan Eligibility**: Credit score-based approval
- **Loan Creation**: Automated processing
- **Loan Viewing**: Comprehensive details
- **Data Validation**: Robust input validation

### **🏆 Advanced Features**
- **Credit Scoring**: 4-component algorithm
- **Interest Rate Correction**: Dynamic rate adjustment
- **EMI Calculation**: Compound interest formula
- **Background Processing**: Async Excel data loading
- **Health Monitoring**: System status tracking

---

## 🧪 **Testing**

### **Automated Testing**
```bash
# Run all tests
python manage.py test

# Run API integration tests
python test_all_endpoints.py

# Results: 21/21 tests passing ✅
```

### **Manual Testing**
```bash
# Import Postman collection
Credit_Approval_System.postman_collection.json

# Test endpoints with pre-configured requests
```

---

## 🗄️ **Database**

### **Models**
- **Customer**: Personal and financial information
- **Loan**: Loan details and payment history
- **CreditScore**: Credit scoring components

### **Sample Data**
- **50 Customers**: Pre-loaded from Excel
- **159 Loans**: Historical loan data
- **Real-time Growth**: New customers and loans

---

## 🏗️ **Development Setup**

### **Local Development**
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py load_initial_data

# Start server
python manage.py runserver
```

### **Production Deployment**
```bash
# Production-ready with Docker
docker-compose up -d

# Services:
# - Web API: http://localhost:8000
# - Database: PostgreSQL on port 5432
# - Cache: Redis on port 6379
# - Worker: Celery for background tasks
```

---

## 📋 **Business Logic**

### **Credit Scoring Algorithm**
```python
# Components (weighted):
- Past Loans Performance (40%)
- Loan Volume History (25%)
- Current Year Activity (20%)
- Credit Utilization (15%)
```

### **Approval Rules**
- **Excellent (50+)**: Use requested interest rate
- **Good (30-49)**: Minimum 12% interest rate
- **Fair (10-29)**: Minimum 16% interest rate
- **Poor (<10)**: Loan rejected

### **EMI Calculation**
```python
# Formula: P * [r(1+r)^n] / [(1+r)^n - 1]
# Where: P = Principal, r = Monthly rate, n = Tenure
```

---

## 🔧 **Configuration**

### **Environment Variables**
```env
DATABASE_URL=postgresql://user:pass@db:5432/credit_db
REDIS_URL=redis://redis:6379/0
DEBUG=1
```

### **Docker Services**
```yaml
services:
  web:       # Django API (port 8000)
  db:        # PostgreSQL (port 5432)
  redis:     # Redis (port 6379)
  celery:    # Background worker
```

---

## 🎬 **Video Demo Guide**

### **Files to Show in Video**

#### **1. Repository Structure (30 seconds)**
```
credit_approval_system/
├── 🐳 docker-compose.yml     # Microservices setup
├── 🐳 Dockerfile             # Container definition
├── 📊 data/                  # Excel data files
├── 🧪 test_all_endpoints.py  # Integration tests
├── 🌐 credit_system/         # Django application
│   ├── api/                  # API endpoints
│   └── core/                 # Database models
└── 📋 requirements.txt       # Dependencies
```

#### **2. Key Code Files (2 minutes)**
- **`credit_system/api/views.py`**: All API endpoints
- **`credit_system/core/models.py`**: Database models
- **`credit_system/api/credit_scoring.py`**: Business logic
- **`docker-compose.yml`**: Production architecture

#### **3. Live Demo (3 minutes)**
- Show running containers: `docker-compose ps`
- Run comprehensive unit tests: `python manage.py test -v 2`
- Display system health: `/health` and `/status` endpoints
- Show 21/21 tests passing for complete endpoint validation

---

## 🎤 **Video Script**

### **Opening (30 seconds)**
> "Welcome to my Credit Approval System - a production-ready Django REST API with intelligent credit scoring. This system demonstrates enterprise-level architecture with microservices, automated testing, and comprehensive business logic."

### **Architecture Overview (1 minute)**
> "The system uses Docker to orchestrate 4 microservices: PostgreSQL for data persistence, Redis for caching, Django for the API, and Celery for background processing. Everything starts with a single docker-compose command."

### **Code Walkthrough (2 minutes)**
> "Let me show you the key components: The models define our data structure with customers, loans, and credit scores. The API views handle all endpoints with proper validation and error handling. The credit scoring algorithm uses a sophisticated 4-component formula for loan approval decisions."

### **Comprehensive Testing (2 minutes)**
> "Now let me demonstrate the enterprise-level testing approach. I'll run the comprehensive unit tests that validate all endpoints automatically. Notice how all 21 tests pass, covering customer registration, loan eligibility, loan creation, and all business logic scenarios - this is much more professional than manual testing."

### **Testing & Quality (30 seconds)**
> "The system includes comprehensive testing with 21 unit tests and integration tests, all passing. This ensures reliability and maintainability for production use."

### **Closing (30 seconds)**
> "This project demonstrates full-stack development skills, enterprise architecture, and production-ready code quality. It's designed for scalability and includes all the features required for a real-world credit approval system."

---

## 🏆 **Technical Achievements**

### **✅ Assignment Compliance**
- All PDF requirements implemented
- Docker single-command deployment
- Comprehensive unit testing (21 tests)
- Professional code organization

### **🎯 Bonus Features**
- Advanced credit scoring algorithm
- Microservices architecture
- Background task processing
- Health monitoring endpoints
- Integration test automation

### **🔧 Production Ready**
- PostgreSQL database
- Redis caching
- Celery task queue
- Docker containerization
- Comprehensive logging

---

## 📞 **Support**

### **Quick Commands**
```bash
# Start system
docker-compose up -d

# Stop system
docker-compose down

# View logs
docker-compose logs

# Run tests
python manage.py test
```

### **Health Check**
```bash
# System status
curl http://localhost:8000/health/

# Detailed metrics
curl http://localhost:8000/status
```

---

## 📄 **License**

This project is developed as part of a technical assignment demonstrating Django REST API development with enterprise-level architecture and comprehensive testing.

---

**🚀 Ready for production deployment and scalable growth!**