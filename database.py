import datetime
import logging
import uuid
from contextlib import contextmanager
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from config import DATABASE_URL, DEFAULT_COMMISSION_PERCENT
from models import (
    Base,
    User,
    Number,
    Order,
    Listing,
    Transaction,
    Wallet,
    PayoutRequest,
    ProcessedEvent,
    Setting,
)

logger = logging.getLogger(__name__)

# Connect args for SQLite to allow multiple threads
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
    future=True,
)


def init_db() -> None:
    """Initializes all database tables and seeds default settings if needed."""
    Base.metadata.create_all(bind=engine)
    with get_db() as db:
        commission_setting = db.query(Setting).filter(Setting.key == "commission_percent").first()
        if not commission_setting:
            db.add(Setting(key="commission_percent", value=str(DEFAULT_COMMISSION_PERCENT)))
            db.commit()
    logger.info("Database initialized successfully.")


@contextmanager
def get_db():
    """Context manager for obtaining a transactional database session."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------
# User Operations
# ---------------------------------------------------------

def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> User:
    """Fetches existing user or creates a new one with an initialized wallet."""
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                currency="INR",
                is_banned=False,
            )
            db.add(user)
            db.flush()  # populate user.id

            # Create initial wallet
            wallet = Wallet(
                user_id=user.id,
                balance_inr=0.0,
                balance_usd=0.0,
            )
            db.add(wallet)
            db.commit()
            db.refresh(user)
        else:
            # Update username and first_name if changed
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if not user.wallet:
                wallet = Wallet(user_id=user.id, balance_inr=0.0, balance_usd=0.0)
                db.add(wallet)
                updated = True
            if updated:
                db.commit()
                db.refresh(user)
        return user


def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    with get_db() as db:
        return db.query(User).filter(User.telegram_id == telegram_id).first()


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_db() as db:
        return db.query(User).filter(User.id == user_id).first()


def set_user_currency(telegram_id: int, currency: str) -> bool:
    if currency not in ("INR", "USD"):
        return False
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.currency = currency
            db.commit()
            return True
        return False


def set_user_ban_status(telegram_id: int, is_banned: bool) -> bool:
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.is_banned = is_banned
            db.commit()
            return True
        return False


# ---------------------------------------------------------
# Inventory & Numbers Operations
# ---------------------------------------------------------

def add_number(
    number: str,
    country: str,
    service: str,
    price_inr: float,
    price_usd: float,
    description: Optional[str] = None,
    seller_id: Optional[int] = None,
) -> Number:
    with get_db() as db:
        new_number = Number(
            number=number.strip(),
            country=country.strip(),
            service=service.strip(),
            price_inr=float(price_inr),
            price_usd=float(price_usd),
            description=description.strip() if description else None,
            seller_id=seller_id,
            status="available",
        )
        db.add(new_number)
        db.commit()
        db.refresh(new_number)
        return new_number


def bulk_add_numbers(lines: List[str]) -> Tuple[int, int, List[str]]:
    """
    Parses and bulk inserts numbers formatted as:
    number | country | service | price_inr | price_usd
    Returns: (added_count, failed_count, error_messages)
    """
    added = 0
    failed = 0
    errors: List[str] = []

    with get_db() as db:
        for idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 5:
                failed += 1
                errors.append(f"Row {idx}: Expected 5 fields separated by '|', got {len(parts)}")
                continue

            num_str, country, service, p_inr_str, p_usd_str = parts[:5]
            desc = parts[5].strip() if len(parts) > 5 else None

            try:
                p_inr = float(p_inr_str.replace("₹", "").replace("$", "").strip())
                p_usd = float(p_usd_str.replace("$", "").replace("₹", "").strip())
                if p_inr <= 0 or p_usd <= 0:
                    raise ValueError("Prices must be greater than 0")
            except ValueError as e:
                failed += 1
                errors.append(f"Row {idx}: Invalid price ({str(e)})")
                continue

            # Check if active duplicate already exists
            existing = (
                db.query(Number)
                .filter(Number.number == num_str, Number.status.in_(["available", "reserved"]))
                .first()
            )
            if existing:
                failed += 1
                errors.append(f"Row {idx}: Active number '{num_str}' already in inventory")
                continue

            item = Number(
                number=num_str,
                country=country,
                service=service,
                price_inr=p_inr,
                price_usd=p_usd,
                description=desc,
                seller_id=None,
                status="available",
            )
            db.add(item)
            added += 1

        db.commit()

    return added, failed, errors


def get_available_countries() -> List[Tuple[str, int]]:
    """Returns list of (country_name, count) of available numbers."""
    with get_db() as db:
        results = (
            db.query(Number.country, func.count(Number.id))
            .filter(Number.status == "available")
            .group_by(Number.country)
            .order_by(Number.country.asc())
            .all()
        )
        return [(r[0], r[1]) for r in results]


def get_available_services(country: str) -> List[Tuple[str, int]]:
    """Returns list of (service_name, count) for a given country."""
    with get_db() as db:
        results = (
            db.query(Number.service, func.count(Number.id))
            .filter(Number.status == "available", Number.country == country)
            .group_by(Number.service)
            .order_by(Number.service.asc())
            .all()
        )
        return [(r[0], r[1]) for r in results]


def get_available_numbers_by_service(country: str, service: str) -> List[Number]:
    with get_db() as db:
        return (
            db.query(Number)
            .filter(
                Number.status == "available",
                Number.country == country,
                Number.service == service,
            )
            .order_by(Number.id.desc())
            .limit(20)
            .all()
        )


def get_number_by_id(number_id: int) -> Optional[Number]:
    with get_db() as db:
        return db.query(Number).filter(Number.id == number_id).first()


def delete_unsold_number(number_id: int) -> Tuple[bool, str]:
    with get_db() as db:
        num = db.query(Number).filter(Number.id == number_id).first()
        if not num:
            return False, "Number not found."
        if num.status == "sold":
            return False, "Cannot delete a sold number with completed order history."
        db.delete(num)
        db.commit()
        return True, "Number deleted successfully."


def toggle_number_status(number_id: int, new_status: str) -> Tuple[bool, str]:
    if new_status not in ("available", "inactive"):
        return False, "Invalid status change."
    with get_db() as db:
        num = db.query(Number).filter(Number.id == number_id).first()
        if not num:
            return False, "Number not found."
        if num.status in ("reserved", "sold"):
            return False, f"Cannot change status while {num.status}."
        num.status = new_status
        db.commit()
        return True, f"Number status changed to {new_status}."


# ---------------------------------------------------------
# Order & Purchase Operations (Atomic & Safe)
# ---------------------------------------------------------

def create_pending_purchase_order(
    user_id: int,
    number_id: int,
    currency: str,
) -> Tuple[Optional[Order], str]:
    """
    Atomically reserves an available number and creates a pending Order.
    Guarantees that two users cannot reserve or buy the same number concurrently.
    """
    with get_db() as db:
        num = db.query(Number).filter(Number.id == number_id).with_for_update().first()
        if not num:
            return None, "Number not found."
        if num.status != "available":
            return None, f"Number is no longer available (current status: {num.status})."

        # Mark number reserved
        num.status = "reserved"

        price = num.price_inr if currency == "INR" else num.price_usd
        order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"

        new_order = Order(
            order_id=order_id,
            user_id=user_id,
            number_id=num.id,
            amount=price,
            currency=currency,
            payment_status="pending",
            order_status="pending",
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order, "Order created successfully."


def cancel_pending_order(order_id: str) -> Tuple[bool, str]:
    """Cancels a pending order and reverts number status to 'available'."""
    with get_db() as db:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            return False, "Order not found."
        if order.order_status != "pending":
            return False, f"Order cannot be cancelled (status: {order.order_status})."

        order.order_status = "cancelled"
        order.payment_status = "failed"

        num = db.query(Number).filter(Number.id == order.number_id).first()
        if num and num.status == "reserved":
            num.status = "available"

        db.commit()
        return True, "Order has been cancelled."


def get_order_by_order_id(order_id: str) -> Optional[Order]:
    with get_db() as db:
        return db.query(Order).filter(Order.order_id == order_id).first()


def get_order_by_payment_id(payment_id: str) -> Optional[Order]:
    with get_db() as db:
        return db.query(Order).filter(Order.payment_id == payment_id).first()


def update_order_payment_id(order_id: str, payment_id: str) -> None:
    with get_db() as db:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            order.payment_id = payment_id
            db.commit()


def fulfill_order_and_credit_seller(
    order_id: str,
    payment_id: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Atomically fulfills an order upon verified payment:
    1. Checks if already fulfilled/paid to prevent double-fulfillment.
    2. Marks order as 'paid' and 'fulfilled'.
    3. Marks number as 'sold'.
    4. If number belonged to a seller, calculates marketplace commission and credits seller wallet.
    5. Records transactions for buyer purchase and seller earnings.
    """
    with get_db() as db:
        order = db.query(Order).filter(Order.order_id == order_id).with_for_update().first()
        if not order:
            return False, f"Order {order_id} not found.", None

        if order.order_status == "fulfilled" and order.payment_status == "paid":
            return True, "Order already fulfilled.", None

        num = db.query(Number).filter(Number.id == order.number_id).with_for_update().first()
        if not num:
            return False, f"Associated number {order.number_id} not found.", None

        # Update order
        order.order_status = "fulfilled"
        order.payment_status = "paid"
        if payment_id:
            order.payment_id = payment_id

        # Mark number sold
        num.status = "sold"

        # Record buyer purchase transaction
        buyer_tx = Transaction(
            user_id=order.user_id,
            type="purchase",
            amount=order.amount,
            currency=order.currency,
            reference=order.order_id,
            description=f"Purchased number {num.number} ({num.country} - {num.service})",
        )
        db.add(buyer_tx)

        seller_info = None
        # Handle seller earnings if number is user-listed
        if num.seller_id:
            seller = db.query(User).filter(User.id == num.seller_id).first()
            if seller:
                comm_setting = db.query(Setting).filter(Setting.key == "commission_percent").first()
                comm_pct = float(comm_setting.value) if comm_setting else DEFAULT_COMMISSION_PERCENT

                commission_amount = round(order.amount * (comm_pct / 100.0), 2)
                seller_net = round(order.amount - commission_amount, 2)

                # Ensure wallet exists
                wallet = db.query(Wallet).filter(Wallet.user_id == seller.id).first()
                if not wallet:
                    wallet = Wallet(user_id=seller.id, balance_inr=0.0, balance_usd=0.0)
                    db.add(wallet)
                    db.flush()

                if order.currency == "INR":
                    wallet.balance_inr += seller_net
                else:
                    wallet.balance_usd += seller_net

                # Record seller earning transaction
                seller_tx = Transaction(
                    user_id=seller.id,
                    type="earning",
                    amount=seller_net,
                    currency=order.currency,
                    reference=order.order_id,
                    description=f"Sale earning for {num.number} (Total: {order.amount} - {comm_pct}% comm: {commission_amount})",
                )
                db.add(seller_tx)

                # Mark corresponding listing as sold if found
                listing = (
                    db.query(Listing)
                    .filter(Listing.seller_id == seller.id, Listing.number == num.number)
                    .first()
                )
                if listing:
                    listing.status = "sold"

                seller_info = {
                    "seller_telegram_id": seller.telegram_id,
                    "seller_net": seller_net,
                    "currency": order.currency,
                    "commission": commission_amount,
                }

        # Query buyer telegram_id
        buyer = db.query(User).filter(User.id == order.user_id).first()

        db.commit()

        result_payload = {
            "buyer_telegram_id": buyer.telegram_id if buyer else None,
            "order_id": order.order_id,
            "number": num.number,
            "country": num.country,
            "service": num.service,
            "amount": order.amount,
            "currency": order.currency,
            "seller_info": seller_info,
        }
        return True, "Order fulfilled successfully.", result_payload


