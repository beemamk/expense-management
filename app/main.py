from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

# Absolute imports targeting your current directory structure
from app.database import engine, Base, get_db
from app import models, schemas, auth

# Automatically generate database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Expense Management API")

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/register/", response_model=schemas.Token)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 1. Generate the hash exactly ONCE
    hashed_pwd = auth.get_password_hash(user_in.password)
    
    # 2. Pass the single hash directly to the database column mapping
    new_user = models.User(
        username=user_in.username, 
        hashed_password=hashed_pwd, 
        salary=user_in.salary
    )
    db.add(new_user)
    db.commit()
    
    token = auth.create_access_token(data={"sub": new_user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/token/", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# --- 1.2 CREATE EXPENSE REST API (SECURED) ---

@app.post("/expenses/", response_model=schemas.ExpenseResponse, status_code=201)
def create_expense(
    expense: schemas.ExpenseCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    db_expense = models.Expense(**expense.model_dump(), user_id=current_user.id)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


# --- 1.3 GET EXPENSES API (SECURED) ---

@app.get("/expenses/", response_model=list[schemas.ExpenseResponse])
def get_expenses(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Expense).filter(models.Expense.user_id == current_user.id).all()


# --- 1.4 ADVANCED FILTERING API ---

@app.get("/expenses/month/{year}/{month}/", response_model=list[schemas.ExpenseResponse])
def filter_by_month(
    year: int, month: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Expense).filter(
        models.Expense.user_id == current_user.id,
        func.strftime("%Y", models.Expense.created_at) == f"{year:04d}",
        func.strftime("%m", models.Expense.created_at) == f"{month:02d}"
    ).all()

@app.get("/expenses/filter/", response_model=list[schemas.ExpenseResponse])
def advanced_filter(
    period: str | None = None, # options: "day", "week", "month"
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.Expense).filter(models.Expense.user_id == current_user.id)
    
    if category:
        query = query.filter(models.Expense.category.ilike(category))
        
    if period:
        now = datetime.now(timezone.utc)
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=now.weekday()) # Monday start
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise HTTPException(status_code=400, detail="Invalid period string specified")
        query = query.filter(models.Expense.created_at >= start_date)
        
    return query.all()


# --- 1.5 TOTAL EXPENSE, SALARY & REMAINING AMOUNT API ---

@app.get("/totals/", response_model=schemas.TotalsResponse)
def get_totals(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    total_spent = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == current_user.id
    ).scalar() or 0.0
    
    return {
        "total_expense": total_spent,
        "total_salary": current_user.salary,
        "remaining_amount": current_user.salary - total_spent
    }