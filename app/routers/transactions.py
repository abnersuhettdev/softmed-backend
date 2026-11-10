from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
# --- SQLAlchemy Imports ---
from sqlalchemy.orm import Session

from app.database import \
    SessionLocal  # Assuming SessionLocal is defined in a app.database
# --- Local Imports ---
from app.models.transaction import Transaction as TransactionModel
from app.schemas.transaction import (FinancialSummary, Transaction,
                                     TransactionBase, TransactionCreate)

# Initialize the FastAPI router
router = APIRouter(
    responses={404: {"description": "Not found"}},
)


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Helper Function for Date Parsing ---


def parse_date_time_string(date_time_str: str) -> datetime:
    """Parses DD/MM/YYYY HH:MM string to a datetime object."""
    return datetime.strptime(date_time_str, "%d/%m/%Y %H:%M")


# Mock summary data (for now, until we implement complex summary calculations)
# This could be moved to a separate service layer later
mock_summary: FinancialSummary = FinancialSummary(
    available_financial_balance=1815.00,
    blocked_financial_balance=0.00,
    daily_attendances=66,
    monthly_attendances=158,
    my_rating=10.0,
    time_in_consultation_minutes=5.0,
)

# --- API Endpoints ---


@router.get("/summary", response_model=FinancialSummary, tags=["Summary"])
async def get_financial_summary():
    """Retrieve the overall financial summary and dashboard metrics."""
    # In a real app, this data would be calculated dynamically from the Transaction table.
    return mock_summary


@router.get("/", response_model=List[Transaction])
def get_financial_extract(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Retrieve a list of financial transaction entries, sorted newest first."""

    try:
        transactions = (
            db.query(TransactionModel)
            .order_by(TransactionModel.datetime_obj.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Map SQLAlchemy model to Pydantic schema
        # The schema expects 'date_time' but the model has 'date_time_str'
        result = []
        for txn in transactions:
            # Create Transaction schema instance with mapped fields
            result.append(Transaction(
                id=txn.id,
                date_time=txn.date_time_str,  # Map date_time_str to date_time
                invoice=txn.invoice,  # Can be None, schema allows Optional[str]
                description=txn.description,
                total_value=txn.total_value,
                available_balance=txn.available_balance,
                blocked_balance=txn.blocked_balance,
            ))
        
        return result
    except Exception as e:
        # Log the error for debugging
        import traceback
        error_msg = f"Error in get_financial_extract: {str(e)}"
        traceback_str = traceback.format_exc()
        print(error_msg)
        print(traceback_str)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{entry_id}", response_model=Transaction)
def get_transaction_entry(entry_id: int, db: Session = Depends(get_db)):
    """Retrieve a single financial transaction entry by its unique ID."""

    transaction = db.query(TransactionModel).filter(TransactionModel.id == entry_id).first()
    if not transaction:
        raise HTTPException(
            status_code=404, detail=f"Transaction entry with ID '{entry_id}' not found."
        )

    # Map SQLAlchemy model to Pydantic schema
    return Transaction(
        id=transaction.id,
        date_time=transaction.date_time_str,
        invoice=transaction.invoice,
        description=transaction.description,
        total_value=transaction.total_value,
        available_balance=transaction.available_balance,
        blocked_balance=transaction.blocked_balance,
    )


@router.post("/", response_model=Transaction, status_code=status.HTTP_201_CREATED)
def create_transaction_entry(entry: TransactionCreate, db: Session = Depends(get_db)):
    """Create a new financial transaction entry and persist it to PostgreSQL."""

    # 1. Validate and convert the Pydantic string date to a Python datetime object
    try:
        dt_object = parse_date_time_string(entry.date_time)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date_time format. Must be 'DD/MM/YYYY HH:MM'.",
        )

    # 2. Create the SQLAlchemy model instance
    new_transaction = TransactionModel(
        datetime_obj=dt_object,
        date_time_str=entry.date_time,
        invoice=entry.invoice,
        description=entry.description,
        total_value=entry.total_value,
        available_balance=entry.available_balance,
        blocked_balance=entry.blocked_balance,
    )

    # 3. Add and commit to database
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)

    # 4. Return the created entry, mapped back to the Pydantic response model
    return Transaction(
        id=new_transaction.id,
        date_time=new_transaction.date_time_str,
        invoice=new_transaction.invoice,
        description=new_transaction.description,
        total_value=new_transaction.total_value,
        available_balance=new_transaction.available_balance,
        blocked_balance=new_transaction.blocked_balance,
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a financial transaction entry by its unique ID from PostgreSQL."""

    transaction = db.query(TransactionModel).filter(TransactionModel.id == entry_id).first()
    if not transaction:
        raise HTTPException(
            status_code=404, detail=f"Transaction entry with ID '{entry_id}' not found."
        )

    db.delete(transaction)
    db.commit()

    return