def mark_order_failed(order_id: str, reason: str = "Payment failed") -> bool:
    with get_db() as db:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            return False
        if order.order_status == "fulfilled":
            return False  # Do not cancel fulfilled order

        order.order_status = "cancelled"
        order.payment_status = "failed"

        num = db.query(Number).filter(Number.id == order.number_id).first()
        if num and num.status == "reserved":
            num.status = "available"

        db.commit()
        return True


# ---------------------------------------------------------
# Listings & Seller Operations
# ---------------------------------------------------------

def create_seller_listing(
    seller_id: int,
    number: str,
    country: str,
    service: str,
    price_inr: float,
    price_usd: float,
    description: Optional[str] = None,
) -> Listing:
    with get_db() as db:
        listing = Listing(
            seller_id=seller_id,
            number=number.strip(),
            country=country.strip(),
            service=service.strip(),
            price_inr=float(price_inr),
            price_usd=float(price_usd),
            description=description.strip() if description else None,
            status="pending",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing


def get_pending_listings() -> List[Listing]:
    with get_db() as db:
        return db.query(Listing).filter(Listing.status == "pending").order_by(Listing.id.desc()).all()


def get_listing_by_id(listing_id: int) -> Optional[Listing]:
    with get_db() as db:
        return db.query(Listing).filter(Listing.id == listing_id).first()


def approve_seller_listing(listing_id: int, admin_note: Optional[str] = None) -> Tuple[bool, str, Optional[Listing]]:
    with get_db() as db:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing:
            return False, "Listing not found.", None
        if listing.status != "pending":
            return False, f"Listing status is already {listing.status}.", None

        listing.status = "approved"
        listing.admin_note = admin_note

        # Create live number item in inventory
        num = Number(
            number=listing.number,
            country=listing.country,
            service=listing.service,
            price_inr=listing.price_inr,
            price_usd=listing.price_usd,
            description=listing.description,
            seller_id=listing.seller_id,
            status="available",
        )
        db.add(num)
        db.commit()
        db.refresh(listing)
        return True, "Listing approved and added to available inventory.", listing


def reject_seller_listing(listing_id: int, reason: Optional[str] = None) -> Tuple[bool, str, Optional[Listing]]:
    with get_db() as db:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing:
            return False, "Listing not found.", None
        if listing.status != "pending":
            return False, f"Listing status is already {listing.status}.", None

        listing.status = "rejected"
        listing.admin_note = reason or "Rejected by administrator."
        db.commit()
        db.refresh(listing)
        return True, "Listing rejected.", listing


# ---------------------------------------------------------
# Payout Requests & Wallet Operations
# ---------------------------------------------------------

def create_payout_request(
    user_id: int,
    amount: float,
    currency: str,
    payout_details: str,
) -> Tuple[bool, str, Optional[PayoutRequest]]:
    with get_db() as db:
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).with_for_update().first()
        if not wallet:
            return False, "Wallet not found.", None

        if currency == "INR":
            if wallet.balance_inr < amount:
                return False, f"Insufficient INR balance (Available: ₹{wallet.balance_inr:.2f})", None
            wallet.balance_inr -= amount
        elif currency == "USD":
            if wallet.balance_usd < amount:
                return False, f"Insufficient USD balance (Available: ${wallet.balance_usd:.2f})", None
            wallet.balance_usd -= amount
        else:
            return False, "Invalid currency.", None

        payout = PayoutRequest(
            user_id=user_id,
            amount=amount,
            currency=currency,
            payout_details=payout_details,
            status="pending",
        )
        db.add(payout)
        db.commit()
        db.refresh(payout)
        return True, "Payout request submitted successfully.", payout


