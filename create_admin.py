"""
Admin User Creation Script

This script allows you to create an admin or superadmin user in the database.
Run this script from the backend directory.

Usage:
    python create_admin.py
"""

import os
import sys
import getpass
from datetime import date

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.user import User, Role
from app.routers.users import get_password_hash

# Load environment variables
load_dotenv()


def create_admin():
    """Create an admin user interactively."""
    
    print("=" * 60)
    print("Admin User Creation Script")
    print("=" * 60)
    print()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env file!")
        print("Please make sure your .env file contains DATABASE_URL")
        sys.exit(1)
    
    print("Using database connection from .env file")
    print()
    print("=" * 60)
    print("Admin User Information")
    print("=" * 60)
    print()
    
    # Get admin details
    email = input("Email *: ").strip()
    if not email:
        print("Error: Email is required!")
        sys.exit(1)
    
    # Check if email already exists
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"\nError: User with email '{email}' already exists!")
            response = input("Do you want to update this user to admin? (y/N): ").strip().lower()
            if response != 'y':
                print("Cancelled.")
                sys.exit(0)
            # Update existing user
            print("\nUpdating existing user...")
            name = input(f"Name [{existing_user.name or 'N/A'}]: ").strip() or existing_user.name
            role_input = input("Role (admin/superadmin) [admin]: ").strip().lower() or "admin"
            
            if role_input not in ["admin", "superadmin"]:
                print("Error: Role must be 'admin' or 'superadmin'")
                sys.exit(1)
            
            role = Role.ADMIN if role_input == "admin" else Role.SUPERADMIN
            
            # Update password if provided
            update_password = input("Update password? (y/N): ").strip().lower() == 'y'
            if update_password:
                new_password = getpass.getpass("New password: ")
                if not new_password:
                    print("Error: Password cannot be empty!")
                    sys.exit(1)
                confirm_password = getpass.getpass("Confirm password: ")
                if new_password != confirm_password:
                    print("Error: Passwords do not match!")
                    sys.exit(1)
                existing_user.hashed_password = get_password_hash(new_password)
            
            existing_user.name = name
            existing_user.role = role
            existing_user.is_active = True
            
            db.commit()
            db.refresh(existing_user)
            
            print("\n" + "=" * 60)
            print("User Updated Successfully!")
            print("=" * 60)
            print(f"Email: {existing_user.email}")
            print(f"Name: {existing_user.name}")
            print(f"Role: {existing_user.role.value}")
            print(f"ID: {existing_user.id}")
            print()
            return
        
        # Create new user
        name = input("Name *: ").strip()
        if not name:
            print("Error: Name is required!")
            sys.exit(1)
        
        password = getpass.getpass("Password *: ")
        if not password:
            print("Error: Password is required!")
            sys.exit(1)
        
        confirm_password = getpass.getpass("Confirm password *: ")
        if password != confirm_password:
            print("Error: Passwords do not match!")
            sys.exit(1)
        
        role_input = input("Role (admin/superadmin) [admin]: ").strip().lower() or "admin"
        if role_input not in ["admin", "superadmin"]:
            print("Error: Role must be 'admin' or 'superadmin'")
            sys.exit(1)
        
        role = Role.ADMIN if role_input == "admin" else Role.SUPERADMIN
        
        # Optional fields
        print("\nOptional fields (press Enter to skip):")
        phone = input("Phone: ").strip() or None
        cpf = input("CPF: ").strip() or None
        
        # Check if CPF already exists
        if cpf:
            existing_cpf = db.query(User).filter(User.cpf == cpf).first()
            if existing_cpf:
                print(f"Warning: CPF '{cpf}' is already registered to another user.")
                use_cpf = input("Continue anyway? (y/N): ").strip().lower() == 'y'
                if not use_cpf:
                    cpf = None
        
        # Create the admin user
        hashed_password = get_password_hash(password)
        
        admin_user = User(
            email=email,
            name=name,
            hashed_password=hashed_password,
            role=role,
            is_active=True,
            phone=phone,
            cpf=cpf,
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("\n" + "=" * 60)
        print("Admin User Created Successfully!")
        print("=" * 60)
        print(f"Email: {admin_user.email}")
        print(f"Name: {admin_user.name}")
        print(f"Role: {admin_user.role.value}")
        print(f"ID: {admin_user.id}")
        print(f"Active: {admin_user.is_active}")
        if admin_user.phone:
            print(f"Phone: {admin_user.phone}")
        if admin_user.cpf:
            print(f"CPF: {admin_user.cpf}")
        print()
        print("You can now login with this account!")
        print()
        
    except Exception as e:
        db.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    try:
        create_admin()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

