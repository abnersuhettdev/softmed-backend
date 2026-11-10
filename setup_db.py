"""
Database Setup Script for SoftMed Backend

This script helps you create the database and verify the connection.
Run this script before starting the backend server.
"""

import os
import sys
import getpass
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def create_database():
    """Create the softmed_db database if it doesn't exist."""
    
    print("=" * 60)
    print("SoftMed Database Setup")
    print("=" * 60)
    
    # Get database connection details
    print("\nEnter PostgreSQL connection details:")
    host = input("Host [localhost]: ").strip() or "localhost"
    port = input("Port [5432]: ").strip() or "5432"
    user = input("Username [postgres]: ").strip() or "postgres"
    password = getpass.getpass("Password: ")
    database_name = "softmed_db"
    
    try:
        # Connect to PostgreSQL server (connect to 'postgres' database first)
        print(f"\nConnecting to PostgreSQL server at {host}:{port}...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres"  # Connect to default database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database already exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (database_name,)
        )
        exists = cur.fetchone()
        
        if exists:
            print(f"\n✓ Database '{database_name}' already exists!")
            response = input("Do you want to recreate it? (y/N): ").strip().lower()
            if response == 'y':
                # Terminate existing connections
                cur.execute(
                    sql.SQL("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()"),
                    (database_name,)
                )
                cur.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name)))
                print(f"✓ Dropped existing database '{database_name}'")
            else:
                print(f"✓ Using existing database '{database_name}'")
                cur.close()
                conn.close()
                return
        
        # Create the database
        print(f"\nCreating database '{database_name}'...")
        cur.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )
        print(f"✓ Database '{database_name}' created successfully!")
        
        cur.close()
        conn.close()
        
        # Test connection to the new database
        print(f"\nTesting connection to '{database_name}'...")
        test_conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database_name
        )
        test_conn.close()
        print("✓ Connection test successful!")
        
        # Generate DATABASE_URL for .env file
        database_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database_name}"
        
        print("\n" + "=" * 60)
        print("Database Setup Complete!")
        print("=" * 60)
        print(f"\nAdd this to your .env file:")
        print(f"DATABASE_URL={database_url}")
        print("\nNote: Make sure to keep your password secure!")
        
    except psycopg2.OperationalError as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your host, port, username, and password")
        print("3. Verify PostgreSQL service is started (Services app)")
        sys.exit(1)
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        create_database()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)