def get_pending_payouts() -> List[PayoutRequest]:
    with get_db() as db:
        return db.query(PayoutRequest).filter(PayoutRequest.status == "pending").order_by(PayoutRequest.id.desc()).all()


def process_payout_request(payout_id: int, action: str) -> Tuple[bool, str, Optional[PayoutRequest]]:
    """Action: 'approved', 'paid', or 'rejected'"""
    with get_db() as db:
        payout = db.query(PayoutRequest).filter(PayoutRequest.id == payout_id).with_for_update().first()
        if not payout:
            return False, "Payout request not found.", None
        if payout.status not in ("pending", "approved"):
            return False, f"Cannot update payout in state: {payout.status}.", None

        if action in ("approved", "paid"):
            payout.status = action
            payout.processed_at = datetime.datetime.utcnow()
            if action == "paid":
                # Record transaction
                tx = Transaction(
                    user_id=payout.user_id,
                    type="payout",
                    amount=payout.amount,
                    currency=payout.currency,
                    reference=f"PAYOUT-{payout.id}",
                    description=f"Completed payout to: {payout.payout_details[:30]}",
                )
                db.add(tx)
        elif action == "rejected":
            payout.status = "rejected"
            payout.processed_at = datetime.datetime.utcnow()
            # Refund wallet balance
            wallet = db.query(Wallet).filter(Wallet.user_id == payout.user_id).first()
            if wallet:
                if payout.currency == "INR":
                    wallet.balance_inr += payout.amount
                else:
                    wallet.balance_usd += payout.amount
        else:
            return False, "Invalid action.", None

        db.commit()
        db.refresh(payout)
        return True, f"Payout request updated to {action}.", payout


