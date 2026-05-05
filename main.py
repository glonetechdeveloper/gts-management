import os
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Response, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session

from database import SessionLocal, init_db
from models import (
    Content,
    Contribution,
    Event,
    Expense,
    FinanceCategoryEnum,
    Income,
    LanguageEnum,
    Notification,
    NotificationTypeEnum,
    PlatformEnum,
    PriorityEnum,
    RoleEnum,
    StatusEnum,
    Task,
    ThemeEnum,
    Transaction,
    TransactionTypeEnum,
    User,
    UserSettings,
)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()

app = FastAPI(title="GloneTech Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    phone: Optional[str] = None
    department: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    confirm_password: str

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[str] = "employee"
    phone: Optional[str] = None
    department: Optional[str] = None

    @validator("role")
    def validate_role(cls, v):
        if v not in {"admin", "executive", "employee"}:
            raise ValueError("Invalid role")
        return v


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None

    @validator("role")
    def validate_role(cls, v):
        if v is not None and v not in {"admin", "executive", "employee"}:
            raise ValueError("Invalid role")
        return v


class TransactionCreateRequest(BaseModel):
    client_name: Optional[str] = None
    amount: float
    payment_date: Optional[date] = None
    payment_details: Optional[str] = None
    category: Optional[str] = None
    recipient_vendor: Optional[str] = None
    expense_date: Optional[date] = None
    expense_details: Optional[str] = None


class TransactionUpdateRequest(BaseModel):
    client_name: Optional[str] = None
    amount: Optional[float] = None
    payment_date: Optional[date] = None
    payment_details: Optional[str] = None
    category: Optional[str] = None
    recipient_vendor: Optional[str] = None
    expense_date: Optional[date] = None
    expense_details: Optional[str] = None


class EventCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    date: "date"
    time: "time"
    location: Optional[str] = None
    organizer: Optional[str] = None


class EventUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    date: Optional["date"] = None
    time: Optional["time"] = None
    location: Optional[str] = None
    organizer: Optional[str] = None


class ContentCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    platform: PlatformEnum
    post_date: date
    review_time: time
    organizer: Optional[str] = None


class ContentUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[PlatformEnum] = None
    post_date: Optional[date] = None
    review_time: Optional[time] = None
    organizer: Optional[str] = None


class ContributionCreateRequest(BaseModel):
    message: str


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = PriorityEnum.medium
    assigned_to_id: int
    deadline: Optional[date] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None
    assigned_to_id: Optional[int] = None
    deadline: Optional[date] = None


class FlagContributionRequest(BaseModel):
    reason: str


class SettingsUpdateRequest(BaseModel):
    notification_email_enabled: Optional[bool] = None
    notification_push_enabled: Optional[bool] = None
    theme: Optional[ThemeEnum] = None
    language: Optional[LanguageEnum] = None
    timezone: Optional[str] = None
    dashboard_layout: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_task(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value,
        "status": task.status.value,
        "assigned_to": {
            "id": task.assigned_to.id,
            "name": task.assigned_to.full_name,
        },
        "assigned_by": {
            "id": task.assigned_by.id,
            "name": task.assigned_by.full_name,
        },
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


def serialize_event(event: Event) -> dict:
    return {
        "id": event.id,
        "name": event.name,
        "description": event.description,
        "date": event.date.isoformat(),
        "time": event.time.isoformat(),
        "organizer": event.organizer,
        "location": event.location,
        "created_by": {
            "id": event.created_by.id,
            "name": event.created_by.full_name,
        },
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def serialize_content(item: Content) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "platform": item.platform.value,
        "post_date": item.post_date.isoformat(),
        "review_time": item.review_time.isoformat(),
        "organizer": item.organizer,
        "created_by": {
            "id": item.created_by.id,
            "name": item.created_by.full_name,
        },
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def serialize_contribution(contrib: Contribution) -> dict:
    return {
        "id": contrib.id,
        "author": {
            "id": contrib.author.id,
            "name": contrib.author.full_name,
            "initials": "".join([name_part[0] for name_part in contrib.author.full_name.split()]) if contrib.author.full_name else None,
        },
        "message": contrib.message,
        "is_flagged": contrib.is_flagged,
        "flagged_reason": contrib.flagged_reason,
        "created_at": contrib.created_at.isoformat() if contrib.created_at else None,
    }


def serialize_notification(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "type": notification.type.value,
        "title": notification.title,
        "message": notification.message,
        "is_read": notification.is_read,
        "related_item_id": notification.related_item_id,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def serialize_transaction(transaction: Transaction) -> dict:
    return {
        "id": transaction.id,
        "type": transaction.type.value,
        "client_name": transaction.client_name,
        "amount": str(transaction.amount),
        "payment_date": transaction.payment_date.isoformat() if transaction.payment_date else None,
        "payment_details": transaction.payment_details,
        "category": transaction.category.value if transaction.category else None,
        "recipient_vendor": transaction.recipient_vendor,
        "expense_date": transaction.expense_date.isoformat() if transaction.expense_date else None,
        "expense_details": transaction.expense_details,
        "recorded_by": {
            "id": transaction.recorded_by.id,
            "name": transaction.recorded_by.full_name,
        },
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
    }


def serialize_settings(settings: UserSettings) -> dict:
    return {
        "notification_email_enabled": settings.notification_email_enabled,
        "notification_push_enabled": settings.notification_push_enabled,
        "theme": settings.theme.value,
        "language": settings.language.value,
        "timezone": settings.timezone,
        "dashboard_layout": settings.dashboard_layout,
    }


def get_or_create_user_settings(db: Session, user: User) -> UserSettings:
    settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
    return pwd_context.hash(password[:72])


def create_token(data: dict, expires_delta: timedelta, token_type: str) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + expires_delta
    payload.update({"exp": expire, "type": token_type})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user: User) -> str:
    return create_token({"sub": str(user.id)}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user: User) -> str:
    return create_token({"sub": str(user.id)}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or missing user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*roles: str):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return role_checker


def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "phone": user.phone,
        "department": user.department,
    }


def create_initial_users(db: Session) -> None:
    users = [
        {"email": "joseph@glonetech.com", "password": "admin123", "full_name": "Joseph Prince", "role": RoleEnum.admin},
        {"email": "saka@glonetech.com", "password": "admin123", "full_name": "Saka Ola", "role": RoleEnum.admin},
        {"email": "david@glonetech.com", "password": "emp123", "full_name": "David Praise", "role": RoleEnum.executive},
        {"email": "smk@glonetech.com", "password": "emp123", "full_name": "SMK", "role": RoleEnum.executive},
        {"email": "precious@glonetech.com", "password": "emp123", "full_name": "Precious", "role": RoleEnum.executive},
    ]

    for user_data in users:
        if not get_user_by_email(db, user_data["email"]):
            user = User(
                full_name=user_data["full_name"],
                email=user_data["email"].lower(),
                password_hash=get_password_hash(user_data["password"]),
                role=user_data["role"],
            )
            db.add(user)
    db.commit()


@app.on_event("startup")
def startup_event():
    init_db()
    db = SessionLocal()
    try:
        create_initial_users(db)
    finally:
        db.close()


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user.last_login = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return {
        "success": True,
        "message": "Login successful",
        "token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_to_dict(user),
    }


@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> dict:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role=RoleEnum.employee,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return {
        "success": True,
        "message": "Account created successfully",
        "token": access_token,
        "refresh_token": refresh_token,
        "user": user_to_dict(user),
    }


@app.post("/api/auth/logout")
def logout(current_user: User = Depends(get_current_user)) -> dict:
    return {"success": True, "message": "Logged out successfully"}


@app.post("/api/auth/refresh")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> dict:
    try:
        token_data = jwt.decode(payload.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if token_data.get("type") != "refresh":
            raise JWTError("Invalid token type")
        user_id = int(token_data.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return {
        "success": True,
        "message": "Token refreshed successfully",
        "token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/api/users")
def list_users(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    users = db.query(User).all()
    return {
        "success": True,
        "data": [user_to_dict(user) for user in users],
    }


@app.post("/api/users")
def create_user(
    payload: CreateUserRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        password_hash=get_password_hash(payload.password),
        role=RoleEnum(payload.role),
        phone=payload.phone,
        department=payload.department,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User created successfully",
        "data": {"user": user_to_dict(user)},
    }


@app.put("/api/users/{user_id}")
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email.lower()
    if payload.password is not None:
        user.password_hash = get_password_hash(payload.password)
    if payload.role is not None:
        user.role = RoleEnum(payload.role)
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.department is not None:
        user.department = payload.department
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User updated successfully",
        "data": {"user": user_to_dict(user)},
    }


@app.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()

    return {"success": True, "message": "User deleted successfully"}


@app.get("/api/finance")
def get_finance(
    type: Optional[str] = None,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    income_query = db.query(Income)
    expense_query = db.query(Expense)

    if type == "income":
        income_query = income_query.order_by(Income.date_paid.desc())
        incomes = income_query.all()
        return {
            "success": True,
            "stats": {
                "total_income": sum(float(item.amount) for item in incomes),
                "total_expenses": 0,
                "net_balance": sum(float(item.amount) for item in incomes),
                "total_transactions": len(incomes),
            },
            "data": {"income": [
                {
                    "id": item.id,
                    "client_name": item.client_name,
                    "amount": float(item.amount),
                    "date_paid": item.date_paid.isoformat(),
                    "payment_details": item.payment_details,
                }
                for item in incomes
            ], "expenses": []},
        }

    if type == "expense":
        expense_query = expense_query.order_by(Expense.date_spent.desc())
        expenses = expense_query.all()
        return {
            "success": True,
            "stats": {
                "total_income": 0,
                "total_expenses": sum(float(item.amount) for item in expenses),
                "net_balance": -sum(float(item.amount) for item in expenses),
                "total_transactions": len(expenses),
            },
            "data": {"income": [], "expenses": [
                {
                    "id": item.id,
                    "category": item.category.value,
                    "amount": float(item.amount),
                    "date_spent": item.date_spent.isoformat(),
                    "recipient_vendor": item.recipient_vendor,
                    "expense_details": item.expense_details,
                }
                for item in expenses
            ]},
        }

    incomes = income_query.order_by(Income.date_paid.desc()).all()
    expenses = expense_query.order_by(Expense.date_spent.desc()).all()
    total_income = sum(float(item.amount) for item in incomes)
    total_expenses = sum(float(item.amount) for item in expenses)
    return {
        "success": True,
        "stats": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_balance": total_income - total_expenses,
            "total_transactions": len(incomes) + len(expenses),
        },
        "data": {
            "income": [
                {
                    "id": item.id,
                    "client_name": item.client_name,
                    "amount": float(item.amount),
                    "date_paid": item.date_paid.isoformat(),
                    "payment_details": item.payment_details,
                }
                for item in incomes
            ],
            "expenses": [
                {
                    "id": item.id,
                    "category": item.category.value,
                    "amount": float(item.amount),
                    "date_spent": item.date_spent.isoformat(),
                    "recipient_vendor": item.recipient_vendor,
                    "expense_details": item.expense_details,
                }
                for item in expenses
            ],
        },
    }


@app.post("/api/finance/income", status_code=status.HTTP_201_CREATED)
def create_income(
    payload: TransactionCreateRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    income = Income(
        client_name=payload.client_name or "",
        amount=payload.amount,
        date_paid=payload.payment_date or datetime.utcnow().date(),
        payment_details=payload.payment_details,
        recorded_by_id=current_user.id,
    )
    db.add(income)
    db.commit()
    db.refresh(income)
    return {"success": True, "message": "Income recorded successfully", "data": {
        "id": income.id,
        "client_name": income.client_name,
        "amount": float(income.amount),
        "date_paid": income.date_paid.isoformat(),
        "payment_details": income.payment_details,
    }}


@app.post("/api/finance/expense", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: TransactionCreateRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    if not payload.category:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category is required for expenses")
    expense = Expense(
        category=FinanceCategoryEnum(payload.category),
        amount=payload.amount,
        date_spent=payload.expense_date or datetime.utcnow().date(),
        recipient_vendor=payload.recipient_vendor or "",
        expense_details=payload.expense_details,
        recorded_by_id=current_user.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return {"success": True, "message": "Expense recorded successfully", "data": {
        "id": expense.id,
        "category": expense.category.value,
        "amount": float(expense.amount),
        "date_spent": expense.date_spent.isoformat(),
        "recipient_vendor": expense.recipient_vendor,
        "expense_details": expense.expense_details,
    }}


@app.put("/api/finance/income/{income_id}")
def update_income(
    income_id: int,
    payload: TransactionUpdateRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    income = db.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income record not found")

    if payload.client_name is not None:
        income.client_name = payload.client_name
    if payload.amount is not None:
        income.amount = payload.amount
    if payload.payment_date is not None:
        income.date_paid = payload.payment_date
    if payload.payment_details is not None:
        income.payment_details = payload.payment_details

    db.add(income)
    db.commit()
    return {"success": True, "message": "Income updated successfully"}


@app.put("/api/finance/expense/{expense_id}")
def update_expense(
    expense_id: int,
    payload: TransactionUpdateRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense record not found")

    if payload.category is not None:
        expense.category = FinanceCategoryEnum(payload.category)
    if payload.amount is not None:
        expense.amount = payload.amount
    if payload.expense_date is not None:
        expense.date_spent = payload.expense_date
    if payload.recipient_vendor is not None:
        expense.recipient_vendor = payload.recipient_vendor
    if payload.expense_details is not None:
        expense.expense_details = payload.expense_details

    db.add(expense)
    db.commit()
    return {"success": True, "message": "Expense updated successfully"}


@app.delete("/api/finance/income/{income_id}")
def delete_income(
    income_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Response:
    income = db.get(Income, income_id)
    if not income:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income record not found")
    db.delete(income)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/api/finance/expense/{expense_id}")
def delete_expense(
    expense_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Response:
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense record not found")
    db.delete(expense)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/admin/contributions")
def list_contributions_admin(
    status: Optional[str] = None,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Contribution).order_by(Contribution.created_at.desc())
    if status == "flagged":
        query = query.filter(Contribution.is_flagged.is_(True))

    contributions = query.all()
    return {
        "success": True,
        "message": "Contributions retrieved successfully",
        "data": [serialize_contribution(contrib) for contrib in contributions],
    }


@app.get("/api/contributions")
def list_contributions(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    contributions = (
        db.query(Contribution)
        .order_by(Contribution.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return {"success": True, "data": [serialize_contribution(item) for item in contributions]}


@app.post("/api/contributions", status_code=status.HTTP_201_CREATED)
def create_contribution(
    payload: ContributionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    contribution = Contribution(
        author_id=current_user.id,
        message=payload.message,
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return {"success": True, "message": "Contribution posted successfully", "data": serialize_contribution(contribution)}


@app.delete("/api/contributions/{contribution_id}")
def delete_contribution(
    contribution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    contribution = db.get(Contribution, contribution_id)
    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")
    if contribution.author_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this contribution")

    db.delete(contribution)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.put("/api/admin/contributions/{contribution_id}/flag")
def flag_contribution(
    contribution_id: int,
    payload: FlagContributionRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    contribution = db.get(Contribution, contribution_id)
    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")

    contribution.is_flagged = True
    contribution.flagged_reason = payload.reason
    contribution.flagged_by_id = current_user.id
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return {"success": True, "message": "Contribution flagged successfully", "data": serialize_contribution(contribution)}


@app.put("/api/admin/contributions/{contribution_id}/approve")
def approve_contribution(
    contribution_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    contribution = db.get(Contribution, contribution_id)
    if not contribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")
    if not contribution.is_flagged:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution is not flagged")

    contribution.is_flagged = False
    contribution.flagged_reason = None
    contribution.flagged_by_id = None
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return {"success": True, "message": "Contribution approved successfully", "data": serialize_contribution(contribution)}


@app.get("/api/dashboard")
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    task_count = db.query(Task).filter(Task.assigned_to_id == current_user.id).count()
    event_count = db.query(Event).count()
    content_count = db.query(Content).count()
    contribution_count = db.query(Contribution).count()

    return {
        "success": True,
        "data": {
            "task_count": task_count,
            "event_count": event_count,
            "content_count": content_count,
            "contribution_count": contribution_count,
        },
    }


@app.get("/api/notifications")
def list_notifications(
    unread: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread is not None:
        query = query.filter(Notification.is_read.is_(not unread))

    notifications = query.order_by(Notification.created_at.desc()).all()
    return {
        "success": True,
        "unread_count": db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read.is_(False)).count(),
        "data": [serialize_notification(item) for item in notifications],
    }


@app.put("/api/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    db.add(notification)
    db.commit()
    return {"success": True, "message": "Notification marked as read"}


@app.put("/api/notifications/read-all")
def read_all_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"success": True, "message": "All notifications marked as read"}


@app.get("/api/notifications/count")
def notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    count = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read.is_(False)).count()
    return {"unread_count": count}


@app.get("/api/settings")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    settings = get_or_create_user_settings(db, current_user)
    return {"success": True, "data": serialize_settings(settings)}


@app.put("/api/settings")
def update_settings(
    payload: SettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    settings = get_or_create_user_settings(db, current_user)
    if payload.notification_email_enabled is not None:
        settings.notification_email_enabled = payload.notification_email_enabled
    if payload.notification_push_enabled is not None:
        settings.notification_push_enabled = payload.notification_push_enabled
    if payload.theme is not None:
        settings.theme = ThemeEnum(payload.theme)
    if payload.language is not None:
        settings.language = LanguageEnum(payload.language)
    if payload.timezone is not None:
        settings.timezone = payload.timezone
    if payload.dashboard_layout is not None:
        settings.dashboard_layout = payload.dashboard_layout

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return {"success": True, "message": "Settings updated successfully", "data": serialize_settings(settings)}


@app.get("/api/profile")
def get_profile(current_user: User = Depends(get_current_user)) -> dict:
    profile_data = user_to_dict(current_user)
    profile_data["created_at"] = current_user.created_at.isoformat() if current_user.created_at else None
    return {"success": True, "data": profile_data}


@app.put("/api/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.department is not None:
        current_user.department = payload.department

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"success": True, "message": "Profile updated successfully", "data": user_to_dict(current_user)}


@app.get("/api/tasks")
def list_tasks(
    status: Optional[StatusEnum] = None,
    priority: Optional[PriorityEnum] = None,
    assigned_to: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Task)

    if current_user.role.value not in {"admin", "executive"}:
        query = query.filter(Task.assigned_to_id == current_user.id)

    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to:
        query = query.filter(Task.assigned_to_id == assigned_to)

    tasks = query.order_by(Task.created_at.desc()).all()
    return {"success": True, "data": [serialize_task(task) for task in tasks]}


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    assigned_to = get_user_by_id(db, payload.assigned_to_id)
    if not assigned_to:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")

    task = Task(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        assigned_to_id=payload.assigned_to_id,
        assigned_by_id=current_user.id,
        deadline=payload.deadline,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"success": True, "message": "Task created successfully", "data": serialize_task(task)}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.role.value not in {"admin", "executive"} and task.assigned_to_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this task")

    return {"success": True, "data": serialize_task(task)}


@app.put("/api/tasks/{task_id}")
def update_task(
    task_id: int,
    payload: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user.role.value not in {"admin", "executive"} and task.assigned_to_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this task")

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.status is not None:
        task.status = payload.status
    if payload.deadline is not None:
        task.deadline = payload.deadline
    if payload.assigned_to_id is not None:
        if current_user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can reassign tasks")
        if not get_user_by_id(db, payload.assigned_to_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
        task.assigned_to_id = payload.assigned_to_id

    db.add(task)
    db.commit()
    db.refresh(task)
    return {"success": True, "message": "Task updated successfully", "data": serialize_task(task)}


@app.put("/api/tasks/{task_id}/begin")
def begin_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.assigned_to_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assigned user can begin this task")
    if task.status != StatusEnum.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not pending")

    task.status = StatusEnum.in_progress
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"success": True, "message": "Task status updated to in-progress", "data": serialize_task(task)}


@app.put("/api/tasks/{task_id}/complete")
def complete_task(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.assigned_to_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only assigned user can complete this task")
    if task.status == StatusEnum.completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is already completed")

    task.status = StatusEnum.completed
    db.add(task)
    db.commit()
    return {"success": True, "message": "Task marked as completed"}


@app.delete("/api/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Response:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/events")
def list_events(
    days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Event)
    if days is not None:
        today = datetime.utcnow().date()
        end_date = today + timedelta(days=days)
        query = query.filter(Event.date >= today, Event.date <= end_date)

    events = query.order_by(Event.date.asc()).all()
    serialized_events = [serialize_event(event) for event in events]
    return {"success": True, "data": serialized_events, "events": serialized_events}


@app.post("/api/events", status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    event = Event(
        name=payload.name,
        description=payload.description,
        date=payload.date,
        time=payload.time,
        organizer=payload.organizer or current_user.full_name,
        location=payload.location,
        created_by_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"success": True, "message": "Event created successfully", "data": serialize_event(event)}


@app.put("/api/events/{event_id}")
def update_event(
    event_id: int,
    payload: EventUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.created_by_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this event")

    if payload.name is not None:
        event.name = payload.name
    if payload.description is not None:
        event.description = payload.description
    if payload.date is not None:
        event.date = payload.date
    if payload.time is not None:
        event.time = payload.time
    if payload.location is not None:
        event.location = payload.location
    if payload.organizer is not None:
        event.organizer = payload.organizer

    db.add(event)
    db.commit()
    db.refresh(event)
    return {"success": True, "message": "Event updated successfully", "data": serialize_event(event)}


@app.delete("/api/events/{event_id}")
def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    if event.created_by_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this event")

    db.delete(event)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/content")
def list_content(
    platform: Optional[List[PlatformEnum]] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Content)
    if platform:
        query = query.filter(Content.platform.in_(platform))

    content_items = query.order_by(Content.post_date.asc()).all()
    return {"success": True, "data": [serialize_content(item) for item in content_items]}


@app.post("/api/content", status_code=status.HTTP_201_CREATED)
def create_content(
    payload: ContentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    content_item = Content(
        title=payload.title,
        description=payload.description,
        platform=PlatformEnum(payload.platform),
        post_date=payload.post_date,
        review_time=payload.review_time,
        organizer=payload.organizer or current_user.full_name,
        created_by_id=current_user.id,
    )
    db.add(content_item)
    db.commit()
    db.refresh(content_item)
    return {"success": True, "message": "Content created successfully", "data": serialize_content(content_item)}


@app.put("/api/content/{content_id}")
def update_content(
    content_id: int,
    payload: ContentUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    content_item = db.get(Content, content_id)
    if not content_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if content_item.created_by_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this content")

    if payload.title is not None:
        content_item.title = payload.title
    if payload.description is not None:
        content_item.description = payload.description
    if payload.platform is not None:
        content_item.platform = PlatformEnum(payload.platform)
    if payload.post_date is not None:
        content_item.post_date = payload.post_date
    if payload.review_time is not None:
        content_item.review_time = payload.review_time
    if payload.organizer is not None:
        content_item.organizer = payload.organizer

    db.add(content_item)
    db.commit()
    db.refresh(content_item)
    return {"success": True, "message": "Content updated successfully", "data": serialize_content(content_item)}


@app.delete("/api/content/{content_id}")
def delete_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    content_item = db.get(Content, content_id)
    if not content_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if content_item.created_by_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this content")

    db.delete(content_item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
