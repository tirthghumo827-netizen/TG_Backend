from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.coupon_service import validate_coupon

router = APIRouter(prefix="/coupons", tags=["Coupons"])


class CouponValidateRequest(BaseModel):
    coupon_code: str
    email: EmailStr
    trip_type: str


@router.post("/validate")
def validate_coupon_api(
    payload: CouponValidateRequest,
    db: Session = Depends(get_db),
):
    return validate_coupon(
        db=db,
        coupon_code=payload.coupon_code,
        email=str(payload.email),
        trip_type=payload.trip_type,
    )