# ---------------------------------------------------------
# Webhook Deduplication / Idempotency
# ---------------------------------------------------------

def is_event_processed(event_id: str) -> bool:
    with get_db() as db:
        return db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first() is not None


def record_processed_event(event_id: str, event_type: Optional[str] = None) -> None:
    with get_db() as db:
        existing = db.query(ProcessedEvent).filter(ProcessedEvent.event_id == event_id).first()
        if not existing:
            db.add(ProcessedEvent(event_id=event_id, event_type=event_type))
            db.commit()


# ---------------------------------------------------------
# Statistics & Dashboards
# ---------------------------------------------------------

def get_admin_dashboard_stats() -> Dict[str, Any]:
    with get_db() as db:
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_numbers = db.query(func.count(Number.id)).scalar() or 0
        available_numbers = db.query(func.count(Number.id)).filter(Number.status == "available").scalar() or 0
        sold_numbers = db.query(func.count(Number.id)).filter(Number.status == "sold").scalar() or 0
        total_orders = db.query(func.count(Order.id)).scalar() or 0

        # Revenue INR & USD
        revenue_inr = (
            db.query(func.sum(Order.amount))
            .filter(Order.order_status == "fulfilled", Order.currency == "INR")
            .scalar()
            or 0.0
        )
        revenue_usd = (
            db.query(func.sum(Order.amount))
            .filter(Order.order_status == "fulfilled", Order.currency == "USD")
            .scalar()
            or 0.0
        )

        # Seller Earnings INR & USD
        seller_earnings_inr = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.type == "earning", Transaction.currency == "INR")
            .scalar()
            or 0.0
        )
        seller_earnings_usd = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.type == "earning", Transaction.currency == "USD")
            .scalar()
            or 0.0
        )

        pending_listings = db.query(func.count(Listing.id)).filter(Listing.status == "pending").scalar() or 0
        pending_payouts = db.query(func.count(PayoutRequest.id)).filter(PayoutRequest.status == "pending").scalar() or 0

        comm_setting = db.query(Setting).filter(Setting.key == "commission_percent").first()
        comm_pct = float(comm_setting.value) if comm_setting else DEFAULT_COMMISSION_PERCENT

        profit_inr = round(revenue_inr - seller_earnings_inr, 2)
        profit_usd = round(revenue_usd - seller_earnings_usd, 2)

        return {
            "total_users": total_users,
            "total_numbers": total_numbers,
            "available_numbers": available_numbers,
            "sold_numbers": sold_numbers,
            "total_orders": total_orders,
            "revenue_inr": revenue_inr,
            "revenue_usd": revenue_usd,
            "seller_earnings_inr": seller_earnings_inr,
            "seller_earnings_usd": seller_earnings_usd,
            "profit_inr": profit_inr,
            "profit_usd": profit_usd,
            "pending_listings": pending_listings,
            "pending_payouts": pending_payouts,
            "commission_percent": comm_pct,
        }


