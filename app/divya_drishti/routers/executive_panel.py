from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
import os
import shutil
import uuid
from pathlib import Path
from app.utils.supabase_uploads import upload_to_supabase
from fastapi import File, Form, UploadFile

from ..executive_schema import (
    DashboardResponse,
    EarningsSummaryResponse,
    ExecutiveProfileResponse,
    ExecutiveProfileUpdate,
    PayoutResponse,
    RatingReviewResponse,
    SessionAssignmentResponse,
)
from ..models import (
    DarshanBooking,
    DarshanReview,
    DistanceRateConfig,
    Executive,
    SaarthiPayout,
    SaarthiSessionAssignment,
)


router = APIRouter(
    prefix="/divya-drishti/executive-panel",
    tags=["Saarthi Executive Panel"],
)


def money(value) -> Decimal:
    return Decimal(str(value or 0))


def as_float(value) -> float:
    return float(money(value))


def mask_name(name: str) -> str:
    parts = (name or "").split()
    if not parts:
        return "Customer"
    first = parts[0]
    return f"{first[0]}***" if len(first) > 1 else first


def address_area(address: Optional[str]) -> Optional[str]:
    if not address:
        return None
    chunks = [chunk.strip() for chunk in address.split(",") if chunk.strip()]
    return ", ".join(chunks[-2:]) if len(chunks) >= 2 else address[:120]


def get_executive(db: Session, executive_id: int) -> Executive:
    executive = db.query(Executive).filter(Executive.id == executive_id).first()
    if not executive:
        raise HTTPException(status_code=404, detail="Executive not found")
    return executive


