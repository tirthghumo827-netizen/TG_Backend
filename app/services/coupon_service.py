import secrets
import string

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    Coupon,
    CouponRedemption,
    HeritageTrip,
    ODT1,
    ChotaPachmarhi,
    UjjainOmkareshwarTrip,
)


# ============================================================
# CONFIG
# ============================================================

NEW_USER_COUPON = "GHUMO100"
DISCOUNT_AMOUNT = 100
MAX_TOTAL_DISCOUNT = 100


# ============================================================
# HELPERS
# ============================================================

def normalize_email(email: str) -> str:
    """Normalize email before doing any comparison."""
    return (email or "").strip().lower()


def generate_heritage_coupon() -> str:
    """
    Generates a unique Heritage -> Trek coupon.

    Example:
        TG-TREK-A8X29KLM
    """

    suffix = "".join(
        secrets.choice(
            string.ascii_uppercase + string.digits
        )
        for _ in range(8)
    )

    return f"TG-TREK-{suffix}"


# ============================================================
# PREVIOUS BOOKING CHECK
# ============================================================

def _has_previous_booking_in_model(
    db: Session,
    model,
    email: str,
    exclude_booking_id: int | None = None,
) -> bool:
    """
    Check whether an email already has a non-declined/non-cancelled
    booking in the supplied booking model.

    exclude_booking_id is important during redeem_coupon():

    create_odt_booking()
        -> db.add(booking)
        -> db.flush()
        -> redeem_coupon()
        -> validate_coupon()
        -> has_previous_booking()

    At that point the current booking already exists in the SQLAlchemy
    session. Without excluding it, the current first booking would be
    incorrectly treated as a previous booking.
    """

    query = (
        db.query(model.id)
        .filter(
            model.primary_email.ilike(email),
            or_(
                model.status.is_(None),
                model.status.notin_(
                    ["declined", "cancelled"]
                ),
            ),
        )
    )

    if exclude_booking_id is not None:
        query = query.filter(
            model.id != exclude_booking_id
        )

    return query.first() is not None


def has_previous_booking(
    db: Session,
    email: str,
    exclude_booking_id: int | None = None,
) -> bool:
    """
    Check whether the user has already made a TirthGhumo booking.

    GHUMO100 is a first-booking coupon, so all relevant booking models
    are checked:

        - ODT1 / Budhni
        - HeritageTrip
        - ChotaPachmarhi / Halali
        - UjjainOmkareshwarTrip

    The current booking can be excluded by passing exclude_booking_id.
    """

    email = normalize_email(email)

    if not email:
        return False

    booking_models = (
        ODT1,
        HeritageTrip,
        ChotaPachmarhi,
        UjjainOmkareshwarTrip,
    )

    for model in booking_models:
        if _has_previous_booking_in_model(
            db=db,
            model=model,
            email=email,
            exclude_booking_id=exclude_booking_id,
        ):
            return True

    return False


# ============================================================
# SINGLE COUPON VALIDATION
# ============================================================

def validate_coupon(
    db: Session,
    coupon_code: str,
    email: str,
    trip_type: str,
    exclude_booking_id: int | None = None,
):
    """
    Validate one coupon.

    exclude_booking_id is used only when redeem_coupon() validates a
    coupon after the booking has already been flushed to the database.
    """

    email = normalize_email(email)
    coupon_code = (coupon_code or "").strip().upper()
    trip_type = (trip_type or "").strip().upper()

    if trip_type not in {"TREK", "HERITAGE"}:
        return {
            "valid": False,
            "message": "Invalid trip type",
        }

    # ========================================================
    # GHUMO100
    # ========================================================

    if coupon_code == NEW_USER_COUPON:

        if has_previous_booking(
            db=db,
            email=email,
            exclude_booking_id=exclude_booking_id,
        ):
            return {
                "valid": False,
                "message": (
                    "GHUMO100 is valid only "
                    "for your first TirthGhumo booking."
                ),
            }

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
                "message": "GHUMO100 has already been used.",
            }

        return {
            "valid": True,
            "code": NEW_USER_COUPON,
            "discount": DISCOUNT_AMOUNT,
            "coupon_type": "NEW_USER",
            "message": "Coupon applied successfully",
        }

    # ========================================================
    # GENERATED HERITAGE -> TREK COUPON
    # ========================================================

    coupon = (
        db.query(Coupon)
        .filter(
            Coupon.coupon_code == coupon_code
        )
        .first()
    )

    if not coupon:
        return {
            "valid": False,
            "message": "Invalid coupon code",
        }

    if coupon.coupon_type != "HERITAGE_TO_TREK":
        return {
            "valid": False,
            "message": "Invalid coupon type",
        }

    if trip_type != "TREK":
        return {
            "valid": False,
            "message": (
                "This coupon is valid only "
                "for One Day Trek."
            ),
        }

    if not coupon.user_email:
        return {
            "valid": False,
            "message": "Coupon has no assigned user.",
        }

    if normalize_email(coupon.user_email) != email:
        return {
            "valid": False,
            "message": "This coupon belongs to another user.",
        }

    if coupon.is_redeemed:
        return {
            "valid": False,
            "message": "Coupon has already been redeemed.",
        }

    if coupon.expires_at:

        expiry = coupon.expires_at

        if expiry.tzinfo is None:
            expiry = expiry.replace(
                tzinfo=timezone.utc
            )

        if expiry <= datetime.now(timezone.utc):
            return {
                "valid": False,
                "message": "Coupon has expired.",
            }

    return {
        "valid": True,
        "code": coupon.coupon_code,
        "discount": coupon.discount_amount,
        "coupon_type": "HERITAGE_TO_TREK",
        "message": "Coupon applied successfully",
    }


