from typing import Optional, Any

from pydantic import BaseModel, Field, model_validator

# --- Transaction Schemas ---


class TransactionBase(BaseModel):
    """Base schema for a single financial transaction entry."""

    # Data is expected in the string format "DD/MM/YYYY HH:MM"
    date_time: str = Field(
        ...,
        example="28/10/2025 23:39",
        description="Date and time of the transaction (DD/MM/YYYY HH:MM)",
    )
    invoice: Optional[str] = Field(
        None, example="", description="Invoice number (Fatura). Can be empty."
    )
    description: str = Field(
        ...,
        example="Crédito por atendimento concluído no pronto-atendimento",
        description="Description of the transaction (Descrição)",
    )
    total_value: float = Field(
        ...,
        ge=0,  # Changed from gt=0 to ge=0 to allow 0 values
        example=15.00,
        description="Total value of the transaction (Valor Total) in R$",
    )
    available_balance: float = Field(
        ...,
        ge=0,
        example=15.00,
        description="Available balance attributed to this transaction (Saldo Disponível) in R$",
    )
    blocked_balance: float = Field(
        ...,
        ge=0,
        example=0.00,
        description="Blocked balance attributed to this transaction (Saldo Bloqueado) in R$",
    )


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""

    pass


class Transaction(TransactionBase):
    """Schema for transaction entry fetched from the DB (response model)."""

    id: int = Field(..., description="Unique identifier for the transaction")

    class Config:
        # Allows mapping SQLAlchemy object attributes directly to Pydantic fields
        from_attributes = True


# --- Dashboard Schemas ---


class FinancialSummary(BaseModel):
    """Model for the overall financial summary and dashboard metrics."""

    available_financial_balance: float = Field(
        ...,
        ge=0,
        example=1815.00,
        description="Overall available financial balance (Saldo Disponível) in R$",
    )
    blocked_financial_balance: float = Field(
        ...,
        ge=0,
        example=0.00,
        description="Overall blocked financial balance (Saldo Bloqueiro) in R$",
    )
    daily_attendances: int = Field(
        ...,
        ge=0,
        example=66,
        description="Number of daily attendances (Atendimentos Diários)",
    )
    monthly_attendances: int = Field(
        ...,
        ge=0,
        example=158,
        description="Number of monthly attendances (Atendimentos Mensais)",
    )
    my_rating: float = Field(
        ..., ge=0, le=10.0, example=10.0, description="User's rating (Minha Avaliação)"
    )
    time_in_consultation_minutes: float = Field(
        ...,
        ge=0,
        example=5.0,
        description="Average time in consultation (Tempo em Consulta) in minutes",
    )