def get_assignment(db: Session, executive_id: int, assignment_id: int) -> SaarthiSessionAssignment:
    assignment = db.query(SaarthiSessionAssignment).filter(
        SaarthiSessionAssignment.id == assignment_id,
        SaarthiSessionAssignment.executive_id == executive_id,
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Session assignment not found")
    return assignment


def get_rate_config(db: Session) -> DistanceRateConfig:
    config = db.query(DistanceRateConfig).filter(
        DistanceRateConfig.is_active == True
    ).order_by(DistanceRateConfig.id.desc()).first()
    if config:
        return config
    return DistanceRateConfig(
        base_session_fee=0,
        first_slab_km=40,
        first_slab_rate=5,
        overflow_rate=6,
        is_active=True,
    )


def travel_component(distance_km: Optional[float], config: DistanceRateConfig) -> Decimal:
    distance = Decimal(str(distance_km or 0))
    first_slab_km = Decimal(str(config.first_slab_km or 40))
    first_distance = min(distance, first_slab_km)
    overflow_distance = max(distance - first_slab_km, Decimal("0"))
    return (
        first_distance * money(config.first_slab_rate)
        + overflow_distance * money(config.overflow_rate)
    )


def recalculate_assignment(assignment: SaarthiSessionAssignment, config: DistanceRateConfig) -> None:
    if not assignment.base_amount:
        assignment.base_amount = config.base_session_fee
    assignment.travel_amount = travel_component(assignment.distance_km, config)
    assignment.net_amount = (
        money(assignment.base_amount)
        + money(assignment.travel_amount)
        + money(assignment.extension_amount)
        - money(assignment.deductions)
    )


def period_bounds(period: str, start: Optional[date], end: Optional[date]) -> tuple[date, date]:
    today = date.today()
    if start and end:
        return start, end
    if period == "today":
        return today, today
    if period == "week":
        period_start = today - timedelta(days=today.weekday())
        return period_start, period_start + timedelta(days=6)
    if period == "month":
        period_start = today.replace(day=1)
        next_month = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return period_start, next_month - timedelta(days=1)
    raise HTTPException(status_code=400, detail="Invalid period")


def day_range(start: date, end: date) -> tuple[datetime, datetime]:
    starts_at = datetime.combine(start, time.min)
    ends_at = datetime.combine(end, time.max)
    return starts_at, ends_at


def assignment_response(assignment: SaarthiSessionAssignment) -> SessionAssignmentResponse:
    booking = assignment.booking
    duration_minutes = None
    if booking and booking.start_datetime and booking.end_datetime:
        duration_minutes = int((booking.end_datetime - booking.start_datetime).total_seconds() // 60)

    return SessionAssignmentResponse(
        id=assignment.id,
        booking_id=assignment.booking_id,
        status=assignment.status,
        scheduled_date=booking.slot_date if booking else None,
        scheduled_time=booking.slot_time if booking else None,
        customer_name=mask_name(booking.full_name if booking else ""),
        customer_contact=booking.contact_number if booking else None,
        address_area=address_area(booking.address if booking else None),
        distance_km=assignment.distance_km,
        duration_minutes=duration_minutes,
        extension_minutes=assignment.extension_minutes or 0,
        notes=assignment.notes,
        base_amount=as_float(assignment.base_amount),
        travel_amount=as_float(assignment.travel_amount),
        extension_amount=as_float(assignment.extension_amount),
        deductions=as_float(assignment.deductions),
        net_amount=as_float(assignment.net_amount),
        started_at=assignment.started_at,
        completed_at=assignment.completed_at,
    )


def average_rating(db: Session, executive_id: int, starts_at: Optional[datetime] = None, ends_at: Optional[datetime] = None):
    query = db.query(func.avg(DarshanReview.executive_rating)).join(
        SaarthiSessionAssignment,
        SaarthiSessionAssignment.booking_id == DarshanReview.booking_id,
    ).filter(SaarthiSessionAssignment.executive_id == executive_id)
    if starts_at and ends_at:
        query = query.filter(DarshanReview.created_at >= starts_at, DarshanReview.created_at <= ends_at)
    value = query.scalar()
    return round(float(value), 2) if value is not None else None


# 

def earnings_summary(
    db: Session,
    executive_id: int,
    start: date,
    end: date,
) -> EarningsSummaryResponse:
    starts_at, ends_at = day_range(start, end)
    assignments = db.query(SaarthiSessionAssignment).filter(
        SaarthiSessionAssignment.executive_id == executive_id,
        SaarthiSessionAssignment.status == "completed",
        SaarthiSessionAssignment.completed_at >= starts_at,
        SaarthiSessionAssignment.completed_at <= ends_at,
    ).all()
    settled = db.query(func.coalesce(func.sum(SaarthiPayout.total_paid), 0)).filter(
        SaarthiPayout.executive_id == executive_id,
        SaarthiPayout.period_start <= end,
        SaarthiPayout.period_end >= start,
        SaarthiPayout.status == "paid",
    ).scalar() or 0
    total_session_earnings = sum(as_float(item.net_amount) for item in assignments)

    return EarningsSummaryResponse(
        period_start=start,
        period_end=end,
        sessions_completed=len(assignments),
        total_distance_km=round(sum(float(item.distance_km or 0) for item in assignments), 2),
        total_base_amount=sum(as_float(item.base_amount) for item in assignments),
        total_travel_amount=sum(as_float(item.travel_amount) for item in assignments),
        total_extension_amount=sum(as_float(item.extension_amount) for item in assignments),
        total_deductions=sum(as_float(item.deductions) for item in assignments),
        total_session_earnings=total_session_earnings,
        settled_amount=as_float(settled),
        due_amount=total_session_earnings  - as_float(settled),
        average_rating=average_rating(db, executive_id, starts_at, ends_at),
    )


@router.get("/profile", response_model=ExecutiveProfileResponse)
def get_profile(executive_id: int = Query(...), db: Session = Depends(get_db)):
    return get_executive(db, executive_id)


@router.put("/profile", response_model=ExecutiveProfileResponse)
def update_profile(
    executive_id: int = Query(...),
    contact_number: Optional[str] = Form(None, max_length=15),
    email_address: Optional[str] = Form(None, max_length=255),
    address: Optional[str] = Form(None),
    bank_upi: Optional[str] = Form(None, max_length=255),
    photo: Optional[UploadFile] = File(None),
    zone: Optional[str] = Form(None),
    base_location: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    executive = get_executive(db, executive_id)

    if contact_number is not None:
        executive.contact_number = contact_number
    if email_address is not None:
        executive.email_address = email_address
    if address is not None:
        executive.address = address
    if bank_upi is not None:
        executive.bank_upi = bank_upi
    if zone is not None:
        executive.zone = zone
    if base_location is not None:
        executive.base_location = base_location

    if photo is not None:
        old_photo_url = executive.photo_url
        executive.photo_url = upload_to_supabase(photo, folder="executive_photos")
        delete_old_photo(old_photo_url)

    db.commit()
    db.refresh(executive)
    return executive


@router.get("/sessions", response_model=list[SessionAssignmentResponse])
def get_sessions(
    executive_id: int = Query(...),
    status_filter: Optional[str] = Query(None, alias="status"),
    start: Optional[date] = None,
    end: Optional[date] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db),
):
    get_executive(db, executive_id)
    query = db.query(SaarthiSessionAssignment).join(DarshanBooking).filter(
        SaarthiSessionAssignment.executive_id == executive_id
    )
    if status_filter:
        query = query.filter(SaarthiSessionAssignment.status == status_filter)
    if start:
        query = query.filter(DarshanBooking.slot_date >= start)
    if end:
        query = query.filter(DarshanBooking.slot_date <= end)
    if location:
        query = query.filter(DarshanBooking.address.ilike(f"%{location}%"))
    assignments = query.order_by(DarshanBooking.slot_date.desc(), DarshanBooking.slot_time.desc()).all()
    return [assignment_response(item) for item in assignments]


@router.get("/sessions/{assignment_id}", response_model=SessionAssignmentResponse)
def get_session_details(
    assignment_id: int,
    executive_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return assignment_response(get_assignment(db, executive_id, assignment_id))




@router.get("/ratings/reviews", response_model=list[RatingReviewResponse])
def get_rating_reviews(
    executive_id: int = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    get_executive(db, executive_id)
    reviews = (
    db.query(DarshanReview)
      .join(
          SaarthiSessionAssignment,
          SaarthiSessionAssignment.booking_id ==
          DarshanReview.booking_id
      )
      .filter(
          SaarthiSessionAssignment.executive_id ==
          executive_id
      )
      .all()
    )
    return [
    RatingReviewResponse(
        review_id=review.id,
        booking_id=review.booking_id,
        score=review.executive_rating,
        experience_rating=review.experience_rating,
        vr_quality_rating=review.vr_quality_rating,
        comment=review.comment,
        created_at=review.created_at,
        flagged=False
        )
    for review in reviews
    ]



@router.get("/earnings", response_model=EarningsSummaryResponse)
def get_earnings(
    executive_id: int = Query(...),
    period: str = Query("month", pattern="^(today|week|month|custom)$"),
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: Session = Depends(get_db),
):
    get_executive(db, executive_id)
    period_start, period_end = period_bounds(period, start, end)
    return earnings_summary(db, executive_id, period_start, period_end)


@router.get("/summary/weekly", response_model=EarningsSummaryResponse)
def get_weekly_summary(executive_id: int = Query(...), db: Session = Depends(get_db)):
    get_executive(db, executive_id)
    start, end = period_bounds("week", None, None)
    return earnings_summary(db, executive_id, start, end)


@router.get("/summary/monthly", response_model=EarningsSummaryResponse)
def get_monthly_summary(executive_id: int = Query(...), db: Session = Depends(get_db)):
    get_executive(db, executive_id)
    start, end = period_bounds("month", None, None)
    return earnings_summary(db, executive_id, start, end)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(executive_id: int = Query(...), db: Session = Depends(get_db)):
    get_executive(db, executive_id)
    today_start, today_end = day_range(date.today(), date.today())
    week_start, week_end = period_bounds("week", None, None)
    week_start_dt, week_end_dt = day_range(week_start, week_end)
    today_sessions = db.query(func.count(SaarthiSessionAssignment.id)).join(DarshanBooking).filter(
        SaarthiSessionAssignment.executive_id == executive_id,
        DarshanBooking.slot_date == date.today(),
        SaarthiSessionAssignment.status.in_(["assigned", "confirmed", "started"]),
    ).scalar() or 0
    week_summary = earnings_summary(db, executive_id, week_start, week_end)
    return DashboardResponse(
        today_sessions=today_sessions,
        week_earnings=week_summary.total_session_earnings,
        current_rating=average_rating(db, executive_id, today_start, today_end) or average_rating(db, executive_id),
        pending_due_amount=week_summary.due_amount,
    )


@router.get("/payouts", response_model=list[PayoutResponse])
def get_payouts(executive_id: int = Query(...), db: Session = Depends(get_db)):
    get_executive(db, executive_id)
    return db.query(SaarthiPayout).filter(
        SaarthiPayout.executive_id == executive_id
    ).order_by(SaarthiPayout.period_start.desc()).all()





