from sqlalchemy import Column, DateTime, Float, Integer, String

from app.database import Base


class Transaction(Base):
    """
    SQLAlchemy model for the 'transactions' table in the PostgreSQL database.
    This defines the physical structure of the table.
    """

    __tablename__ = "transactions"

    # Primary Key, auto-incrementing integer
    id = Column(Integer, primary_key=True, index=True)

    # Store date/time as a proper DateTime object for correct database sorting and querying
    datetime_obj = Column("date_time_db", DateTime, index=True, nullable=False)

    # Keep the original string format for display purposes (matches user input/output)
    date_time_str = Column("date_time", String, nullable=False)

    invoice = Column(String, nullable=True)
    description = Column(String, nullable=False)
    total_value = Column(Float, nullable=False)
    available_balance = Column(Float, nullable=False)
    blocked_balance = Column(Float, nullable=False)
