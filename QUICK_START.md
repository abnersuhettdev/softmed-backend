# Quick Start Guide - Running the Backend

This guide will help you set up and run the SoftMed backend on Windows with pgAdmin.

## Step-by-Step Setup

### Step 1: Create Database

You can create the database using either **pgAdmin (GUI)** or **Command Line**. Choose one method:

#### Option A: Using Command Line (Recommended)

**Method 1: Using psql (if in PATH)**

```powershell
# Connect to PostgreSQL and create database
psql -U postgres -c "CREATE DATABASE softmed_db;"
```

You'll be prompted for your PostgreSQL password.

**Method 2: Using psql with full path (if not in PATH)**

Find your PostgreSQL installation path (usually `C:\Program Files\PostgreSQL\15\bin\` or similar):

```powershell
# Replace '15' with your PostgreSQL version number
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE softmed_db;"
```

**Method 3: Using createdb command**

```powershell
# If createdb is in your PATH
createdb -U postgres softmed_db

# Or with full path
& "C:\Program Files\PostgreSQL\15\bin\createdb.exe" -U postgres softmed_db
```

**Method 4: Using Python Setup Script (Easiest - No psql needed)**

We've provided a setup script that handles everything:

```powershell
# Make sure you're in the backend directory and virtual environment is activated
cd D:\work-space\soft-med\backend
.\venv\Scripts\Activate.ps1

# Run the setup script
python setup_db.py
```

The script will:
- Prompt you for PostgreSQL connection details
- Create the database automatically
- Test the connection
- Generate the DATABASE_URL for your `.env` file

This is the **recommended method** if you don't have `psql` in your PATH.

#### Option B: Using pgAdmin (GUI)

1. **Open pgAdmin 4** (should be installed with PostgreSQL)

2. **Connect to PostgreSQL Server**:
   - In the left panel, expand "Servers"
   - Click on your PostgreSQL server (usually "PostgreSQL 15" or similar)
   - Enter your PostgreSQL password when prompted

3. **Create a New Database**:
   - Right-click on "Databases" → "Create" → "Database..."
   - In the "Database" field, enter: `softmed_db`
   - Click "Save"

#### Connection Details (for .env file)

- **Host**: `localhost` (or `127.0.0.1`)
- **Port**: `5432` (default PostgreSQL port)
- **Database**: `softmed_db`
- **Username**: Usually `postgres` (or your PostgreSQL username)
- **Password**: Your PostgreSQL password

### Step 2: Set Up Python Virtual Environment

Open PowerShell or Command Prompt in the `backend` directory:

```powershell
# Navigate to backend directory (if not already there)
cd D:\work-space\soft-med\backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again
```

**Note**: If you see `(venv)` at the beginning of your command prompt, the virtual environment is activated.

### Step 3: Install Dependencies

With the virtual environment activated:

```powershell
# Upgrade pip
python -m pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

This may take a few minutes. Wait for it to complete.

### Step 4: Create .env File

Create a `.env` file in the `backend` directory with the following content:

**Create the file**: `backend\.env`

```env
# Database Configuration
# Replace 'postgres' and 'your_password' with your actual PostgreSQL username and password
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/softmed_db

# JWT Authentication
# Generate a secret key (see below)
SECRET_KEY=your-secret-key-here-minimum-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Frontend URL (for password reset links)
FRONTEND_DOCTOR_BASE_URL=http://localhost:5173

# CORS Configuration (comma-separated list of allowed origins)
# Add all frontend URLs that need to access the API
# Example: CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
```

**To generate a secure SECRET_KEY**, run this in Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and replace `your-secret-key-here-minimum-32-characters-long` in your `.env` file.

### Step 4.5: Create Admin User (Optional)

To create your first admin user, run:

```powershell
python create_admin.py
```

The script will prompt you for:
- Email (required)
- Name (required)
- Password (required, will be confirmed)
- Role: `admin` or `superadmin` (default: admin)
- Phone (optional)
- CPF (optional)

**Note**: Make sure your `.env` file has the correct `DATABASE_URL` before running this script.

**Important**: Replace `your_password` in `DATABASE_URL` with your actual PostgreSQL password.

### Step 5: Run Database Migrations

With the virtual environment activated:

```powershell
# Run migrations to create all database tables
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade -> 3d3b78623bab, initial migration
INFO  [alembic.runtime.migration] Running upgrade 3d3b78623bab -> 7fa22ab23f85, add role to user
...
```

### Step 6: Start the Development Server

```powershell
# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 7: Verify It's Working

1. **Open your browser** and go to: http://localhost:8000
   - You should see: `{"message":"Hello World"}`

2. **View API Documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Test the API**:
   - Go to http://localhost:8000/docs
   - Try the `GET /` endpoint
   - Explore other endpoints in the interactive documentation

## Common Issues and Solutions

### Issue 1: "DATABASE_URL environment variable is not set"

**Solution**: Make sure you created the `.env` file in the `backend` directory and it contains `DATABASE_URL=...`

### Issue 2: "password authentication failed for user"

**Solution**: 
- Check your PostgreSQL password in the `.env` file
- Make sure you're using the correct username (usually `postgres`)
- Verify the password in pgAdmin by trying to connect

### Issue 3: "could not connect to server"

**Solution**:
- Make sure PostgreSQL service is running
- Check if the port is correct (default is 5432)
- Verify the host is `localhost` or `127.0.0.1`

### Issue 4: "database 'softmed_db' does not exist"

**Solution**: 
- Go back to Step 1 and create the database in pgAdmin
- Make sure the database name in `.env` matches the one you created

### Issue 5: Virtual environment activation fails

**Solution** (PowerShell):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating again:
```powershell
.\venv\Scripts\Activate.ps1
```

### Issue 6: Port 8000 already in use

**Solution**: Use a different port:
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Daily Usage

Once everything is set up, to start the backend:

1. **Open PowerShell** in the `backend` directory
2. **Activate virtual environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. **Start the server**:
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Stopping the Server

Press `Ctrl + C` in the terminal to stop the server.

## Next Steps

- Explore the API documentation at http://localhost:8000/docs
- Test creating a user via the `/users/` endpoint
- Test authentication via `/auth/token` endpoint
- Check the database tables in pgAdmin to see the data

## Optional: Install Redis (for Queue Management)

If you want to use the queue management features:

1. Download Redis for Windows: https://github.com/microsoftarchive/redis/releases
2. Install and start Redis
3. Add to your `.env` file:
   ```env
   REDIS_URL=redis://localhost:6379/0
   ```

## Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review the API documentation at http://localhost:8000/docs
- Check database tables in pgAdmin to verify data

