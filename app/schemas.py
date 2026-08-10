from pydantic import BaseModel, Field
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    salary: float = 5000.0

class Token(BaseModel):
    access_token: str
    token_type: str

class ExpenseCreate(BaseModel):
    name: str = Field(..., examples=["Gym Membership"])
    amount: float = Field(..., gt=0, examples=[50.0])
    category: str = Field(..., examples=["Health"])

class ExpenseResponse(BaseModel):
    expense_id: int = Field(..., alias="id")
    name: str
    amount: float
    category: str
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class TotalsResponse(BaseModel):
    total_expense: float
    total_salary: float
    remaining_amount: float