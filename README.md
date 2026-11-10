# SoftMed Backend API

A FastAPI-based backend application for the SoftMed telemedicine platform, providing APIs for managing doctors, patients, appointments, medical records, prescriptions, payments, and telemedicine queue management.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Environment Variables](#environment-variables)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Database Migrations](#database-migrations)
- [Production Deployment](#production-deployment)
- [Project Structure](#project-structure)

## Features

- **User Management**: Authentication, authorization, and user profiles with role-based access (Admin, Doctor, Customer)
- **Appointment Management**: Schedule and manage medical appointments
- **Telemedicine Queue**: Real-time queue management for telemedicine consultations
- **Medical Records**: Store and manage patient medical records
- **Prescriptions**: Digital prescription management with Memed API integration
- **Payment Processing**: PIX payment integration via Pagar.me
- **Google Meet Integration**: Automated Google Meet link generation for consultations
- **Reports**: Financial and operational reporting

## Prerequisites

- Python 3.9+ (Python 3.14 recommended)
- PostgreSQL 12+
- Redis (for queue management)
- pip (Python package manager)
- Virtual environment (venv)

## Local Development Setup

### 1. Clone the Repository

```bash
cd backend
```

### 2. Create and Activate Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the `backend` directory with the following variables (see [Environment Variables](#environment-variables) section for details):

```bash
cp .env.example .env  # If you have an example file
# Or create .env manually
```

### 5. Set Up PostgreSQL Database

You can create the database using any of these methods:

#### Option A: Using Python Setup Script (Recommended - Easiest)

```bash
# Activate virtual environment first
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# Run the setup script
python setup_db.py
```

The script will guide you through the setup and generate the DATABASE_URL for your `.env` file.

#### Option B: Using psql Command Line

```bash
# Connect to PostgreSQL and create database
psql -U postgres -c "CREATE DATABASE softmed_db;"

# Or connect interactively
psql -U postgres
CREATE DATABASE softmed_db;
\q
```

#### Option C: Using createdb Command

```bash
createdb -U postgres softmed_db
```

#### Option D: Using pgAdmin (GUI)

1. Open pgAdmin 4
2. Connect to your PostgreSQL server
3. Right-click "Databases" → "Create" → "Database..."
4. Enter database name: `softmed_db`
5. Click "Save"

### 6. Configure Database Connection

Update your `.env` file with the database connection string:

```env
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/softmed_db
```

### 7. Run Database Migrations

```bash
# Initialize Alembic (if not already done)
alembic upgrade head
```

### 8. Start the Development Server

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

## Environment Variables

Create a `.env` file in the `backend` directory with the following variables:

### Required Variables

```env
# Database
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/softmed_db

# JWT Authentication
SECRET_KEY=your-secret-key-here-minimum-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend URL (for password reset links)
FRONTEND_DOCTOR_BASE_URL=http://localhost:5173

# CORS Configuration (comma-separated list of allowed origins)
# Example: CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
# Use "*" to allow all origins (development only - NOT recommended for production)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
```

### Optional Variables (for specific features)

```env
# Email Configuration (for password reset)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com

# Google Meet Integration
GOOGLE_OAUTH_TOKEN=your-google-oauth-token
GOOGLE_REFRESH_TOKEN=your-google-refresh-token
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Pagar.me Payment Integration
PAGARME_SECRET_KEY=your-pagarme-secret-key
PAGARME_API_URL=https://api.pagar.me/core/v5

# Memed API (for prescriptions)
MEMED_API_KEY=your-memed-api-key

# Redis (for queue management)
REDIS_URL=redis://localhost:6379/0
```

### Generating a Secret Key

You can generate a secure secret key using Python:

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Creating an Admin User

To create an admin or superadmin user, use the provided script:

```bash
# Make sure your virtual environment is activated
.\venv\Scripts\Activate.ps1  # Windows
# or
source venv/bin/activate     # Linux/Mac

# Run the admin creation script
python create_admin.py
```

The script will:
- Prompt you for admin details (email, name, password)
- Ask you to choose between `admin` or `superadmin` role
- Optionally collect phone and CPF information
- Create the user in the database with proper password hashing

**Note**: Make sure your `.env` file has the correct `DATABASE_URL` configured before running the script.

## Database Schema

### Users Table

The `users` table stores all user information including patients, doctors, and admins.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `email` | String (Unique) | User email address |
| `hashed_password` | String | Bcrypt hashed password |
| `is_active` | Boolean | Account active status |
| `role` | Enum | User role: `superadmin`, `admin`, `doctor`, `customer` |
| `name` | String | Full name |
| `gender` | String | Gender |
| `cpf` | String (Unique) | Brazilian CPF (tax ID) |
| `phone` | String | Phone number |
| `birthday` | Date | Date of birth |
| `cep` | String | Brazilian postal code |
| `logradouro` | String | Street address |
| `numero` | String | Address number |
| `complemento` | String | Address complement (optional) |
| `bairro` | String | Neighborhood |
| `estado` | String | State |
| `cidade` | String | City |
| `crm` | String | Doctor's CRM (optional, for doctors) |
| `uf_crm` | String | CRM state (optional, for doctors) |
| `bank_information` | String | Bank details (optional, for doctors) |
| `attached_document` | String | Document file path (optional) |
| `password_reset_token` | String | Password reset token (optional) |
| `password_reset_expires_at` | DateTime | Token expiration (optional) |
| `queue_status` | String | Queue status: `waiting`, `in_service`, `completed`, `no_wait` |
| `queue_entry_time` | DateTime | Time when user entered queue (optional) |

### Appointments Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `patient_id` | Integer (FK) | Reference to users.id |
| `doctor_id` | Integer (FK) | Reference to users.id |
| `appointment_time` | DateTime | Scheduled appointment time |
| `status` | String | Appointment status (default: "scheduled") |

### Medical Records Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `patient_id` | Integer (FK) | Reference to users.id |
| `record_date` | DateTime | Date of medical record |
| `diagnosis` | Text | Diagnosis information |
| `treatment` | Text | Treatment information |

### Prescriptions Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `patient_id` | Integer (FK) | Reference to users.id |
| `prescriber_id` | Integer (FK) | Reference to users.id (doctor) |
| `prescription_date` | DateTime | Date of prescription |
| `medication` | String | Medication name |
| `dosage` | String | Medication dosage |

### Payments Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `user_id` | Integer (FK) | Reference to users.id |
| `start_date` | DateTime | Payment start date |
| `end_date` | DateTime | Payment end date |
| `pix_transaction_id` | String | PIX transaction ID (optional) |
| `pix_qr_code_data` | String | PIX QR code data (optional) |
| `pix_status` | String | Payment status (default: "pending") |

### Transactions Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK) | Primary key |
| `date_time_db` | DateTime | DateTime object for sorting |
| `date_time` | String | Original date/time string |
| `invoice` | String | Invoice number (optional) |
| `description` | String | Transaction description |
| `total_value` | Float | Total transaction value |
| `available_balance` | Float | Available balance after transaction |
| `blocked_balance` | Float | Blocked balance after transaction |

## API Endpoints

### Authentication (`/auth`)

- **POST** `/auth/token` - Login and get access token
  - Body: `username` (email), `password`
  - Returns: `access_token`, `token_type`

- **POST** `/auth/forgot-password` - Request password reset
  - Body: `email`
  - Returns: Success message

- **POST** `/auth/reset-password` - Reset password with token
  - Body: `token`, `new_password`, `confirm_password`
  - Returns: Success message

### Users (`/users`)

- **GET** `/users/` - Get all users (requires authentication)
- **GET** `/users/{user_id}` - Get user by ID
- **POST** `/users/` - Create new user
- **PUT** `/users/{user_id}` - Update user
- **DELETE** `/users/{user_id}` - Delete user
- **GET** `/users/me` - Get current user profile
- **PUT** `/users/me` - Update current user profile

### Appointments (`/appointments`)

- **GET** `/appointments/` - Get all appointments
- **GET** `/appointments/{appointment_id}` - Get appointment by ID
- **POST** `/appointments/` - Create new appointment
- **PUT** `/appointments/{appointment_id}` - Update appointment
- **DELETE** `/appointments/{appointment_id}` - Delete appointment
- **POST** `/appointments/create-meeting` - Create Google Meet meeting
  - Body: `summary`, `start_time`, `end_time`, `attendees[]`

### Queue Management (`/queue`)

- **GET** `/queue/` - Get all patients in waiting queue
- **GET** `/queue/stats` - Get queue statistics
  - Returns: `waiting_count`, `in_service_count`, `completed_count`, `no_wait_count`
- **POST** `/queue/{patient_id}` - Add patient to queue
- **DELETE** `/queue/{patient_id}` - Remove patient from queue
- **POST** `/queue/call_next/{doctor_id}` - Call next patient in queue
  - Returns: Appointment details and Google Meet link

### Medical Records (`/medical_records`)

- **GET** `/medical_records/` - Get all medical records
- **GET** `/medical_records/{record_id}` - Get medical record by ID
- **POST** `/medical_records/` - Create new medical record
- **PUT** `/medical_records/{record_id}` - Update medical record
- **DELETE** `/medical_records/{record_id}` - Delete medical record

### Prescriptions (`/prescriptions`)

- **GET** `/prescriptions/` - Get all prescriptions
- **GET** `/prescriptions/{prescription_id}` - Get prescription by ID
- **POST** `/prescriptions/` - Create new prescription
- **PUT** `/prescriptions/{prescription_id}` - Update prescription
- **DELETE** `/prescriptions/{prescription_id}` - Delete prescription

### Payments (`/payments`)

- **GET** `/payments/` - Get all payments
- **GET** `/payments/{payment_id}` - Get payment by ID
- **POST** `/payments/` - Create new payment
- **PUT** `/payments/{payment_id}` - Update payment
- **POST** `/payments/{payment_id}/pix` - Generate PIX payment

### Transactions (`/transactions`)

- **GET** `/transactions/` - Get all transactions
- **GET** `/transactions/{transaction_id}` - Get transaction by ID
- **POST** `/transactions/` - Create new transaction

### Doctors (`/doctors`)

- **GET** `/doctors/` - Get all doctors
- **GET** `/doctors/{doctor_id}` - Get doctor by ID

### Reports (`/reports`)

- **GET** `/reports/financial` - Get financial reports
- **GET** `/reports/operational` - Get operational reports

## Database Migrations

This project uses Alembic for database migrations.

### Creating a New Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration file
alembic revision -m "description of changes"
```

### Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Migration History

```bash
# View migration history
alembic history

# View current database revision
alembic current
```

## Production Deployment

### CI/CD Setup for Digital Ocean

For automated deployments to a Digital Ocean Droplet, see the comprehensive guide:
- **[CI/CD Setup Guide](CICD_SETUP.md)** - Complete step-by-step instructions
- **[Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** - Pre-deployment checklist

The CI/CD setup includes:
- Automated deployments via GitHub Actions
- Systemd service management
- Nginx reverse proxy configuration
- SSL/HTTPS with Let's Encrypt
- Automated backups
- Health checks and monitoring

### Using Docker (Recommended)

1. **Create Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. **Create docker-compose.yml**:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: softmed_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:postgres@db:5432/softmed_db
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      # Add other environment variables
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

volumes:
  postgres_data:
```

3. **Deploy**:

```bash
docker-compose up -d
```

### Using Gunicorn (Production Server)

1. **Install Gunicorn**:

```bash
pip install gunicorn
```

2. **Run with Gunicorn**:

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Environment-Specific Configuration

For production, ensure:

1. **Set secure SECRET_KEY**: Use a strong, randomly generated secret key
2. **Update CORS origins**: Restrict CORS to your frontend domain only
3. **Use environment variables**: Never commit `.env` files
4. **Enable HTTPS**: Use a reverse proxy (nginx) with SSL certificates
5. **Database connection pooling**: Configure appropriate pool sizes
6. **Logging**: Set up proper logging and monitoring
7. **Backup strategy**: Implement regular database backups

### Example Production `.env`

```env
DATABASE_URL=postgresql+psycopg2://user:password@db-host:5432/softmed_db
SECRET_KEY=your-production-secret-key-minimum-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_BASE_URL=https://your-frontend-domain.com
# ... other production variables
```

## Project Structure

```
backend/
├── alembic/              # Database migration files
│   ├── versions/         # Migration version files
│   └── env.py           # Alembic environment configuration
├── app/
│   ├── models/          # SQLAlchemy database models
│   │   ├── user.py
│   │   ├── appointment.py
│   │   ├── medical_record.py
│   │   ├── payment.py
│   │   ├── prescription.py
│   │   └── transaction.py
│   ├── routers/         # API route handlers
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── appointments.py
│   │   ├── queue.py
│   │   ├── medical_records.py
│   │   ├── prescriptions.py
│   │   ├── payments.py
│   │   ├── transactions.py
│   │   ├── doctors.py
│   │   └── reports.py
│   ├── schemas/         # Pydantic schemas for request/response validation
│   ├── services/        # Business logic services
│   │   ├── email_service.py
│   │   ├── google_meet_service.py
│   │   ├── memed_service.py
│   │   ├── payment_service.py
│   │   ├── pix_service.py
│   │   └── queue_service.py
│   ├── database.py      # Database connection configuration
│   └── main.py          # FastAPI application entry point
├── alembic.ini          # Alembic configuration
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running: `pg_isready`
- Check DATABASE_URL format: `postgresql+psycopg2://user:password@host:port/dbname`
- Ensure database exists and user has proper permissions

### Migration Issues

- Check current migration: `alembic current`
- View migration history: `alembic history`
- If migrations are out of sync, you may need to manually fix the database state

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port 8000
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# Use a different port
uvicorn app.main:app --reload --port 8001
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests (if available)
4. Create a pull request

## License

[Your License Here]

## Support

For issues and questions, please open an issue in the repository or contact the development team.


