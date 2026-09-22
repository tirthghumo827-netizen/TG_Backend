import os
import secrets
import string

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Coupon, CouponRedemption , HeritageTrip


NEW_USER_COUPON = os.getenv(
    "GHUMO100"
)

COUPON_EXPIRY_DAYS = int(
    os.getenv("COUPON_EXPIRY_DAYS", "30")
)

DISCOUNT_AMOUNT = 100


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_heritage_coupon() -> str:
    suffix = "".join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(8)
    )

    return f"TG-TREK-{suffix}"


def has_previous_booking(db: Session, email: str) -> bool:
    email = normalize_email(email)

    # Check previous Heritage bookings
    heritage_booking = (
        db.query(HeritageTrip.id)
        .filter(
            HeritageTrip.primary_email.ilike(email),
            HeritageTrip.status.notin_(["declined", "cancelled"]),
        )
        .first()
    )

    if heritage_booking:
        return True

    # TODO: Check previous One Day Trek bookings here
    # after adding the actual Trek booking model.

    return False

def validate_coupon(
    db: Session,
    coupon_code: str,
    email: str,
    trip_type: str,
):
    email = normalize_email(email)
    coupon_code = coupon_code.strip().upper()
    trip_type = trip_type.strip().upper()

    if trip_type not in {"TREK", "HERITAGE"}:
        return {
            "valid": False,
            "message": "Invalid trip type"
        }

    # COMMON NEW-USER COUPON
    if coupon_code == NEW_USER_COUPON.upper():

        if has_previous_booking(db, email):
            return {
                "valid": False,
                "message": (
                    "New-user coupon is valid only "
                    "for your first TirthGhumo booking."
                )
            }

        already_used = db.query(CouponRedemption).filter(
            CouponRedemption.user_email == email,
            CouponRedemption.coupon_type == "NEW_USER",
        ).first()

        if already_used:
            return {
                "valid": False,
                "message": "New-user coupon already used."
            }

        return {
            "valid": True,
            "discount": DISCOUNT_AMOUNT,
            "coupon_type": "NEW_USER",
            "message": "Coupon applied successfully"
        }

    # UNIQUE HERITAGE-TO-TREK COUPON
    coupon = db.query(Coupon).filter(
        Coupon.coupon_code == coupon_code
    ).first()

    if not coupon:
        return {
            "valid": False,
            "message": "Invalid coupon code"
        }

    if coupon.coupon_type != "HERITAGE_TO_TREK":
        return {
            "valid": False,
            "message": "Invalid coupon type"
        }

    if trip_type != "TREK":
        return {
            "valid": False,
            "message": "This coupon is valid only for One Day Trek."
        }

    if coupon.user_email != email:
        return {
            "valid": False,
            "message": "This coupon belongs to another user."
        }

    if coupon.is_redeemed:
        return {
            "valid": False,
            "message": "Coupon has already been redeemed."
        }

    if (
        coupon.expires_at
        and coupon.expires_at <= datetime.now(timezone.utc)
    ):
        return {
            "valid": False,
            "message": "Coupon has expired."
        }

    return {
        "valid": True,
        "discount": coupon.discount_amount,
        "coupon_type": "HERITAGE_TO_TREK",
        "message": "Coupon applied successfully"
    }