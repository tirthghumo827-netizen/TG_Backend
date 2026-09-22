import os
import secrets
import string

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import Coupon


DISCOUNT_AMOUNT = 100

HERITAGE_TREK_EXPIRY_DAYS = int(
    os.getenv("HERITAGE_TREK_COUPON_EXPIRY_DAYS", "90")
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_heritage_coupon() -> str:
    """Generate a random, hard-to-guess coupon code."""
    suffix = "".join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(8)
    )

    return f"TG-TREK-{suffix}"


def get_or_create_heritage_trek_coupon(
    db: Session,
    email: str,
    heritage_booking_id: int,
):
    """
    Create or return the customer's Heritage-to-Trek coupon.

    The coupon:
    - Gives ₹100 off
    - Is valid only for TREK
    - Belongs to the customer's email
    - Expires after the configured number of days

    Reuses an existing coupon for the same customer to avoid
    duplicate generation if approval is retried.
    """

    email = normalize_email(email)

    # Reuse an existing coupon for this customer.
    existing_coupon = (
        db.query(Coupon)
        .filter(
            Coupon.user_email == email,
            Coupon.coupon_type == "HERITAGE_TO_TREK",
        )
        .first()
    )

    if existing_coupon:
        return existing_coupon, False

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        days=HERITAGE_TREK_EXPIRY_DAYS
    )

    # Retry if a randomly generated code already exists.
    for _ in range(10):
        coupon_code = generate_heritage_coupon()

        code_exists = (
            db.query(Coupon.id)
            .filter(Coupon.coupon_code == coupon_code)
            .first()
        )

        if not code_exists:
            break
    else:
        raise RuntimeError(
            "Unable to generate a unique coupon code."
        )

    coupon = Coupon(
        coupon_code=coupon_code,
        coupon_type="HERITAGE_TO_TREK",
        user_email=email,
        discount_amount=DISCOUNT_AMOUNT,
        applicable_on="TREK",
        is_redeemed=False,
        expires_at=expires_at,
    )

    db.add(coupon)
    db.commit()
    db.refresh(coupon)

    return coupon, True