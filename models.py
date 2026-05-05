from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    DECIMAL,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RoleEnum(PyEnum):
    admin = "admin"
    executive = "executive"
    employee = "employee"


class PriorityEnum(PyEnum):
    low = "low"
    medium = "medium"
    high = "high"


class StatusEnum(PyEnum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class PlatformEnum(PyEnum):
    instagram = "instagram"
    linkedin = "linkedin"
    youtube = "youtube"
    tiktok = "tiktok"
    facebook = "facebook"
    x = "x"


class TransactionTypeEnum(PyEnum):
    income = "income"
    expense = "expense"


class FinanceCategoryEnum(PyEnum):
    operations = "operations"
    salaries = "salaries"
    marketing = "marketing"
    utilities = "utilities"
    supplies = "supplies"
    other = "other"


class NotificationTypeEnum(PyEnum):
    task = "task"
    event = "event"
    content = "content"
    finance = "finance"
    general = "general"


class ThemeEnum(PyEnum):
    light = "light"
    dark = "dark"


class LanguageEnum(PyEnum):
    en = "en"
    fr = "fr"
    es = "es"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(
        Enum(
            RoleEnum,
            name="role_enum",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
        default=RoleEnum.employee,
        server_default="employee",
    )
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login = Column(DateTime(timezone=True), nullable=True)

    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assigned_to")
    tasks_created = relationship("Task", foreign_keys="Task.assigned_by_id", back_populates="assigned_by")
    events_created = relationship("Event", back_populates="created_by")
    content_created = relationship("Content", back_populates="created_by")
    transactions_recorded = relationship("Transaction", back_populates="recorded_by")
    contributions = relationship(
        "Contribution",
        foreign_keys="Contribution.author_id",
        back_populates="author",
    )
    contributions_flagged = relationship(
        "Contribution",
        foreign_keys="Contribution.flagged_by_id",
        back_populates="flagged_by",
    )
    notifications = relationship("Notification", back_populates="user")
    settings = relationship("UserSettings", uselist=False, back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(
        Enum(PriorityEnum, name="priority_enum", native_enum=False),
        nullable=False,
        default=PriorityEnum.medium,
        server_default="medium",
    )
    status = Column(
        Enum(StatusEnum, name="status_enum", native_enum=True),
        nullable=False,
        default=StatusEnum.pending,
        server_default="pending",
    )
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    deadline = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="tasks_assigned")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id], back_populates="tasks_created")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    organizer = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_by = relationship("User", back_populates="events_created")


class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    platform = Column(
        Enum(PlatformEnum, name="platform_enum", native_enum=False),
        nullable=False,
    )
    post_date = Column(Date, nullable=False)
    review_time = Column(Time, nullable=False)
    organizer = Column(String(255), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_by = relationship("User", back_populates="content_created")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(
        Enum(TransactionTypeEnum, name="transaction_type_enum", native_enum=False),
        nullable=False,
    )
    client_name = Column(String(255), nullable=True)
    amount = Column(DECIMAL(15, 2), nullable=False)
    payment_date = Column(Date, nullable=True)
    payment_details = Column(Text, nullable=True)
    category = Column(
        Enum(FinanceCategoryEnum, name="finance_category_enum", native_enum=False),
        nullable=True,
    )
    recipient_vendor = Column(String(255), nullable=True)
    expense_date = Column(Date, nullable=True)
    expense_details = Column(Text, nullable=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    recorded_by = relationship("User", back_populates="transactions_recorded")


class Income(Base):
    __tablename__ = "income"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_name = Column(String(255), nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    date_paid = Column(Date, nullable=False)
    payment_details = Column(Text, nullable=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    recorded_by = relationship("User")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(
        Enum(FinanceCategoryEnum, name="expense_category_enum", native_enum=False),
        nullable=False,
    )
    amount = Column(DECIMAL(15, 2), nullable=False)
    date_spent = Column(Date, nullable=False)
    recipient_vendor = Column(String(255), nullable=False)
    expense_details = Column(Text, nullable=True)
    recorded_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    recorded_by = relationship("User")


class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=False)
    is_flagged = Column(Boolean, nullable=False, default=False, server_default="false")
    flagged_reason = Column(String(255), nullable=True)
    flagged_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    author = relationship("User", foreign_keys=[author_id], back_populates="contributions")
    flagged_by = relationship("User", foreign_keys=[flagged_by_id], back_populates="contributions_flagged")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(
        Enum(NotificationTypeEnum, name="notification_type_enum", native_enum=False),
        nullable=False,
        default=NotificationTypeEnum.general,
        server_default="general",
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, server_default="false")
    related_item_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="notifications")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    notification_email_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    notification_push_enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    theme = Column(
        Enum(ThemeEnum, name="theme_enum", native_enum=False),
        nullable=False,
        default=ThemeEnum.light,
        server_default="light",
    )
    language = Column(
        Enum(LanguageEnum, name="language_enum", native_enum=False),
        nullable=False,
        default=LanguageEnum.en,
        server_default="en",
    )
    timezone = Column(String(50), nullable=False, default="UTC", server_default="UTC")
    dashboard_layout = Column(String(50), nullable=False, default="default", server_default="default")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user = relationship("User", back_populates="settings")