# ============================================================
# MULTIPLE COUPONS
# ============================================================

def validate_coupons(
    db: Session,
    coupon_codes: list[str],
    email: str,
    trip_type: str,
    exclude_booking_id: int | None = None,
):
    """
    Validate multiple coupons.

    The combined discount can never exceed ₹100.
    """

    email = normalize_email(email)

    applied_coupons = []
    invalid_coupons = []

    total_discount = 0

    # Remove empty values and duplicates while preserving order.
    unique_codes = list(
        dict.fromkeys(
            code.strip().upper()
            for code in (coupon_codes or [])
            if code and code.strip()
        )
    )

    for code in unique_codes:

        result = validate_coupon(
            db=db,
            coupon_code=code,
            email=email,
            trip_type=trip_type,
            exclude_booking_id=exclude_booking_id,
        )

        if not result["valid"]:

            invalid_coupons.append({
                "coupon_code": code,
                "message": result["message"],
            })

            continue

        remaining_discount = (
            MAX_TOTAL_DISCOUNT - total_discount
        )

        if remaining_discount <= 0:
            break

        actual_discount = min(
            result["discount"],
            remaining_discount,
        )

        applied_coupons.append({
            "code": result["code"],
            "discount": actual_discount,
            "coupon_type": result["coupon_type"],
        })

        total_discount += actual_discount

    return {
        "discount": min(
            total_discount,
            MAX_TOTAL_DISCOUNT,
        ),
        "applied_coupons": applied_coupons,
        "invalid_coupons": invalid_coupons,
    }


# ============================================================
# REDEEM COUPON
# ============================================================

def redeem_coupon(
    db: Session,
    coupon_code: str,
    email: str,
    booking_id: int,
    trip_type: str,
):
    """
    Redeem a coupon after the booking has been flushed.

    The current booking is excluded from the first-booking check so that
    GHUMO100 works correctly for a genuinely new user.
    """

    email = normalize_email(email)
    coupon_code = (coupon_code or "").strip().upper()

    # Validate AGAIN before redemption.
    # The current booking is excluded from the first-booking check.
    result = validate_coupon(
        db=db,
        coupon_code=coupon_code,
        email=email,
        trip_type=trip_type,
        exclude_booking_id=booking_id,
    )

    if not result["valid"]:
        raise ValueError(result["message"])

    coupon_type = result["coupon_type"]

    # Prevent the same user from using the same coupon type twice.
    already_redeemed = (
        db.query(CouponRedemption)
        .filter(
            CouponRedemption.user_email == email,
            CouponRedemption.coupon_type == coupon_type,
        )
        .first()
    )

    if already_redeemed:
        raise ValueError(
            f"{coupon_type} coupon already redeemed."
        )

    # ========================================================
    # UNIQUE HERITAGE COUPON
    # ========================================================

    if coupon_type == "HERITAGE_TO_TREK":

        coupon = (
            db.query(Coupon)
            .filter(
                Coupon.coupon_code == coupon_code
            )
            .first()
        )

        if not coupon:
            raise ValueError(
                "Coupon not found."
            )

        if coupon.is_redeemed:
            raise ValueError(
                "Coupon has already been redeemed."
            )

        coupon.is_redeemed = True
        coupon.redeemed_at = datetime.now(
            timezone.utc
        )

    # ========================================================
    # RECORD REDEMPTION
    # ========================================================

    redemption = CouponRedemption(
        user_email=email,
        coupon_code=coupon_code,
        coupon_type=coupon_type,
        booking_id=str(booking_id),
        redeemed_at=datetime.now(timezone.utc),
    )

    db.add(redemption)

    return redemption
