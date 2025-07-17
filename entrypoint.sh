#!/bin/bash

# Credit Approval System - Docker Entrypoint Script
# This script initializes the Django application in the container

echo "Starting Credit Approval System..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! python manage.py dbshell --command="SELECT 1;" 2>/dev/null; do
    echo "Database is not ready yet. Waiting..."
    sleep 2
done

echo "Database is ready!"

# Create migrations
echo "Creating database migrations..."
python manage.py makemigrations core
python manage.py makemigrations api

# Apply migrations
echo "Applying database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created: admin/admin123")
else:
    print("Superuser already exists")
EOF

# Load initial data if Excel files exist
echo "Loading initial data..."
if [ -f "data/customer_data.xlsx" ] && [ -f "data/loan_data.xlsx" ]; then
    python manage.py load_initial_data
    echo "Initial data loaded successfully"
else
    echo "Excel files not found. Generating test data..."
    python manage.py load_initial_data --generate-test-data --num-customers 20 --num-loans 2
fi

# Start the Django development server
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000