def get_user_stats(user_id: int) -> Dict[str, Any]:
    with get_db() as db:
        orders_count = db.query(func.count(Order.id)).filter(Order.user_id == user_id).scalar() or 0
        purchases_count = (
            db.query(func.count(Order.id))
            .filter(Order.user_id == user_id, Order.order_status == "fulfilled")
            .scalar()
            or 0
        )
        listings_count = db.query(func.count(Listing.id)).filter(Listing.seller_id == user_id).scalar() or 0
        sales_count = (
            db.query(func.count(Listing.id))
            .filter(Listing.seller_id == user_id, Listing.status == "sold")
            .scalar()
            or 0
        )

        spent_inr = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id, Transaction.type == "purchase", Transaction.currency == "INR")
            .scalar()
            or 0.0
        )
        spent_usd = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id, Transaction.type == "purchase", Transaction.currency == "USD")
            .scalar()
            or 0.0
        )

        earned_inr = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id, Transaction.type == "earning", Transaction.currency == "INR")
            .scalar()
            or 0.0
        )
        earned_usd = (
            db.query(func.sum(Transaction.amount))
            .filter(Transaction.user_id == user_id, Transaction.type == "earning", Transaction.currency == "USD")
            .scalar()
            or 0.0
        )

        return {
            "orders": orders_count,
            "purchases": purchases_count,
            "listings": listings_count,
            "sales": sales_count,
            "spent_inr": spent_inr,
            "spent_usd": spent_usd,
            "earned_inr": earned_inr,
            "earned_usd": earned_usd,
        }


def get_system_setting(key: str, default: str = "") -> str:
    with get_db() as db:
        s = db.query(Setting).filter(Setting.key == key).first()
        return s.value if s else default


def set_system_setting(key: str, value: str) -> None:
    with get_db() as db:
        s = db.query(Setting).filter(Setting.key == key).first()
        if s:
            s.value = value
        else:
            db.add(Setting(key=key, value=value))
        db.commit()
