import secrets
import string

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Coupon, CouponRedemption, HeritageTrip


# Single common new-user coupon
NEW_USER_COUPON = "GHUMO100"

DISCOUNT_AMOUNT = 100


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_heritage_coupon() -> str:
    """
    Generate a unique Heritage-to-Trek coupon code.
    Example: TG-TREK-A8X29KLM
    """
    suffix = "".join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(8)
    )

    return f"TG-TREK-{suffix}"


def has_previous_booking(db: Session, email: str) -> bool:
    """
    Check whether the user has any previous eligible Heritage booking.

    TODO: Add the One Day Trek booking model query here.
    """

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

    # TODO:
    # Check previous One Day Trek bookings here
    # using the actual Trek booking model.

    return False


def validate_coupon(
    db: Session,
    coupon_code: str,
    email: str,
    trip_type: str,
):
    """
    Validate GHUMO100 or a unique Heritage-to-Trek coupon.
    """

    email = normalize_email(email)
    coupon_code = coupon_code.strip().upper()
    trip_type = trip_type.strip().upper()

    # Validate trip type
    if trip_type not in {"TREK", "HERITAGE"}:
        return {
            "valid": False,
            "message": "Invalid trip type",
        }

    # -----------------------------------------
    # COMMON NEW-USER COUPON: GHUMO100
    # -----------------------------------------

    if coupon_code == NEW_USER_COUPON:

        # Check previous bookings
        if has_previous_booking(db, email):
            return {
                "valid": False,
                "message": (
                    "New-user coupon is valid only "
                    "for your first TirthGhumo booking."
                ),
            }

        # Check whether the user already redeemed
        # the new-user coupon
        already_used = (
            db.query(CouponRedemption)
            .filter(
                CouponRedemption.user_email == email,
                CouponRedemption.coupon_type == "NEW_USER",
            )
            .first()
        )

        if already_used:
            return {
                "valid": False,
                "message": "New-user coupon already used.",
            }

        return {
            "valid": True,
            "discount": DISCOUNT_AMOUNT,
            "coupon_type": "NEW_USER",
            "message": "Coupon applied successfully",
        }

    # -----------------------------------------
    # UNIQUE HERITAGE-TO-TREK COUPON
    # -----------------------------------------

    coupon = (
        db.query(Coupon)
        .filter(
            Coupon.coupon_code == coupon_code
        )
        .first()
    )

    # Coupon does not exist
    if not coupon:
        return {
            "valid": False,
            "message": "Invalid coupon code",
        }

    # Check coupon type
    if coupon.coupon_type != "HERITAGE_TO_TREK":
        return {
            "valid": False,
            "message": "Invalid coupon type",
        }

    # Heritage-to-Trek coupon is valid only for Trek
    if trip_type != "TREK":
        return {
            "valid": False,
            "message": (
                "This coupon is valid only for One Day Trek."
            ),
        }

    # Check coupon owner
    if normalize_email(coupon.user_email) != email:
        return {
            "valid": False,
            "message": "This coupon belongs to another user.",
        }

    # Check if already redeemed
    if coupon.is_redeemed:
        return {
            "valid": False,
            "message": "Coupon has already been redeemed.",
        }

    # Check coupon expiry
    if coupon.expires_at:

        expiry = coupon.expires_at

        # Handle timezone-naive datetime values
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= datetime.now(timezone.utc):
            return {
                "valid": False,
                "message": "Coupon has expired.",
            }

    # Coupon is valid
    return {
        "valid": True,
        "discount": coupon.discount_amount,
        "coupon_type": "HERITAGE_TO_TREK",
        "message": "Coupon applied successfully",
    }