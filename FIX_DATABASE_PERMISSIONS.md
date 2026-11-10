# Fix: Database Permission Denied Error

## Problem

The deployment is failing with this error:
```
psycopg2.errors.InsufficientPrivilege: permission denied for schema public
```

This occurs because the database user doesn't have sufficient privileges to create tables in the `public` schema.

## Solution

SSH into your Digital Ocean Droplet and run these commands:

```bash
# SSH into your Droplet
ssh root@your-droplet-ip

# Connect to PostgreSQL as the postgres superuser
sudo -u postgres psql

# Grant necessary privileges to your database user
# Replace 'softmed_user' with your actual database username
GRANT ALL PRIVILEGES ON DATABASE softmed_db TO softmed_user;
\c softmed_db
GRANT ALL ON SCHEMA public TO softmed_user;
GRANT CREATE ON SCHEMA public TO softmed_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO softmed_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO softmed_user;

# If the user needs to create the schema (for PostgreSQL 15+)
ALTER USER softmed_user CREATEDB;

# Exit PostgreSQL
\q
```

## Alternative: Make user owner of the database

If you want to give full ownership:

```bash
sudo -u postgres psql

ALTER DATABASE softmed_db OWNER TO softmed_user;
\c softmed_db
ALTER SCHEMA public OWNER TO softmed_user;

\q
```

## Verify Permissions

After granting permissions, verify they work:

```bash
# Test connection and permissions
sudo -u postgres psql -d softmed_db -U softmed_user -c "CREATE TABLE test_table (id SERIAL PRIMARY KEY); DROP TABLE test_table;"
```

If this command succeeds, permissions are correctly configured.

## After Fixing

1. Re-run the deployment workflow
2. The migrations should now run successfully

## For PostgreSQL 15+

If you're using PostgreSQL 15 or newer, the `public` schema permissions are more restricted by default. You may also need to:

```bash
sudo -u postgres psql

# Grant usage and create on public schema
\c softmed_db
GRANT USAGE ON SCHEMA public TO softmed_user;
GRANT CREATE ON SCHEMA public TO softmed_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO softmed_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO softmed_user;

\q
```

## Quick One-Liner

Here's a quick command you can run all at once:

```bash
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE softmed_db TO softmed_user;" -c "\c softmed_db" -c "GRANT ALL ON SCHEMA public TO softmed_user;" -c "GRANT CREATE ON SCHEMA public TO softmed_user;" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO softmed_user;" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO softmed_user;"
```

