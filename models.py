import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)
    balance = Column(Float, default=0.0, nullable=False)
    currency = Column(String(8), default="INR", nullable=False)  # 'INR' or 'USD'
    is_banned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="seller", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    payout_requests = relationship("PayoutRequest", back_populates="user", cascade="all, delete-orphan")


class Number(Base):
    __tablename__ = "numbers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    number = Column(String(64), nullable=False, index=True)
    country = Column(String(64), nullable=False, index=True)
    service = Column(String(64), nullable=False, index=True)
    price_inr = Column(Float, nullable=False)
    price_usd = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    # Statuses: available, reserved, sold, inactive
    status = Column(String(32), default="available", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="number_item")
    seller = relationship("User", foreign_keys=[seller_id])

    __table_args__ = (
        Index("ix_numbers_status_country_service", "status", "country", "service"),
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    number_id = Column(Integer, ForeignKey("numbers.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False)  # 'INR' or 'USD'
    payment_id = Column(String(128), nullable=True, index=True)
    # Payment statuses: pending, paid, failed, refunded, disputed
    payment_status = Column(String(32), default="pending", nullable=False, index=True)
    # Order statuses: pending, paid, fulfilled, cancelled, refunded
    order_status = Column(String(32), default="pending", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="orders")
    number_item = relationship("Number", back_populates="orders")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    number = Column(String(64), nullable=False)
    country = Column(String(64), nullable=False)
    service = Column(String(64), nullable=False)
    price_inr = Column(Float, nullable=False)
    price_usd = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    # Listing statuses: pending, approved, rejected, sold, cancelled
    status = Column(String(32), default="pending", nullable=False, index=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    seller = relationship("User", back_populates="listings")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Types: purchase, earning, commission, payout, refund
    type = Column(String(32), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False)
    reference = Column(String(128), nullable=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="transactions")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    balance_inr = Column(Float, default=0.0, nullable=False)
    balance_usd = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="wallet")


class PayoutRequest(Base):
    __tablename__ = "payout_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False)  # 'INR' or 'USD'
    payout_details = Column(Text, nullable=False)
    # Statuses: pending, approved, rejected, paid
    status = Column(String(32), default="pending", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="payout_requests")


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id = Column(String(128), primary_key=True)
    event_type = Column(String(64), nullable=True)
    processed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(String(255), nullable=False)
