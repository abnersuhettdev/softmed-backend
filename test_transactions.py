"""Test script to diagnose transaction endpoint issues."""
import sys
from app.database import SessionLocal
from app.models.transaction import Transaction as TransactionModel

def test_transactions():
    """Test if we can query transactions from the database."""
    db = SessionLocal()
    try:
        print("Testing database connection...")
        
        # Try to query transactions
        transactions = db.query(TransactionModel).limit(5).all()
        print(f"Found {len(transactions)} transactions")
        
        if transactions:
            print("\nFirst transaction:")
            txn = transactions[0]
            print(f"  ID: {txn.id}")
            print(f"  date_time_str: {txn.date_time_str}")
            print(f"  invoice: {txn.invoice}")
            print(f"  description: {txn.description}")
            print(f"  total_value: {txn.total_value}")
            print(f"  available_balance: {txn.available_balance}")
            print(f"  blocked_balance: {txn.blocked_balance}")
        else:
            print("No transactions found in database (this is OK if the table is empty)")
        
        print("\nTest completed successfully!")
        return True
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_transactions()
    sys.exit(0 if success else 1)

